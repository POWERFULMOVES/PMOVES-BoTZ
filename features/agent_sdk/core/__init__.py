"""
Core Utilities - Shared across all vertical slices.

Contains only truly shared code:
- Configuration loading
- Logging setup
- HTTP client factory
- Event publishing
"""

from .config import Config, load_config
from .logging import setup_logging, get_logger
from .events import EventPublisher

__all__ = [
    "Config",
    "load_config",
    "setup_logging",
    "get_logger",
    "EventPublisher",
]
