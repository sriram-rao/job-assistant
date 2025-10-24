from __future__ import annotations

import os
from typing import cast, override

from openai import Omit, OpenAI as OpenAIClient
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
            instructions=self.system_prompt,
            input=str(messages[0]["content"]),
            reasoning=Reasoning(effort=cast(ReasoningEffort, reasoning)) if (model or self.model).startswith("gpt-5") else Omit()
        )
        # Extract text from response output (Responses API format)
        response_messages = [m for m in response.output if "message" == m.type]
        return [c.text for m in response_messages  ## pyright: ignore[reportAttributeAccessIssue]
            for c in m.content if "output_text" == c.type]  ## pyright: ignore[] ignores m and c unknown type warnings
