from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
try:
    import tiktoken  # type: ignore
except Exception:  # optional dependency; used only for counting
    tiktoken = None  # type: ignore
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Literal, cast

from .llm import (
    Request,
    Response,
    LLM,
    Message,
    Role,
)


OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

PROMPT_RATES: Dict[str, float | Dict[str, float]] = {
    "gpt-4o-mini": 0.15 / 1000.0,
    "gpt-4o": 5.00 / 1000.0,
    "gpt-3.5-turbo": 0.50 / 1000.0,
    "gpt-5": {
        "input": 1.250 / 1_000_000.0,
        "cached_input": 0.125 / 1_000_000.0,
        "output": 10.000 / 1_000_000.0,
    },
    "gpt-5-mini": {
        "input": 0.250 / 1_000_000.0,
        "cached_input": 0.025 / 1_000_000.0,
        "output": 2.000 / 1_000_000.0,
    },
    "gpt-5-nano": {
        "input": 0.050 / 1_000_000.0,
        "cached_input": 0.005 / 1_000_000.0,
        "output": 0.400 / 1_000_000.0,
    },
}


@dataclass
class OpenAIConfig:
    default_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    api_key: Optional[str] = os.environ.get(OPENAI_API_KEY_ENV)
    timeout: float = 60.0


class _Message(Message):
    @classmethod
    def from_dict(clas, data: dict) -> 'Message':
        return clas(
            payload={"role": cast(Role, data.get("role", "assistant"))},
            content=data.get("content", "")
        ) if data else None
        
    def to_dict(self) -> dict:
        return {
            "role": self.payload.get("role", "assistant"),
            "content": self.content
        }


Message = _Message


class OpenAI(LLM):
    def __init__(self, config: Optional[OpenAIConfig] = None) -> None:
        self.config = config or OpenAIConfig()

    def make_request_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    def build_payload(self, request: Request, model: str) -> Dict:
        def get_msg_dict(m: Message) -> Dict[str, str]:
            return {"role": str(m.payload.get("role", "assistant")), "content": m.content}

        payload = {
            "model": model,
            "messages": [get_msg_dict(m) for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        return {k: v for k, v in payload.items() if v is not None}

    def parse_response(self, response_data: Dict, model: str, start_time: int) -> Response:
        choices = []
        for i, ch in enumerate(response_data.get("choices", [])):
            msg_data = ch.get("message", {})
            msg = Message.from_dict(msg_data)
            if msg:
                msg.payload["index"] = i
                msg.payload["finish_reason"] = ch.get("finish_reason")
                choices.append(msg)

        usage_data = response_data.get("usage", {})
        if usage_data:
            prompt_tokens = int(usage_data.get("prompt_tokens", 0))
            completion_tokens = int(usage_data.get("completion_tokens", 0))
            total_tokens = int(usage_data.get("total_tokens", 0))
            logging.info(
                f"OpenAI Usage - Model: {model}, Input: {prompt_tokens}, "
                f"Output: {completion_tokens}, Total: {total_tokens}"
            )

        return Response(
            id=response_data.get("id"),
            model=response_data.get("model", model),
            choices=choices,
            created=response_data.get("created", start_time),
        )

    def chat(self, request: Request) -> Response:
        model = request.model or self.config.default_model
        url = f"{OPENAI_API_BASE}/chat/completions"
        
        headers = self.make_request_headers()
        payload = self.build_payload(request, model)
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        start_time = int(time.time())
        
        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            
        return self.parse_response(response_data, model, start_time)

    async def async_chat(self, request: Request) -> Response:
        return self.chat(request)
