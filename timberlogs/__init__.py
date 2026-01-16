"""
Timberlogs - Structured logging made simple.

The official Timberlogs SDK for Python applications.

Example:
    >>> from timberlogs import create_timberlogs
    >>> timber = create_timberlogs(
    ...     source="my-app",
    ...     environment="production",
    ...     api_key="tb_live_xxx",
    ... )
    >>> timber.info("Hello, Timberlogs!")
"""

from .client import Flow, TimberlogsClient, create_timberlogs
from .types import (
    Environment,
    LogEntry,
    LogLevel,
    LogOptions,
    TimberlogsConfig,
)

__version__ = "1.0.0"

__all__ = [
    # Factory function
    "create_timberlogs",
    # Classes
    "TimberlogsClient",
    "Flow",
    # Types and config
    "LogLevel",
    "Environment",
    "LogEntry",
    "LogOptions",
    "TimberlogsConfig",
    # Version
    "__version__",
]
