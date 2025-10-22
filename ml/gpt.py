from __future__ import annotations

import logging
import os
from typing import cast

from openai import OpenAI as OpenAIClient
from openai.types.responses import ResponseInputParam

from settings import OPENAI_MODEL
from .llm import Request, Response, Message


class GPT:
    def __init__(self, api_key: str | None = None, default_model: str = OPENAI_MODEL) -> None:
        self.client: OpenAIClient = OpenAIClient(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.default_model: str = default_model

    def chat(self, request: Request) -> Response:
        model = request.model or self.default_model
        
        response = self.client.responses.create(
            model=model,
            input=cast(ResponseInputParam, [{"type": "message", "role": str(m.payload.get("role", "assistant")), "content": m.content} for m in request.messages]),
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        
        messages = [
            Message(
                payload={"role": "assistant", "index": 0, "finish_reason": response.status},
                content=response.output_text or ""
            )
        ]
        
        if response.usage:
            logging.info((
                f"GPT Usage - Model: {model}, Input: {response.usage.input_tokens}, "
                f"Output: {response.usage.output_tokens}, Total: {response.usage.input_tokens + response.usage.output_tokens}"
            ))
        
        return Response(
            id=response.id,
            model=model,
            choices=messages,
            created=int(response.created_at),
        )

    async def async_chat(self, request: Request) -> Response:
        return self.chat(request)
