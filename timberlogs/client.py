"""Timberlogs client implementation."""

from __future__ import annotations

import asyncio
import threading
import traceback
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import httpx

from .types import (
    LOG_LEVEL_PRIORITY,
    Environment,
    LogEntry,
    LogLevel,
    LogOptions,
    TimberlogsConfig,
)

T = TypeVar("T", bound="TimberlogsClient")
F = TypeVar("F", bound="Flow")

# Default endpoints
LOGS_ENDPOINT = "https://timberlogs-ingest.enaboapps.workers.dev/v1/logs"
FLOWS_ENDPOINT = "https://timberlogs-ingest.enaboapps.workers.dev/v1/flows"


class Flow:
    """
    A flow for tracking related logs across a multi-step process.

    Flows automatically track step indices and group logs with a unique flow ID.
    """

    def __init__(
        self,
        flow_id: str,
        name: str,
        client: "TimberlogsClient",
    ) -> None:
        """Initialize a new Flow.

        Args:
            flow_id: The unique flow identifier.
            name: The human-readable flow name.
            client: The parent TimberlogsClient instance.
        """
        self._id = flow_id
        self._name = name
        self._client = client
        self._step_index = 0

    @property
    def id(self) -> str:
        """Get the flow ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the flow name."""
        return self._name

    def _log(
        self,
        level: LogLevel,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
        error: Optional[Exception] = None,
    ) -> "Flow":
        """Internal logging method."""
        if not self._client.should_log(level):
            return self

        entry = LogEntry(
            level=level,
            message=message,
            data=data,
            tags=options.tags if options else None,
            flow_id=self._id,
            step_index=self._step_index,
        )

        # Handle error objects
        if error is not None:
            entry.error_name = type(error).__name__
            entry.error_stack = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            if entry.data is None:
                entry.data = {}
            entry.data["message"] = str(error)

        self._client.log(entry)
        self._step_index += 1
        return self

    def debug(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "Flow":
        """Log a debug message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self._log("debug", message, data, options)

    def info(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "Flow":
        """Log an info message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self._log("info", message, data, options)

    def warn(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "Flow":
        """Log a warning message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self._log("warn", message, data, options)

    def error(
        self,
        message: str,
        error_or_data: Optional[Union[Exception, Dict[str, Any]]] = None,
        options: Optional[LogOptions] = None,
    ) -> "Flow":
        """Log an error message.

        Args:
            message: The log message.
            error_or_data: An Exception object or data dictionary.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        if isinstance(error_or_data, Exception):
            return self._log("error", message, None, options, error=error_or_data)
        return self._log("error", message, error_or_data, options)


class TimberlogsClient:
    """
    The main Timberlogs client for sending structured logs.

    Example:
        >>> timber = TimberlogsClient(TimberlogsConfig(
        ...     source="my-app",
        ...     environment="production",
        ...     api_key="tb_live_xxx",
        ... ))
        >>> timber.info("User signed in", {"user_id": "123"})
    """

    def __init__(self, config: TimberlogsConfig) -> None:
        """Initialize the Timberlogs client.

        Args:
            config: The client configuration.
        """
        self._config = config
        self._queue: List[Dict[str, Any]] = []
        self._user_id = config.user_id
        self._session_id = config.session_id
        self._http_client: Optional[httpx.Client] = None
        self._async_http_client: Optional[httpx.AsyncClient] = None
        self._flush_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = False

        # Custom backend functions
        self._create_log: Optional[Callable[[Dict[str, Any]], None]] = None
        self._create_batch_logs: Optional[Callable[[List[Dict[str, Any]]], None]] = None

        # Start HTTP transport if API key provided
        if config.api_key:
            self._start_http_transport()

    def _start_http_transport(self) -> None:
        """Start the HTTP transport for sending logs."""
        self._http_client = httpx.Client(timeout=30.0)
        self._running = True
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        """Schedule the next auto-flush."""
        if self._running and self._config.flush_interval > 0:
            self._flush_timer = threading.Timer(
                self._config.flush_interval, self._auto_flush
            )
            self._flush_timer.daemon = True
            self._flush_timer.start()

    def _auto_flush(self) -> None:
        """Auto-flush callback."""
        try:
            self.flush()
        finally:
            self._schedule_flush()

    def connect(
        self,
        create_log: Optional[Callable[[Dict[str, Any]], None]] = None,
        create_batch_logs: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> "TimberlogsClient":
        """Connect to a custom backend.

        Args:
            create_log: Function to handle single log entries.
            create_batch_logs: Function to handle batched log entries.

        Returns:
            self for method chaining.
        """
        self._create_log = create_log
        self._create_batch_logs = create_batch_logs
        return self

    def should_log(self, level: LogLevel) -> bool:
        """Check if a log level should be sent based on min_level config.

        Args:
            level: The log level to check.

        Returns:
            True if the log should be sent.
        """
        return LOG_LEVEL_PRIORITY[level] >= LOG_LEVEL_PRIORITY[self._config.min_level]

    def set_user_id(self, user_id: Optional[str]) -> "TimberlogsClient":
        """Set the default user ID for subsequent logs.

        Args:
            user_id: The user ID to set, or None to clear.

        Returns:
            self for method chaining.
        """
        self._user_id = user_id
        return self

    def set_session_id(self, session_id: Optional[str]) -> "TimberlogsClient":
        """Set the default session ID for subsequent logs.

        Args:
            session_id: The session ID to set, or None to clear.

        Returns:
            self for method chaining.
        """
        self._session_id = session_id
        return self

    def _build_log_payload(self, entry: LogEntry) -> Dict[str, Any]:
        """Build the full log payload with config defaults."""
        payload = entry.to_dict()
        payload["source"] = self._config.source
        payload["environment"] = self._config.environment

        if self._config.version:
            payload["version"] = self._config.version

        # Apply defaults if not set in entry
        if "userId" not in payload and self._user_id:
            payload["userId"] = self._user_id
        if "sessionId" not in payload and self._session_id:
            payload["sessionId"] = self._session_id

        return payload

    def log(self, entry: LogEntry) -> "TimberlogsClient":
        """Log an entry with full control.

        Args:
            entry: The log entry to send.

        Returns:
            self for method chaining.
        """
        if not self.should_log(entry.level):
            return self

        payload = self._build_log_payload(entry)

        # If custom backend, use it
        if self._create_log or self._create_batch_logs:
            if self._create_batch_logs:
                with self._lock:
                    self._queue.append(payload)
                    if len(self._queue) >= self._config.batch_size:
                        self._flush_custom()
            elif self._create_log:
                self._create_log(payload)
            return self

        # Queue for HTTP transport
        with self._lock:
            self._queue.append(payload)
            if len(self._queue) >= self._config.batch_size:
                self._flush_http()

        return self

    def debug(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "TimberlogsClient":
        """Log a debug message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self.log(
            LogEntry(
                level="debug",
                message=message,
                data=data,
                tags=options.tags if options else None,
            )
        )

    def info(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "TimberlogsClient":
        """Log an info message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self.log(
            LogEntry(
                level="info",
                message=message,
                data=data,
                tags=options.tags if options else None,
            )
        )

    def warn(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        options: Optional[LogOptions] = None,
    ) -> "TimberlogsClient":
        """Log a warning message.

        Args:
            message: The log message.
            data: Optional data to include with the log.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        return self.log(
            LogEntry(
                level="warn",
                message=message,
                data=data,
                tags=options.tags if options else None,
            )
        )

    def error(
        self,
        message: str,
        error_or_data: Optional[Union[Exception, Dict[str, Any]]] = None,
        options: Optional[LogOptions] = None,
    ) -> "TimberlogsClient":
        """Log an error message.

        Args:
            message: The log message.
            error_or_data: An Exception object or data dictionary.
            options: Optional logging options (e.g., tags).

        Returns:
            self for method chaining.
        """
        entry = LogEntry(
            level="error",
            message=message,
            tags=options.tags if options else None,
        )

        if isinstance(error_or_data, Exception):
            entry.error_name = type(error_or_data).__name__
            entry.error_stack = "".join(
                traceback.format_exception(
                    type(error_or_data), error_or_data, error_or_data.__traceback__
                )
            )
            entry.data = {"message": str(error_or_data)}
        elif error_or_data is not None:
            entry.data = error_or_data

        return self.log(entry)

    def _flush_custom(self) -> None:
        """Flush logs to custom backend."""
        with self._lock:
            if not self._queue:
                return
            logs = self._queue.copy()
            self._queue.clear()

        if self._create_batch_logs:
            try:
                self._create_batch_logs(logs)
            except Exception as e:
                self._handle_error(e, logs)

    def _flush_http(self) -> None:
        """Flush logs via HTTP with retry logic."""
        with self._lock:
            if not self._queue:
                return
            logs = self._queue.copy()
            self._queue.clear()

        if not self._http_client or not self._config.api_key:
            return

        retry_config = self._config.retry
        max_retries = retry_config.get("max_retries", 3)
        initial_delay_ms = retry_config.get("initial_delay_ms", 1000)
        max_delay_ms = retry_config.get("max_delay_ms", 30000)

        delay_ms = initial_delay_ms
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                response = self._http_client.post(
                    self._config.endpoint,
                    json={"logs": logs},
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self._config.api_key,
                    },
                )
                response.raise_for_status()
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(delay_ms / 1000)
                    delay_ms = min(delay_ms * 2, max_delay_ms)

        # All retries failed, re-queue logs and handle error
        with self._lock:
            self._queue = logs + self._queue

        if last_error:
            self._handle_error(last_error, logs)

    def _handle_error(
        self, error: Exception, logs: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Handle a flush error."""
        if self._config.on_error:
            self._config.on_error(error)
        else:
            print(f"Timberlogs error: {error}")

    def flush(self) -> None:
        """Immediately send all queued logs."""
        if self._create_batch_logs:
            self._flush_custom()
        else:
            self._flush_http()

    async def flush_async(self) -> None:
        """Asynchronously send all queued logs."""
        with self._lock:
            if not self._queue:
                return
            logs = self._queue.copy()
            self._queue.clear()

        if not self._config.api_key:
            return

        if self._async_http_client is None:
            self._async_http_client = httpx.AsyncClient(timeout=30.0)

        retry_config = self._config.retry
        max_retries = retry_config.get("max_retries", 3)
        initial_delay_ms = retry_config.get("initial_delay_ms", 1000)
        max_delay_ms = retry_config.get("max_delay_ms", 30000)

        delay_ms = initial_delay_ms
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._async_http_client.post(
                    self._config.endpoint,
                    json={"logs": logs},
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self._config.api_key,
                    },
                )
                response.raise_for_status()
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(delay_ms / 1000)
                    delay_ms = min(delay_ms * 2, max_delay_ms)

        # All retries failed, re-queue logs and handle error
        with self._lock:
            self._queue = logs + self._queue

        if last_error:
            self._handle_error(last_error, logs)

    def flow(self, name: str) -> Flow:
        """Create a new flow for tracking related logs synchronously.

        Note: This creates the flow locally. For server-side flow ID generation,
        use flow_async().

        Args:
            name: The name for the flow.

        Returns:
            A new Flow instance.
        """
        # Generate a local flow ID
        import secrets

        suffix = secrets.token_hex(4)
        flow_id = f"{name}-{suffix}"
        return Flow(flow_id, name, self)

    async def flow_async(self, name: str) -> Flow:
        """Create a new flow with server-generated flow ID.

        Args:
            name: The name for the flow.

        Returns:
            A new Flow instance with server-generated ID.

        Raises:
            RuntimeError: If no API key is configured.
        """
        if not self._config.api_key:
            raise RuntimeError("API key required for async flow creation")

        if self._async_http_client is None:
            self._async_http_client = httpx.AsyncClient(timeout=30.0)

        response = await self._async_http_client.post(
            FLOWS_ENDPOINT,
            json={"name": name},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self._config.api_key,
            },
        )
        response.raise_for_status()
        data = response.json()

        return Flow(data["flowId"], data["name"], self)

    def disconnect(self) -> None:
        """Flush logs and stop the client."""
        self._running = False
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

        self.flush()

        if self._http_client:
            self._http_client.close()
            self._http_client = None

    async def disconnect_async(self) -> None:
        """Asynchronously flush logs and stop the client."""
        self._running = False
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

        await self.flush_async()

        if self._async_http_client:
            await self._async_http_client.aclose()
            self._async_http_client = None

        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "TimberlogsClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - flush and disconnect."""
        self.disconnect()

    async def __aenter__(self) -> "TimberlogsClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - flush and disconnect."""
        await self.disconnect_async()


def create_timberlogs(
    source: str,
    environment: Environment,
    api_key: Optional[str] = None,
    endpoint: str = LOGS_ENDPOINT,
    version: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    batch_size: int = 10,
    flush_interval: float = 5.0,
    min_level: LogLevel = "debug",
    on_error: Optional[Callable[[Exception], None]] = None,
    max_retries: int = 3,
    initial_delay_ms: int = 1000,
    max_delay_ms: int = 30000,
) -> TimberlogsClient:
    """Create a new Timberlogs client.

    This is the recommended way to create a client instance.

    Args:
        source: Your application or service name.
        environment: The environment (development, staging, production).
        api_key: Your Timberlogs API key (starts with tb_live_ or tb_test_).
        endpoint: The ingestion endpoint URL.
        version: Your application version.
        user_id: Default user ID for all logs.
        session_id: Default session ID for all logs.
        batch_size: Number of logs to batch before sending.
        flush_interval: Auto-flush interval in seconds.
        min_level: Minimum log level to send.
        on_error: Callback for handling errors.
        max_retries: Maximum retry attempts for failed requests.
        initial_delay_ms: Initial delay between retries in milliseconds.
        max_delay_ms: Maximum delay between retries in milliseconds.

    Returns:
        A configured TimberlogsClient instance.

    Example:
        >>> timber = create_timberlogs(
        ...     source="my-app",
        ...     environment="production",
        ...     api_key="tb_live_xxx",
        ... )
        >>> timber.info("Hello, Timberlogs!")
    """
    config = TimberlogsConfig(
        source=source,
        environment=environment,
        api_key=api_key,
        endpoint=endpoint,
        version=version,
        user_id=user_id,
        session_id=session_id,
        batch_size=batch_size,
        flush_interval=flush_interval,
        min_level=min_level,
        on_error=on_error,
        retry={
            "max_retries": max_retries,
            "initial_delay_ms": initial_delay_ms,
            "max_delay_ms": max_delay_ms,
        },
    )
    return TimberlogsClient(config)


__all__ = [
    "Flow",
    "TimberlogsClient",
    "create_timberlogs",
]
