"""Logging configuration for the prediction engine."""

import logging
import sys
from typing import Optional

from fifa26_engine.config import get_settings

_CONFIGURED = False


def configure_logging(level: Optional[str] = None) -> None:
    """Configure root logging once with a consistent format.

    Args:
        level: Optional log level override. Defaults to ``Settings.log_level``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    log_level = (level or settings.log_level).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring logging is configured first."""
    configure_logging()
    return logging.getLogger(name)
