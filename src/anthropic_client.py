from typing import Optional
import os
from anthropic import Anthropic
from shuntly import shunt, SinkPipe


class AnthropicClientBase:
    def __init__(self, api_key: Optional[str]):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key.
        """
        self.client = Anthropic(api_key=api_key)
        if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("CI") != "true":
            self.client = shunt(self.client, SinkPipe("/tmp/shuntly.fifo"))
