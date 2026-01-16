"""Basic usage example for the Timberlogs Python SDK."""

import os

from timberlogs import LogOptions, create_timberlogs

# Create a client
timber = create_timberlogs(
    source="example-app",
    environment="development",
    api_key=os.getenv("TIMBER_API_KEY"),
)

# Basic logging
timber.debug("Application starting")
timber.info("User signed in", {"user_id": "user_123", "method": "password"})
timber.warn("Rate limit approaching", {"current": 950, "limit": 1000})

# Error logging with Exception
try:
    raise ValueError("Something went wrong")
except Exception as e:
    timber.error("Operation failed", e)

# Error logging with data
timber.error("Validation failed", {"field": "email", "reason": "invalid format"})

# Using tags
timber.info(
    "Payment processed",
    {"amount": 99.99, "currency": "USD"},
    LogOptions(tags=["payments", "success"]),
)

# Method chaining
timber.set_user_id("user_456").set_session_id("sess_789").info("User action logged")

# Flush and disconnect
timber.disconnect()

print("Logs sent successfully!")
