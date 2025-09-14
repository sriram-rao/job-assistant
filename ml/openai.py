from __future__ import annotations

import json
import os
import time
import urllib.request
import tiktoken
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Literal

from .llm import (
    ChatChoice,
    ChatRequest,
    ChatResponse,
    LLM,
    Message,
    Usage,
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
class ChatGPTConfig:
    default_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    api_key: Optional[str] = os.environ.get(OPENAI_API_KEY_ENV)
    timeout: float = 60.0


class _Message(Message):
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            role=data.get("role", "assistant"),
            content=data.get("content", "")
        ) if data else None
        
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content
        }


class _ChatChoice(ChatChoice):
    @classmethod
    def from_dict(cls, data: dict, index: int) -> 'ChatChoice':
        return cls(
            index=index,
            message=Message.from_dict(data.get("message", {})),
            finish_reason=data.get("finish_reason")
        ) if data else None


class _Usage(Usage):
    @classmethod
    def from_dict(cls, data: dict) -> 'Usage':
        return cls(
            prompt_tokens=int(data.get("prompt_tokens", 0)),
            completion_tokens=int(data.get("completion_tokens", 0)),
            total_tokens=int(data.get("total_tokens", 0)),
        ) if data else None


Message = _Message
ChatChoice = _ChatChoice
Usage = _Usage


class ChatGPT(LLM):
    def __init__(self, config: Optional[ChatGPTConfig] = None) -> None:
        self.config = config or ChatGPTConfig()

    def make_request_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    def build_payload(self, request: ChatRequest, model: str) -> Dict:
        def get_msg_dict(m: Message) -> Dict[str, str]:
            return {"role": m.role, "content": m.content}

        payload = {
            "model": model,
            "messages": [get_msg_dict(m) for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        return {k: v for k, v in payload.items() if v is not None}

    def parse_response(self, response_data: Dict, model: str, start_time: int) -> ChatResponse:
        choices = [
            ChatChoice.from_dict(ch, i)
            for i, ch in enumerate(response_data.get("choices", []))
        ]

        usage_obj = Usage.from_dict(response_data.get("usage", {}))

        return ChatResponse(
            id=response_data.get("id"),
            model=response_data.get("model", model),
            choices=choices,
            usage=usage_obj,
            created=response_data.get("created", start_time),
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
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

    async def async_chat(self, request: ChatRequest) -> ChatResponse:
        return self.chat(request)

    def count_prompt_tokens(self, messages: Sequence[Message], model: Optional[str] = None) -> int:
        model = model or self.config.default_model
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return sum(len(enc.encode(getattr(m, "content", ""))) for m in messages)

    def unit_price(self, model: str, kind: Literal["input", "cached_input", "output"]) -> float:
        return float(rate.get(kind, rate)) if (rate := PROMPT_RATES.get(model)) is not None \
            else float('nan')

    def price_tokens(self, token_count: int, model: Optional[str], kind: Literal["input", "cached_input", "output"]) -> float:
        model_name = model or self.config.default_model
        return float(token_count) * self.unit_price(model_name, kind)

    def price_for_prompt_tokens(self, token_count: int, model: Optional[str] = None) -> float:
        return self.price_tokens(token_count, model, "input")

    def price_for_cached_prompt_tokens(self, token_count: int, model: Optional[str] = None) -> float:
        return self.price_tokens(token_count, model, "cached_input")

    def price_for_output_tokens(self, token_count: int, model: Optional[str] = None) -> float:
        return self.price_tokens(token_count, model, "output")

    def price_for_prompt(self, messages: Sequence[Message], model: Optional[str] = None) -> float:
        prompt_token_count = self.count_prompt_tokens(messages, model=model)
        return self.price_for_prompt_tokens(prompt_token_count, model=model)
