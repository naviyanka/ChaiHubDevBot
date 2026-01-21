import asyncio

from .approval import ApprovalStore
from .approval_service import ApprovalService
from .bot import TelegramBot
from .config import APPROVAL_TIMEOUT_SECONDS, AUTHORIZED_USER_ID, LOG_PATH, TELEGRAM_BOT_TOKEN
from .executor import Executor
from .logging_utils import setup_logging
from .planner import Planner


async def planner_loop(planner: Planner, executor: Executor, approval_service: ApprovalService) -> None:
    logger = setup_logging(LOG_PATH)
    while not executor.is_stopped():
        prompt = await planner.next_prompt()
        if executor.is_stopped():
            break
        actions = planner.plan(prompt)
        logger.info("Plan created | goal=%s | actions=%s", prompt, len(actions))
        for action in actions:
            if executor.is_stopped():
                break
            if planner.was_interrupted():
                logger.info("Plan interrupted | new prompt received")
                break
            logger.info("Execution start | action=%s", action.summary)
            status = await executor.execute(action, approval_service)
            logger.info("Execution end | action=%s | status=%s", action.summary, status)
            if planner.was_interrupted():
                logger.info("Plan interrupted after action | new prompt received")
                break


async def main() -> None:
    logger = setup_logging(LOG_PATH)
    logger.info("System initializing")
    planner = Planner()
    executor = Executor()
    approval_store = ApprovalStore(timeout_seconds=APPROVAL_TIMEOUT_SECONDS)
    approval_service = ApprovalService(approval_store, LOG_PATH)
    bot = TelegramBot(
        token=TELEGRAM_BOT_TOKEN,
        authorized_user_id=AUTHORIZED_USER_ID,
        planner=planner,
        executor=executor,
        approval_service=approval_service,
    )

    await bot.start()
    try:
        await planner_loop(planner, executor, approval_service)
    finally:
        await bot.stop()
        logger.info("System stopped")


if __name__ == "__main__":
    asyncio.run(main())
