"""Async usage example for the Timberlogs Python SDK."""

import asyncio
import os

from timberlogs import create_timberlogs


async def main() -> None:
    """Demonstrate async logging capabilities."""

    # Create a client
    timber = create_timberlogs(
        source="async-example",
        environment="development",
        api_key=os.getenv("TIMBER_API_KEY"),
    )

    # Basic async logging (logs are queued synchronously, sent async)
    timber.info("Starting async operation")

    # Create an async flow with server-generated ID
    try:
        flow = await timber.flow_async("async-job")
        print(f"Created flow with server ID: {flow.id}")

        flow.info("Async job started")

        # Simulate async work
        await asyncio.sleep(0.1)
        flow.info("Processing step 1")

        await asyncio.sleep(0.1)
        flow.info("Processing step 2")

        await asyncio.sleep(0.1)
        flow.info("Async job completed")

    except RuntimeError as e:
        # Fall back to local flow if no API key
        print(f"Using local flow (API key not configured): {e}")
        flow = timber.flow("async-job")
        flow.info("Async job with local flow ID")

    # Async flush
    await timber.flush_async()

    # Async disconnect
    await timber.disconnect_async()

    print("Async operations completed!")


async def context_manager_example() -> None:
    """Demonstrate async context manager usage."""

    async with create_timberlogs(
        source="async-context-example",
        environment="development",
        api_key=os.getenv("TIMBER_API_KEY"),
    ) as timber:
        timber.info("Inside async context manager")
        timber.info("Auto-flushed on exit")

    print("Context manager example completed!")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())

    print()

    # Run context manager example
    asyncio.run(context_manager_example())
