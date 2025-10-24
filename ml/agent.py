"""
LLM Agent Protocol - simple interface for LLM implementations.
"""


from abc import ABC, abstractmethod
from typing import TypeAlias


MessageValue: TypeAlias = str | dict[str, 'MessageValue'] | list['MessageValue']
Message: TypeAlias = dict[str, MessageValue]


class Agent(ABC):
    """Minimal protocol for LLM clients."""

    def __init__(self, model: str = "", system_prompt: str = "", api_key: str | None = None):
        self.model: str = model
        self.system_prompt: str = system_prompt

    @abstractmethod
    def chat_full(
        self,
        messages: list[Message],
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0,
        reasoning: str = "low",
    ) -> list[str]:
        """
        Full chat interface with all customization options.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            model: Model name/ID
            max_tokens: Maximum tokens in response
            system: System prompt
            temperature: Temperature for sampling

        Returns:
            Full response object from the LLM provider
        """
        ...

    def chat(self, message: str, model: str = "", max_tokens: int = 1024, temperature: float = 1, reasoning: str = "low") -> str:
        return "\n".join(self.chat_full([{"role": "user", "content": message}], model, max_tokens, temperature, reasoning))
