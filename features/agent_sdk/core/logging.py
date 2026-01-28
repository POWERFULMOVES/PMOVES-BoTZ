"""
Core Logging - Standardized logging setup.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Set up standardized logging for PMOVES Agent SDK.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string
        log_file: Optional file path for logging
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
    )

    # Set third-party loggers to WARNING
    for name in ["httpx", "httpcore", "urllib3"]:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the PMOVES Agent SDK namespace.

    Args:
        name: Logger name (will be prefixed with 'pmoves_agent.')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"pmoves_agent.{name}")
