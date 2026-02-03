"""Authentication utilities for OpenWeather."""

import os

from mcp.gumstack import get_credentials as gumstack_get_credentials


# Provider name constant for use with get_credentials()
PROVIDER_NAME = "credentials"


async def get_credentials(provider: str = PROVIDER_NAME) -> dict[str, str]:
    """
    Get user-provided credentials from gumstack backend.

    User enters these in gumstack frontend.
    Keys match credentials[].name from config.yaml.

    Args:
        provider: The provider name (defaults to "credentials").
    """
    if os.environ.get("ENVIRONMENT") == "local":
        return {
            "api_key": os.environ.get("LOCAL_API_KEY", ""),
        }

    return await gumstack_get_credentials(provider)
