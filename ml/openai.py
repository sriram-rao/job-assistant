from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, cast

import requests

from .llm import (
    LLM,
    Message,
    Request,
    Response,
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
    default_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    api_key: Optional[str] = None
    timeout: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.environ.get(OPENAI_API_KEY_ENV)
        if not self.default_model:
            self.default_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


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
        def to_content(message: Message) -> Dict[str, object]:
            role = str(message.payload.get("role", "assistant"))
            text = message.content or ""
            return {
                "role": role,
                "content": [{"type": "input_text", "text": text}],
            }

        payload: Dict[str, object] = {
            "model": model,
            "input": [to_content(m) for m in request.messages],
            "stream": False,
            "text": {"format": {"type": "text"}},
        }
        if request.max_tokens is not None:
            payload["max_output_tokens"] = request.max_tokens
        return {key: value for key, value in payload.items() if value is not None}

    def parse_response(self, response_data: Dict, model: str, start_time: int) -> Response:
        choices: List[Message] = []
        outputs = response_data.get("output") or []
        for index, item in enumerate(outputs):
            if item.get("role") not in {"assistant", "tool"}:
                continue
            parts = item.get("content") or []
            text_segments = [part.get("text", "") for part in parts if part.get("type") in {"output_text", "text"}]
            if not text_segments:
                continue
            message = Message(
                payload={"role": item.get("role", "assistant"), "index": index},
                content="".join(text_segments),
            )
            finish = item.get("finish_reason") or item.get("status") or item.get("stop_reason")
            if finish:
                message.payload["finish_reason"] = finish
            choices.append(message)

        usage_data = response_data.get("usage", {})
        if usage_data:
            prompt_tokens = int(usage_data.get("input_tokens", usage_data.get("prompt_tokens", 0)))
            completion_tokens = int(usage_data.get("output_tokens", usage_data.get("completion_tokens", 0)))
            total_tokens = int(usage_data.get("total_tokens", prompt_tokens + completion_tokens))
            logging.info(
                f"OpenAI Usage - Model: {model}, Input: {prompt_tokens}, "
                f"Output: {completion_tokens}, Total: {total_tokens}"
            )
        if not choices:
            logging.error("OpenAI parsed no choices from: %s", response_data)

        return Response(
            id=response_data.get("id"),
            model=response_data.get("model", model),
            choices=choices,
            created=response_data.get("created", start_time),
        )

    def chat(self, request: Request) -> Response:
        model = request.model or self.config.default_model
        url = f"{OPENAI_API_BASE}/responses"

        headers = self.make_request_headers()
        payload = self.build_payload(request, model)
        start_time = int(time.time())
        response = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        if response.status_code >= 400:
            logging.error("OpenAI response %s: %s", response.status_code, response.text)
        response.raise_for_status()
        response_data = response.json()
        if not response_data.get("output"):
            logging.error("OpenAI empty output: %s", response_data)

        return self.parse_response(response_data, model, start_time)

    async def async_chat(self, request: Request) -> Response:
        return self.chat(request)
