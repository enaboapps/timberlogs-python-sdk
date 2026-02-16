"""Tests for the Timberlogs client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from timberlogs import (
    Flow,
    LogEntry,
    LogOptions,
    TimberlogsClient,
    TimberlogsConfig,
    create_timberlogs,
)


class TestTimberlogsClient:
    """Tests for TimberlogsClient."""

    def test_create_client(self) -> None:
        """Test basic client creation."""
        config = TimberlogsConfig(
            source="test-app",
            environment="development",
        )
        client = TimberlogsClient(config)
        assert client is not None

    def test_create_timberlogs_factory(self) -> None:
        """Test the factory function."""
        client = create_timberlogs(
            source="test-app",
            environment="production",
        )
        assert client is not None

    def test_set_user_id(self) -> None:
        """Test setting user ID."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        result = client.set_user_id("user_123")
        assert result is client  # Returns self for chaining
        assert client._user_id == "user_123"

    def test_set_session_id(self) -> None:
        """Test setting session ID."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        result = client.set_session_id("sess_abc")
        assert result is client  # Returns self for chaining
        assert client._session_id == "sess_abc"

    def test_method_chaining(self) -> None:
        """Test method chaining."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        result = client.set_user_id("user_123").set_session_id("sess_abc")
        assert result is client
        assert client._user_id == "user_123"
        assert client._session_id == "sess_abc"

    def test_should_log(self) -> None:
        """Test should_log method."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="info",
        )

        assert client.should_log("debug") is False
        assert client.should_log("info") is True
        assert client.should_log("warn") is True
        assert client.should_log("error") is True

    def test_should_log_debug_level(self) -> None:
        """Test should_log with debug min level."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="debug",
        )

        assert client.should_log("debug") is True
        assert client.should_log("info") is True
        assert client.should_log("warn") is True
        assert client.should_log("error") is True

    def test_should_log_error_level(self) -> None:
        """Test should_log with error min level."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="error",
        )

        assert client.should_log("debug") is False
        assert client.should_log("info") is False
        assert client.should_log("warn") is False
        assert client.should_log("error") is True

    def test_build_log_payload(self) -> None:
        """Test building log payload."""
        client = create_timberlogs(
            source="my-service",
            environment="production",
            version="1.2.3",
        )
        client.set_user_id("user_123")
        client.set_session_id("sess_abc")

        entry = LogEntry(
            level="info",
            message="Test message",
            data={"key": "value"},
        )

        payload = client._build_log_payload(entry)

        assert payload["level"] == "info"
        assert payload["message"] == "Test message"
        assert payload["source"] == "my-service"
        assert payload["environment"] == "production"
        assert payload["version"] == "1.2.3"
        assert payload["userId"] == "user_123"
        assert payload["sessionId"] == "sess_abc"
        assert payload["data"] == {"key": "value"}

    def test_build_log_payload_entry_overrides(self) -> None:
        """Test that entry values override defaults."""
        client = create_timberlogs(
            source="my-service",
            environment="production",
        )
        client.set_user_id("default_user")

        entry = LogEntry(
            level="info",
            message="Test message",
            user_id="override_user",
        )

        payload = client._build_log_payload(entry)
        assert payload["userId"] == "override_user"


class TestFlow:
    """Tests for Flow tracking."""

    def test_create_flow(self) -> None:
        """Test creating a flow."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )

        flow = client.flow("checkout")
        assert flow.name == "checkout"
        assert flow.id.startswith("checkout-")

    def test_flow_id_format(self) -> None:
        """Test flow ID format."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )

        flow = client.flow("my-flow")
        # Format should be {name}-{8 hex chars}
        parts = flow.id.split("-")
        assert parts[0] == "my"
        assert parts[1] == "flow"
        assert len(parts[2]) == 8  # hex suffix

    def test_flow_properties(self) -> None:
        """Test flow properties."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )

        flow = client.flow("test-flow")
        assert flow.name == "test-flow"
        assert isinstance(flow.id, str)
        assert len(flow.id) > len("test-flow")

    def test_flow_step_index_increments(self) -> None:
        """Test that flow step index increments."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )

        flow = client.flow("test")
        assert flow._step_index == 0

        # Each log should increment step index
        flow.info("Step 1")
        assert flow._step_index == 1

        flow.info("Step 2")
        assert flow._step_index == 2

        flow.info("Step 3")
        assert flow._step_index == 3

    def test_flow_method_chaining(self) -> None:
        """Test flow method chaining."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )

        flow = client.flow("chained")
        result = flow.info("Step 1").info("Step 2").info("Step 3")

        assert result is flow
        assert flow._step_index == 3

    def test_flow_respects_min_level(self) -> None:
        """Test flow respects min_level filtering."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="info",
        )

        flow = client.flow("filtered")

        # Debug should not increment
        flow.debug("Filtered out")
        assert flow._step_index == 0

        # Info should increment
        flow.info("First log")
        assert flow._step_index == 1

        # Debug should still not increment
        flow.debug("Filtered out again")
        assert flow._step_index == 1

        # Info should increment
        flow.info("Second log")
        assert flow._step_index == 2


class TestLogEntry:
    """Tests for LogEntry."""

    def test_log_entry_to_dict(self) -> None:
        """Test LogEntry to_dict method."""
        entry = LogEntry(
            level="info",
            message="Test message",
            data={"key": "value"},
            user_id="user_123",
            session_id="sess_abc",
            request_id="req_xyz",
            tags=["tag1", "tag2"],
        )

        result = entry.to_dict()

        assert result["level"] == "info"
        assert result["message"] == "Test message"
        assert result["data"] == {"key": "value"}
        assert result["userId"] == "user_123"
        assert result["sessionId"] == "sess_abc"
        assert result["requestId"] == "req_xyz"
        assert result["tags"] == ["tag1", "tag2"]

    def test_log_entry_minimal(self) -> None:
        """Test LogEntry with minimal fields."""
        entry = LogEntry(
            level="debug",
            message="Minimal",
        )

        result = entry.to_dict()

        assert result == {
            "level": "debug",
            "message": "Minimal",
        }

    def test_log_entry_with_error(self) -> None:
        """Test LogEntry with error fields."""
        entry = LogEntry(
            level="error",
            message="Error occurred",
            error_name="ValueError",
            error_stack="Traceback...",
        )

        result = entry.to_dict()

        assert result["level"] == "error"
        assert result["errorName"] == "ValueError"
        assert result["errorStack"] == "Traceback..."

    def test_log_entry_with_flow(self) -> None:
        """Test LogEntry with flow fields."""
        entry = LogEntry(
            level="info",
            message="Flow step",
            flow_id="checkout-abc123",
            step_index=2,
        )

        result = entry.to_dict()

        assert result["flowId"] == "checkout-abc123"
        assert result["stepIndex"] == 2


class TestConfig:
    """Tests for configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        client = create_timberlogs(
            source="test",
            environment="development",
        )
        assert client._config.batch_size == 10
        assert client._config.flush_interval == 5.0
        assert client._config.min_level == "debug"

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        client = create_timberlogs(
            source="test",
            environment="production",
            batch_size=20,
            flush_interval=10.0,
            min_level="warn",
            max_retries=5,
            initial_delay_ms=2000,
            max_delay_ms=60000,
        )
        assert client._config.batch_size == 20
        assert client._config.flush_interval == 10.0
        assert client._config.min_level == "warn"
        assert client._config.retry["max_retries"] == 5
        assert client._config.retry["initial_delay_ms"] == 2000
        assert client._config.retry["max_delay_ms"] == 60000

    def test_config_with_api_key(self) -> None:
        """Test configuration with API key."""
        client = create_timberlogs(
            source="test",
            environment="production",
            api_key="tb_live_test",
        )
        assert client._config.api_key == "tb_live_test"
        assert client._http_client is not None
        client.disconnect()

    def test_config_without_api_key(self) -> None:
        """Test configuration without API key."""
        client = create_timberlogs(
            source="test",
            environment="development",
        )
        assert client._config.api_key is None
        assert client._http_client is None


