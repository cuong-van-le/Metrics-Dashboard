import logging
import os
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    force: bool = False,
) -> None:
    if not force and logging.root.handlers:
        return

    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()

    default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_format = format_string or default_format

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        force=force,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
