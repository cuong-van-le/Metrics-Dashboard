import logging
import os


def setup_logging(
    level: str | None = None,
    format_string: str | None = None,
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
