import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("chaihub_control")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=2)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
