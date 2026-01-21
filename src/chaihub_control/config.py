import os


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


TELEGRAM_BOT_TOKEN = require_env("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(require_env("AUTHORIZED_USER_ID"))
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))
LOG_PATH = os.getenv("LOG_PATH", "logs/control.log")
