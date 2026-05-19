import logging
import sys
from typing import Optional

from config import get_settings

settings = get_settings()


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    config_level = getattr(settings, 'LOG_LEVEL', 'INFO')
    logger.setLevel(getattr(logging, (level or config_level).upper()))

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) -> %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = setup_logger("tg_parser")
