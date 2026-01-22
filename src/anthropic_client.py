"""Base class for Anthropic API clients."""

from typing import Optional

import anthropic

from . import config


class AnthropicClientBase:
    """Base class providing common Anthropic client initialization."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
