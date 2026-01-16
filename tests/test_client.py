"""Tests for the Timberlogs client."""

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

    def test_log_levels(self) -> None:
        """Test all log level methods."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.debug("Debug message")
        client.info("Info message")
        client.warn("Warn message")
        client.error("Error message")
        client.flush()

        assert len(logs) == 4
        assert logs[0]["level"] == "debug"
        assert logs[1]["level"] == "info"
        assert logs[2]["level"] == "warn"
        assert logs[3]["level"] == "error"

    def test_log_with_data(self) -> None:
        """Test logging with data."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.info("Test message", {"key": "value", "number": 42})
        client.flush()

        assert len(logs) == 1
        assert logs[0]["data"] == {"key": "value", "number": 42}

    def test_log_with_tags(self) -> None:
        """Test logging with tags."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.info("Test message", None, LogOptions(tags=["tag1", "tag2"]))
        client.flush()

        assert len(logs) == 1
        assert logs[0]["tags"] == ["tag1", "tag2"]

    def test_error_with_exception(self) -> None:
        """Test error logging with Exception."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        try:
            raise ValueError("Test error")
        except Exception as e:
            client.error("Operation failed", e)

        client.flush()

        assert len(logs) == 1
        assert logs[0]["errorName"] == "ValueError"
        assert "ValueError: Test error" in logs[0]["errorStack"]
        assert logs[0]["data"]["message"] == "Test error"

    def test_set_user_id(self) -> None:
        """Test setting user ID."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.set_user_id("user_123")
        client.info("Test message")
        client.flush()

        assert len(logs) == 1
        assert logs[0]["userId"] == "user_123"

    def test_set_session_id(self) -> None:
        """Test setting session ID."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.set_session_id("sess_abc")
        client.info("Test message")
        client.flush()

        assert len(logs) == 1
        assert logs[0]["sessionId"] == "sess_abc"

    def test_method_chaining(self) -> None:
        """Test method chaining."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.set_user_id("user_123").set_session_id("sess_abc").info("Chained")
        client.flush()

        assert len(logs) == 1
        assert logs[0]["userId"] == "user_123"
        assert logs[0]["sessionId"] == "sess_abc"

    def test_min_level_filtering(self) -> None:
        """Test log level filtering."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="warn",
        )
        client.connect(create_batch_logs=capture_logs)

        client.debug("Not sent")
        client.info("Not sent")
        client.warn("Sent")
        client.error("Sent")
        client.flush()

        assert len(logs) == 2
        assert logs[0]["level"] == "warn"
        assert logs[1]["level"] == "error"

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

    def test_source_and_environment(self) -> None:
        """Test that source and environment are included in logs."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="my-service",
            environment="production",
        )
        client.connect(create_batch_logs=capture_logs)

        client.info("Test")
        client.flush()

        assert len(logs) == 1
        assert logs[0]["source"] == "my-service"
        assert logs[0]["environment"] == "production"

    def test_version_included(self) -> None:
        """Test that version is included when set."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
            version="1.2.3",
        )
        client.connect(create_batch_logs=capture_logs)

        client.info("Test")
        client.flush()

        assert len(logs) == 1
        assert logs[0]["version"] == "1.2.3"

    def test_batching(self) -> None:
        """Test that logs are batched."""
        batch_count = 0
        logs: list = []

        def capture_logs(batch: list) -> None:
            nonlocal batch_count
            batch_count += 1
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
            batch_size=3,
            flush_interval=0,  # Disable auto-flush
        )
        client.connect(create_batch_logs=capture_logs)

        # First 3 logs should trigger a flush
        client.info("Log 1")
        client.info("Log 2")
        client.info("Log 3")

        assert batch_count == 1
        assert len(logs) == 3

        # Next 2 logs won't trigger flush
        client.info("Log 4")
        client.info("Log 5")
        assert batch_count == 1

        # Manual flush
        client.flush()
        assert batch_count == 2
        assert len(logs) == 5

    def test_log_entry_direct(self) -> None:
        """Test logging with LogEntry directly."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        client.log(
            LogEntry(
                level="info",
                message="Direct log",
                data={"key": "value"},
                user_id="user_123",
                request_id="req_xyz",
                tags=["custom"],
            )
        )
        client.flush()

        assert len(logs) == 1
        assert logs[0]["message"] == "Direct log"
        assert logs[0]["userId"] == "user_123"
        assert logs[0]["requestId"] == "req_xyz"
        assert logs[0]["tags"] == ["custom"]


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

    def test_flow_logging(self) -> None:
        """Test logging within a flow."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("test-flow")
        flow.info("Step 1")
        flow.info("Step 2")
        flow.info("Step 3")
        client.flush()

        assert len(logs) == 3
        assert all(log["flowId"] == flow.id for log in logs)
        assert logs[0]["stepIndex"] == 0
        assert logs[1]["stepIndex"] == 1
        assert logs[2]["stepIndex"] == 2

    def test_flow_method_chaining(self) -> None:
        """Test flow method chaining."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("chained-flow")
        flow.info("Step 1").info("Step 2").info("Step 3")
        client.flush()

        assert len(logs) == 3

    def test_flow_all_levels(self) -> None:
        """Test all flow log levels."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("level-test")
        flow.debug("Debug")
        flow.info("Info")
        flow.warn("Warn")
        flow.error("Error")
        client.flush()

        assert len(logs) == 4
        assert logs[0]["level"] == "debug"
        assert logs[1]["level"] == "info"
        assert logs[2]["level"] == "warn"
        assert logs[3]["level"] == "error"

    def test_flow_error_with_exception(self) -> None:
        """Test flow error logging with Exception."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("error-test")

        try:
            raise RuntimeError("Flow error")
        except Exception as e:
            flow.error("Operation failed", e)

        client.flush()

        assert len(logs) == 1
        assert logs[0]["errorName"] == "RuntimeError"
        assert "RuntimeError: Flow error" in logs[0]["errorStack"]

    def test_flow_min_level_filtering(self) -> None:
        """Test flow respects min_level."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
            min_level="info",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("filtered-flow")
        flow.debug("Not sent")  # Filtered
        flow.info("First")  # stepIndex 0
        flow.debug("Not sent")  # Filtered
        flow.info("Second")  # stepIndex 1
        client.flush()

        assert len(logs) == 2
        # Step indices should be sequential without gaps
        assert logs[0]["stepIndex"] == 0
        assert logs[1]["stepIndex"] == 1

    def test_flow_with_data_and_tags(self) -> None:
        """Test flow logging with data and tags."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        client = create_timberlogs(
            source="test-app",
            environment="development",
        )
        client.connect(create_batch_logs=capture_logs)

        flow = client.flow("detailed-flow")
        flow.info("With data", {"key": "value"}, LogOptions(tags=["important"]))
        client.flush()

        assert len(logs) == 1
        assert logs[0]["data"] == {"key": "value"}
        assert logs[0]["tags"] == ["important"]


class TestContextManager:
    """Tests for context manager usage."""

    def test_sync_context_manager(self) -> None:
        """Test synchronous context manager."""
        logs: list = []

        def capture_logs(batch: list) -> None:
            logs.extend(batch)

        with create_timberlogs(
            source="test-app",
            environment="development",
        ) as client:
            client.connect(create_batch_logs=capture_logs)
            client.info("Inside context")

        # Should auto-flush on exit
        assert len(logs) == 1


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
