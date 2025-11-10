from typing import override

from openai import OpenAI as OpenAIClient, chat
from ml.agent import Agent, Message


class OpenAI(Agent):

    def __init__(self, model: str = "", system_prompt: str = "", api_key: str | None = None):
        super().__init__(model, system_prompt, api_key)
        self.client = OpenAIClient()

    @override
    def chat_full(self, messages: list[Message], model: str = "", max_tokens: int = 1024, temperature: float = 1, reasoning: str = "low") -> list[str]:
        response = self.client,chat.completions.create(
            messages=messages,
            model=model or self.model,
            max_tokens=max_tokens,
            service_tier="flex",
            reasoning_effort=reasoning,
            temperature=temperature
        )
