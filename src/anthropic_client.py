from typing import Optional

import anthropic


class AnthropicClientBase:
    def __init__(self, api_key: Optional[str]):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