class TestContextManager:
    """Tests for context manager usage."""

    def test_sync_context_manager(self) -> None:
        """Test synchronous context manager."""
        with create_timberlogs(
            source="test-app",
            environment="development",
        ) as client:
            assert client is not None

    def test_context_manager_disconnects(self) -> None:
        """Test that context manager disconnects on exit."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            api_key="tb_test_key",
        )

        with client:
            assert client._running is True

        assert client._running is False
        assert client._http_client is None


class TestAsyncClient:
    """Tests for async client methods."""

    async def test_flush_async_empty_queue(self) -> None:
        """Test flush_async with no queued logs."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
            api_key="tb_test_key",
        )
        await client.flush_async()
        assert len(client._queue) == 0
        client.disconnect()

    async def test_flush_async_no_api_key(self) -> None:
        """Test flush_async without API key skips sending."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        # Without API key, logs aren't queued (no HTTP transport)
        client.info("test message")
        await client.flush_async()
        assert client._async_http_client is None

    async def test_flush_async_sends_logs(self, httpx_mock) -> None:
        """Test flush_async sends queued logs via HTTP."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        )
        client.info("async log message")
        assert len(client._queue) == 1

        await client.flush_async()
        assert len(client._queue) == 0

        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].headers["X-API-Key"] == "tb_test_key"
        client.disconnect()

    async def test_flush_async_requeues_on_failure(self, httpx_mock) -> None:
        """Test flush_async re-queues logs on repeated failure."""
        for _ in range(8):
            httpx_mock.add_response(status_code=500)

        errors = []
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
            max_retries=3,
            initial_delay_ms=1,
            max_delay_ms=1,
            on_error=lambda e: errors.append(e),
        )
        client.info("will fail")
        await client.flush_async()

        assert len(client._queue) == 1
        assert len(errors) == 1
        await client.disconnect_async()

    async def test_flow_async_requires_api_key(self) -> None:
        """Test flow_async raises without API key."""
        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        with pytest.raises(RuntimeError, match="API key required"):
            await client.flow_async("test-flow")

    async def test_flow_async_creates_flow(self, httpx_mock) -> None:
        """Test flow_async creates a flow with server-generated ID."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/flows",
            method="POST",
            json={"flowId": "server-flow-123", "name": "checkout"},
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        )
        flow = await client.flow_async("checkout")
        assert flow.id == "server-flow-123"
        assert flow.name == "checkout"
        client.disconnect()

    async def test_flow_async_handles_invalid_response(self, httpx_mock) -> None:
        """Test flow_async raises on missing flowId in response."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/flows",
            method="POST",
            json={"unexpected": "data"},
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        )
        with pytest.raises(RuntimeError, match="missing flowId"):
            await client.flow_async("test")
        client.disconnect()

    async def test_flow_async_handles_http_error(self, httpx_mock) -> None:
        """Test flow_async raises on HTTP error."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/flows",
            method="POST",
            status_code=500,
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        )
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await client.flow_async("test")
        client.disconnect()

    async def test_disconnect_async(self, httpx_mock) -> None:
        """Test disconnect_async flushes and cleans up."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        )
        client.info("final log")
        await client.disconnect_async()

        assert client._running is False
        assert client._async_http_client is None
        assert len(client._queue) == 0

    async def test_async_context_manager(self, httpx_mock) -> None:
        """Test async context manager."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        async with create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_test_key",
        ) as client:
            client.info("inside async context")
            assert client._running is True

        assert client._running is False


class TestHTTPRequests:
    """Tests for HTTP request behavior using mocked HTTP.

    All tests use flush_interval=0 to disable the auto-flush timer,
    preventing background flushes from interfering with mock assertions.
    """

    def test_sync_flush_sends_correct_headers(self, httpx_mock) -> None:
        """Test that sync flush sends correct headers."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc123",
            flush_interval=0,
        )
        client.info("test message")
        client.flush()

        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].headers["Content-Type"] == "application/json"
        assert requests[0].headers["X-API-Key"] == "tb_live_abc123"
        client.disconnect()

    def test_sync_flush_sends_correct_payload(self, httpx_mock) -> None:
        """Test that sync flush sends correct log payload."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        client = create_timberlogs(
            source="my-service",
            environment="production",
            api_key="tb_live_abc",
            version="2.0.0",
            flush_interval=0,
        )
        client.set_user_id("user_42")
        client.info("Hello", {"key": "value"}, LogOptions(tags=["tag1"]))
        client.flush()

        requests = httpx_mock.get_requests()
        import json

        body = json.loads(requests[0].content)
        assert "logs" in body
        assert len(body["logs"]) == 1
        log = body["logs"][0]
        assert log["level"] == "info"
        assert log["message"] == "Hello"
        assert log["source"] == "my-service"
        assert log["environment"] == "production"
        assert log["version"] == "2.0.0"
        assert log["userId"] == "user_42"
        assert log["data"] == {"key": "value"}
        assert log["tags"] == ["tag1"]
        client.disconnect()

    def test_sync_flush_batches_multiple_logs(self, httpx_mock) -> None:
        """Test that multiple logs are batched in a single request."""
        httpx_mock.add_response(
            url="https://timberlogs-ingest.enaboapps.workers.dev/v1/logs",
            method="POST",
            status_code=200,
        )
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc",
            batch_size=100,
            flush_interval=0,
        )
        for i in range(5):
            client.info(f"Message {i}")
        client.flush()

        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        import json

        body = json.loads(requests[0].content)
        assert len(body["logs"]) == 5
        client.disconnect()

    def test_sync_flush_auto_triggers_on_batch_size(self, httpx_mock) -> None:
        """Test that flush triggers automatically when batch size is reached."""
        httpx_mock.add_response(status_code=200)
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc",
            batch_size=3,
            flush_interval=0,
        )
        client.info("msg 1")
        client.info("msg 2")
        assert len(httpx_mock.get_requests()) == 0

        client.info("msg 3")
        assert len(httpx_mock.get_requests()) == 1
        client.disconnect()

    def test_sync_flush_retry_with_backoff(self, httpx_mock) -> None:
        """Test that sync flush retries on failure with backoff."""
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=200)

        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc",
            max_retries=2,
            initial_delay_ms=1,
            max_delay_ms=1,
            flush_interval=0,
        )
        client.info("retry me")
        client.flush()

        assert len(httpx_mock.get_requests()) == 3
        assert len(client._queue) == 0
        client.disconnect()

    def test_sync_flush_requeues_after_all_retries_fail(self, httpx_mock) -> None:
        """Test that logs are re-queued when all retries fail."""
        for _ in range(8):
            httpx_mock.add_response(status_code=500)

        errors = []
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc",
            max_retries=3,
            initial_delay_ms=1,
            max_delay_ms=1,
            flush_interval=0,
            on_error=lambda e: errors.append(e),
        )
        client.info("will fail")
        client.flush()

        assert len(client._queue) == 1
        assert len(errors) == 1
        client.disconnect()

    def test_on_error_callback(self, httpx_mock) -> None:
        """Test that on_error callback is called on failure."""
        # 2 for flush (1 attempt + 1 retry) + 2 for disconnect flush
        for _ in range(4):
            httpx_mock.add_response(status_code=503)

        errors = []
        client = create_timberlogs(
            source="test-app",
            environment="production",
            api_key="tb_live_abc",
            max_retries=1,
            initial_delay_ms=1,
            max_delay_ms=1,
            flush_interval=0,
            on_error=lambda e: errors.append(str(e)),
        )
        client.info("error test")
        client.flush()

        assert len(errors) == 1
        assert "503" in errors[0]
        client.disconnect()
