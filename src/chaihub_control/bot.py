from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from .approval_service import ApprovalService
from .config import LOG_PATH
from .logging_utils import setup_logging
from .models import ApprovalRequest, ApprovalStatus
from .planner import Planner
from .executor import Executor


@dataclass
class BotState:
    current_goal: Optional[str] = None


class TelegramBot:
    def __init__(
        self,
        token: str,
        authorized_user_id: int,
        planner: Planner,
        executor: Executor,
        approval_service: ApprovalService,
    ) -> None:
        self._logger = setup_logging(LOG_PATH)
        self._authorized_user_id = authorized_user_id
        self._planner = planner
        self._executor = executor
        self._approval_service = approval_service
        self._state = BotState()
        self._app = Application.builder().token(token).build()
        self._register_handlers()
        self._approval_service.set_notifier(self._notify_approval_request)

    def _register_handlers(self) -> None:
        self._app.add_handler(CommandHandler("run", self._run_command))
        self._app.add_handler(CommandHandler("status", self._status_command))
        self._app.add_handler(CommandHandler("stop", self._stop_command))
        self._app.add_handler(CommandHandler("pause", self._pause_command))
        self._app.add_handler(CommandHandler("resume", self._resume_command))
        self._app.add_handler(CallbackQueryHandler(self._approval_callback))

    async def start(self) -> None:
        self._logger.info("Bot started")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

    async def stop(self) -> None:
        self._logger.info("Bot stopping")
        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()

    async def _run_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        prompt = " ".join(context.args).strip()
        if not prompt:
            await update.message.reply_text("Usage: /run <instruction>")
            return
        self._logger.info("Prompt received | user=%s | prompt=%s", update.effective_user.id, prompt)
        self._planner.submit_prompt(prompt)
        self._state.current_goal = prompt
        await update.message.reply_text("Prompt accepted and queued.")

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        pending = self._approval_service.list_pending()
        pending_lines = "\n".join([f"- {req.request_id}: {req.action_summary}" for req in pending])
        status_message = (
            f"Current goal: {self._state.current_goal or 'None'}\n"
            f"Current action: {self._executor.current_action or 'Idle'}\n"
            f"Pending approvals: {len(pending)}\n"
            f"{pending_lines if pending_lines else ''}"
        )
        await update.message.reply_text(status_message)

    async def _stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        self._logger.info("Stop command received")
        self._executor.stop()
        self._planner.signal_stop()
        await update.message.reply_text("Execution stopped.")

    async def _pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        self._logger.info("Pause command received")
        self._executor.pause()
        await update.message.reply_text("Execution paused.")

    async def _resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        self._logger.info("Resume command received")
        self._executor.resume()
        await update.message.reply_text("Execution resumed.")

    async def _approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return
        query = update.callback_query
        if not query or not query.data:
            return
        await query.answer()
        try:
            action, request_id = query.data.split(":", 1)
        except ValueError:
            await query.edit_message_text("Malformed approval response.")
            return
        approved = action == "approve"
        request = self._approval_service.get_request(request_id)
        if not request:
            await query.edit_message_text("Approval request not found.")
            return
        if request.status != ApprovalStatus.WAITING:
            await query.edit_message_text(f"Request already handled: {request.status}")
            return
        status = self._approval_service.decide(request_id, approved)
        decision_text = "Approved" if status == ApprovalStatus.APPROVED else "Denied"
        await query.edit_message_text(
            f"{decision_text} | ID: {request_id}\nAction: {request.action_summary}\nRisk: {request.risk}"
        )
        await query.message.reply_text(f"Decision recorded: {decision_text}.")

    def _notify_approval_request(self, request: ApprovalRequest) -> None:
        async def _send() -> None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request.request_id}"),
                        InlineKeyboardButton("❌ Deny", callback_data=f"deny:{request.request_id}"),
                    ]
                ]
            )
            message = (
                f"Approval required\n"
                f"Action: {request.action_summary}\n"
                f"Risk: {request.risk}\n"
                f"ID: {request.request_id}"
            )
            sent = await self._app.bot.send_message(
                chat_id=self._authorized_user_id,
                text=message,
                reply_markup=keyboard,
            )
            request.message_id = sent.message_id
            request.chat_id = sent.chat_id
        asyncio.create_task(_send())

    def _is_authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != self._authorized_user_id:
            self._logger.warning("Unauthorized access attempt | user=%s", user_id)
            return False
        return True
