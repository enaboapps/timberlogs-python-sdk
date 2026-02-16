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
    dataset: Optional[str]
    ip_address: Optional[str]
    country: Optional[str]


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
    dataset: Optional[str] = None
    ip_address: Optional[str] = None
    country: Optional[str] = None

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
        if self.dataset is not None:
            result["dataset"] = self.dataset
        if self.ip_address is not None:
            result["ipAddress"] = self.ip_address
        if self.country is not None:
            result["country"] = self.country
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
    dataset: Optional[str] = None
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


class ValidationError(ValueError):
    """Raised when a log entry or config value fails validation."""


def validate_log_payload(payload: Dict[str, Any]) -> None:
    """Validate a log payload against API constraints.

    Raises:
        ValidationError: If any field exceeds API limits.
    """
    _check_str(payload, "message", 1, 10_000)
    _check_str(payload, "source", 1, 100)
    _check_str(payload, "environment", 1, 50)
    _check_str(payload, "errorName", 0, 200)
    _check_str(payload, "errorStack", 0, 10_000)
    _check_str(payload, "userId", 0, 100)
    _check_str(payload, "sessionId", 0, 100)
    _check_str(payload, "requestId", 0, 100)
    _check_str(payload, "version", 0, 50)
    _check_str(payload, "dataset", 0, 50)
    _check_str(payload, "flowId", 0, 50)

    if "stepIndex" in payload:
        step = payload["stepIndex"]
        if not isinstance(step, int) or step < 0 or step > 1000:
            raise ValidationError(f"stepIndex must be 0-1000, got {step}")

    tags = payload.get("tags")
    if tags is not None:
        if len(tags) > 20:
            raise ValidationError(f"tags must have at most 20 items, got {len(tags)}")
        for i, tag in enumerate(tags):
            if len(tag) > 50:
                raise ValidationError(
                    f"tags[{i}] exceeds 50 characters: {len(tag)}"
                )


def _check_str(
    payload: Dict[str, Any], key: str, min_len: int, max_len: int
) -> None:
    value = payload.get(key)
    if value is None:
        return
    if not isinstance(value, str):
        return
    if min_len > 0 and len(value) < min_len:
        raise ValidationError(
            f"{key} must be at least {min_len} character(s), got {len(value)}"
        )
    if len(value) > max_len:
        raise ValidationError(
            f"{key} exceeds {max_len} characters: {len(value)}"
        )


__all__ = [
    "LogLevel",
    "Environment",
    "RetryConfig",
    "LogEntry",
    "LogEntryDict",
    "LogOptions",
    "TimberlogsConfig",
    "LOG_LEVEL_PRIORITY",
    "ValidationError",
    "validate_log_payload",
]
