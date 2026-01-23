"""Base class for Anthropic API clients."""

from typing import Optional

import anthropic


class AnthropicClientBase:
    """Base class providing common Anthropic client initialization."""

    def __init__(self, api_key: Optional[str]):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
