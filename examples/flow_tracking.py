"""Flow tracking example for the Timberlogs Python SDK."""

import os

from timberlogs import create_timberlogs

# Create a client
timber = create_timberlogs(
    source="example-app",
    environment="development",
    api_key=os.getenv("TIMBER_API_KEY"),
)


def process_checkout(user_id: str, items: list, total: float) -> dict:
    """Simulate a checkout process with flow tracking."""

    # Create a flow for this checkout
    flow = timber.flow("checkout")

    flow.info("Checkout started", {"user_id": user_id, "item_count": len(items)})

    # Step 1: Validate cart
    flow.info("Validating cart", {"items": items})
    # ... validation logic ...
    flow.info("Cart validated")

    # Step 2: Process payment
    flow.info("Processing payment", {"amount": total})
    # ... payment logic ...
    flow.info("Payment successful", {"transaction_id": "txn_abc123"})

    # Step 3: Create order
    order_id = "ord_xyz789"
    flow.info("Creating order", {"order_id": order_id})
    # ... order creation logic ...
    flow.info("Order created")

    # Step 4: Send confirmation
    flow.info("Sending confirmation email", {"email": "user@example.com"})
    # ... email logic ...
    flow.info("Confirmation sent")

    print(f"Flow completed: {flow.id}")
    return {"success": True, "order_id": order_id}


def process_data_pipeline(data: list) -> None:
    """Simulate a data pipeline with flow tracking."""

    flow = timber.flow("data-pipeline")

    flow.info("Pipeline started", {"record_count": len(data)})

    # Process each record
    for i, record in enumerate(data):
        flow.debug("Processing record", {"index": i, "record": record})

    flow.info("Pipeline completed", {"processed_count": len(data)})

    print(f"Pipeline flow: {flow.id}")


# Run examples
if __name__ == "__main__":
    # Example 1: Checkout flow
    result = process_checkout(
        user_id="user_123",
        items=["item_1", "item_2", "item_3"],
        total=149.99,
    )
    print(f"Checkout result: {result}")

    print()

    # Example 2: Data pipeline flow
    process_data_pipeline(
        data=[
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
    )

    # Flush and disconnect
    timber.disconnect()
    print("\nAll flows logged successfully!")
