from __future__ import annotations

import os
from typing import cast, override

from openai import OpenAI as OpenAIClient
from openai.types.shared.reasoning_effort import ReasoningEffort
from openai.types.shared_params.reasoning import Reasoning

from settings import OPENAI_MODEL
from .agent import Agent, Message


class GPT(Agent):
    def __init__(self, default_model: str = OPENAI_MODEL, system_prompt: str = "", api_key: str | None = None) -> None:
        super().__init__(default_model, system_prompt, api_key)
        self.client: OpenAIClient = OpenAIClient(api_key=api_key or os.environ.get("OPENAI_API_KEY"))


    @override
    def chat_full(self, messages: list[Message], model: str = "", max_tokens: int = 4096, temperature: float = 1, reasoning: str = "low") -> list[str]:
        response = self.client.responses.parse(
            model=model or self.model,
            max_output_tokens=max_tokens,
            temperature=temperature,
            reasoning=Reasoning(effort=cast(ReasoningEffort, reasoning)),
            instructions=self.system_prompt,
            input=str(messages[0]["content"])
        )

        return [choice.message.content for choice in getattr(response, "choices", [])]
