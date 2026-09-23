from typing import Optional
import os
from anthropic import Anthropic
from anthropic.types import Message
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

    @staticmethod
    def response_text(response: Message) -> str:
        """Return the response's text, skipping thinking blocks.

        Current models think by default, so the text is not necessarily the first
        content block. Raises if the output was cut off or refused, rather than
        returning partial text.
        """
        if response.stop_reason == "max_tokens":
            raise RuntimeError(
                f"{response.model} response hit max_tokens "
                f"({response.usage.output_tokens} output tokens); output is truncated"
            )
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None)
            raise RuntimeError(f"{response.model} declined the request (category: {category})")
        return "".join(block.text for block in response.content if block.type == "text")
