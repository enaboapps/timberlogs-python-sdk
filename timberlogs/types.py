"""Type definitions for the Timberlogs SDK."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict

# Type aliases
LogLevel = Literal["debug", "info", "warn", "error"]
Environment = Literal["development", "staging", "production"]


class RetryConfig(TypedDict, total=False):
    """Configuration for retry behavior."""

    max_retries: int
    initial_delay_ms: int
    max_delay_ms: int


class LogEntryDict(TypedDict, total=False):
    """Dictionary representation of a log entry for API calls."""

    level: LogLevel
    message: str
    source: str
    environment: Environment
    version: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    data: Optional[Dict[str, Any]]
    error_name: Optional[str]
    error_stack: Optional[str]
    tags: Optional[List[str]]
    flow_id: Optional[str]
    step_index: Optional[int]


@dataclass
class LogEntry:
    """A log entry to be sent to Timberlogs."""

    level: LogLevel
    message: str
    data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    error_name: Optional[str] = None
    error_stack: Optional[str] = None
    tags: Optional[List[str]] = None
    flow_id: Optional[str] = None
    step_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        result: Dict[str, Any] = {
            "level": self.level,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.user_id is not None:
            result["userId"] = self.user_id
        if self.session_id is not None:
            result["sessionId"] = self.session_id
        if self.request_id is not None:
            result["requestId"] = self.request_id
        if self.error_name is not None:
            result["errorName"] = self.error_name
        if self.error_stack is not None:
            result["errorStack"] = self.error_stack
        if self.tags is not None:
            result["tags"] = self.tags
        if self.flow_id is not None:
            result["flowId"] = self.flow_id
        if self.step_index is not None:
            result["stepIndex"] = self.step_index
        return result


@dataclass
class LogOptions:
    """Options that can be passed to logging methods."""

    tags: Optional[List[str]] = None


@dataclass
class TimberlogsConfig:
    """Configuration for the Timberlogs client."""

    source: str
    environment: Environment
    api_key: Optional[str] = None
    endpoint: str = "https://timberlogs-ingest.enaboapps.workers.dev/v1/logs"
    version: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    batch_size: int = 10
    flush_interval: float = 5.0  # seconds
    min_level: LogLevel = "debug"
    on_error: Optional[Callable[[Exception], None]] = None
    retry: RetryConfig = field(
        default_factory=lambda: {
            "max_retries": 3,
            "initial_delay_ms": 1000,
            "max_delay_ms": 30000,
        }
    )


# Log level priority for filtering
LOG_LEVEL_PRIORITY: Dict[LogLevel, int] = {
    "debug": 0,
    "info": 1,
    "warn": 2,
    "error": 3,
}


__all__ = [
    "LogLevel",
    "Environment",
    "RetryConfig",
    "LogEntry",
    "LogEntryDict",
    "LogOptions",
    "TimberlogsConfig",
    "LOG_LEVEL_PRIORITY",
]
