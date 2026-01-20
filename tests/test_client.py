"""Tests for the Timberlogs client."""

from unittest.mock import MagicMock, patch

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
