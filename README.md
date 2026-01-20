# Timberlogs Python SDK

The official Timberlogs SDK for Python applications. Send structured logs to [Timberlogs](https://timberlogs.dev) with automatic batching, retry logic, and flow tracking.

## Installation

```bash
pip install timberlogs
```

## Quick Start

```python
from timberlogs import create_timberlogs

timber = create_timberlogs(
    source="my-app",
    environment="production",
    api_key="tb_live_xxxxxxxxxxxxx",
)

timber.info("Hello, Timberlogs!")
```

## Features

- **Structured logging** - Log with arbitrary JSON data
- **Automatic batching** - Efficiently batch logs before sending
- **Retry with backoff** - Automatic retry on failures
- **Flow tracking** - Group related logs together
- **Level filtering** - Filter logs by severity
- **Async support** - Full async/await support
- **Context manager** - Automatic cleanup with `with` statement

## Basic Usage

### Log Levels

```python
timber.debug("Detailed diagnostic info", {"key": "value"})
timber.info("General information", {"user_id": "123"})
timber.warn("Warning condition", {"threshold": 90})
timber.error("Error occurred", {"code": "E001"})
```

### Logging with Data

```python
timber.info("User signed in", {
    "user_id": "user_123",
    "method": "oauth",
    "provider": "google",
})
```

### Error Logging

```python
# With Exception object (extracts name, message, stack)
try:
    risky_operation()
except Exception as e:
    timber.error("Operation failed", e)

# With data object
timber.error("Validation failed", {
    "field": "email",
    "reason": "invalid format",
})
```

### Tags

```python
from timberlogs import LogOptions

timber.info("Payment processed", {"amount": 99.99}, LogOptions(tags=["payments", "success"]))
```

### Setting User/Session IDs

```python
# Set defaults for all subsequent logs
timber.set_user_id("user_123")
timber.set_session_id("sess_abc")

# Clear on logout
timber.set_user_id(None)
timber.set_session_id(None)
```

### Method Chaining

```python
timber.set_user_id("user_123").set_session_id("sess_abc").info("User action")
```

## Flow Tracking

Flows group related logs together with automatic step indexing:

```python
# Synchronous flow (local ID generation)
flow = timber.flow("checkout")
flow.info("Started checkout", {"items": 3})
flow.info("Payment processed", {"amount": 99.99})
flow.info("Order confirmed", {"order_id": "ord_123"})
```

### Async Flow (Server-Generated ID)

```python
import asyncio

async def process_checkout():
    flow = await timber.flow_async("checkout")
    flow.info("Started checkout")
    flow.info("Payment processed")
    flow.info("Order confirmed")

asyncio.run(process_checkout())
```

### Flow Properties

```python
flow = timber.flow("user-onboarding")
print(flow.id)    # "user-onboarding-a1b2c3d4"
print(flow.name)  # "user-onboarding"
```

## Configuration

### All Options

```python
from timberlogs import create_timberlogs

timber = create_timberlogs(
    # Required
    source="my-app",                    # Your app/service name
    environment="production",           # development, staging, production

    # Authentication
    api_key="tb_live_xxx",              # Your Timberlogs API key

    # Optional
    endpoint="https://...",             # Custom endpoint URL
    version="1.2.3",                    # Your app version
    user_id="user_123",                 # Default user ID
    session_id="sess_abc",              # Default session ID
    batch_size=10,                      # Logs to batch before sending
    flush_interval=5.0,                 # Auto-flush interval (seconds)
    min_level="info",                   # Minimum level to send
    on_error=lambda e: print(e),        # Error callback

    # Retry configuration
    max_retries=3,                      # Retry attempts
    initial_delay_ms=1000,              # Initial retry delay
    max_delay_ms=30000,                 # Maximum retry delay
)
```

### Environment Variables

```python
import os
from timberlogs import create_timberlogs

timber = create_timberlogs(
    source="my-app",
    environment=os.getenv("ENVIRONMENT", "development"),
    api_key=os.getenv("TIMBER_API_KEY"),
)
```

### Level Filtering

```python
timber = create_timberlogs(
    source="my-app",
    environment="production",
    api_key="tb_live_xxx",
    min_level="warn",  # Only send warn and error
)

timber.debug("Not sent")  # Filtered
timber.info("Not sent")   # Filtered
timber.warn("Sent")       # Sent
timber.error("Sent")      # Sent
```

## Async Usage

```python
import asyncio
from timberlogs import create_timberlogs

async def main():
    timber = create_timberlogs(
        source="my-app",
        environment="production",
        api_key="tb_live_xxx",
    )

    timber.info("Starting async operation")

    # Create async flow with server-generated ID
    flow = await timber.flow_async("async-job")
    flow.info("Step 1")
    flow.info("Step 2")

    # Async flush
    await timber.flush_async()

    # Async disconnect
    await timber.disconnect_async()

asyncio.run(main())
```

### Async Context Manager

```python
async def main():
    async with create_timberlogs(
        source="my-app",
        environment="production",
        api_key="tb_live_xxx",
    ) as timber:
        timber.info("Auto-flushed on exit")
```

## Context Manager

```python
with create_timberlogs(
    source="my-app",
    environment="production",
    api_key="tb_live_xxx",
) as timber:
    timber.info("Logs are auto-flushed on exit")
```

## Low-Level Logging

For full control over log entries:

```python
from timberlogs import LogEntry

timber.log(LogEntry(
    level="info",
    message="Custom log entry",
    data={"custom": "data"},
    user_id="user_123",
    session_id="sess_abc",
    request_id="req_xyz",
    tags=["important", "billing"],
))
```

## API Reference

### TimberlogsClient Methods

| Method | Description |
|--------|-------------|
| `debug(message, data?, options?)` | Log debug message |
| `info(message, data?, options?)` | Log info message |
| `warn(message, data?, options?)` | Log warning message |
| `error(message, error_or_data?, options?)` | Log error message |
| `log(entry)` | Log with full control |
| `flow(name)` | Create flow (local ID) |
| `flow_async(name)` | Create flow (server ID) |
| `set_user_id(user_id)` | Set default user ID |
| `set_session_id(session_id)` | Set default session ID |
| `flush()` | Send queued logs immediately |
| `flush_async()` | Async send queued logs |
| `disconnect()` | Flush and stop client |
| `disconnect_async()` | Async flush and stop |
| `should_log(level)` | Check if level passes filter |

### Flow Methods

| Method | Description |
|--------|-------------|
| `debug(message, data?, options?)` | Log debug message |
| `info(message, data?, options?)` | Log info message |
| `warn(message, data?, options?)` | Log warning message |
| `error(message, error_or_data?, options?)` | Log error message |
| `id` | Property: flow ID |
| `name` | Property: flow name |

## Requirements

- Python 3.8+
- httpx >= 0.24.0

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Documentation](https://docs.timberlogs.dev)
- [Dashboard](https://app.timberlogs.dev)
- [GitHub](https://github.com/enaboapps/timberlogs-python-sdk)
