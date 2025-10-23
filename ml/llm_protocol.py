# filepath: ml/llm_protocol.py
"""
Lean LLM Protocol - simple interface for LLM implementations.
"""

from abc import ABC, abstractmethod


class LLMProtocol(ABC):
    """Minimal protocol for LLM clients."""

    def chat(self, prompt: str) -> str:
        """
        Simple chat interface: string in, string out.
        Default implementation uses chat_full.

        Args:
            prompt: User prompt/question

        Returns:
            LLM response as string
        """
        response = self.chat_full([{"role": "user", "content": prompt}])
        return "".join(block.text for block in response.content)

    @abstractmethod
    def chat_full(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        max_tokens: int = 1024,
        system: str = "",
        temperature: float = 1.0
    ) -> object:
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
