from __future__ import annotations

from typing import Callable

from .approval import ApprovalStore
from .logging_utils import setup_logging
from .models import Action, ApprovalRequest, ApprovalStatus


class ApprovalService:
    def __init__(self, store: ApprovalStore, log_path: str) -> None:
        self._store = store
        self._logger = setup_logging(log_path)
        self._notify_callback: Callable[[ApprovalRequest], None] | None = None

    def set_notifier(self, notifier: Callable[[ApprovalRequest], None]) -> None:
        self._notify_callback = notifier
        self._store.set_notifier(notifier)

    def list_pending(self) -> list[ApprovalRequest]:
        return self._store.list_pending()

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._store.get_request(request_id)

    def decide(self, request_id: str, approved: bool) -> ApprovalStatus:
        status = self._store.decide(request_id, approved)
        self._logger.info("Approval decision | id=%s | status=%s", request_id, status)
        return status

    async def request_and_wait(self, action: Action) -> ApprovalStatus:
        request = self._store.create_request(action.summary, action.risk)
        self._logger.info("Approval requested | id=%s | risk=%s | action=%s", request.request_id, action.risk, action.summary)
        status = await self._store.wait_for_decision(request.request_id)
        if status == ApprovalStatus.TIMED_OUT:
            self._logger.info("Approval timed out | id=%s", request.request_id)
        return status
