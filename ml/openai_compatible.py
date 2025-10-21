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

@dataclass
class OpenAICompatibleConfig:
    default_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    api_base: str = field(default_factory=lambda: os.environ.get("OPENAI_API_BASE", "http://localhost:11434/v1"))
    api_key: Optional[str] = None
    timeout: float = 120.0

    def __post_init__(self) -> None:
        if not self.default_model:
            self.default_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_base:
            self.api_base = os.environ.get("OPENAI_API_BASE", "http://localhost:11434/v1")
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")


class _Message(Message):
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            payload={"role": cast(Role, data.get("role", "assistant"))},
            content=data.get("content", "")
        ) if data else None

    def to_dict(self) -> dict:
        return {
            "role": self.payload.get("role", "assistant"),
            "content": self.content
        }


Message = _Message


class OpenAICompatible(LLM):
    # Model-specific parameter configurations
    GPT5_PARAMS = {
        "tokens_param": "max_completion_tokens",  # GPT-5 requires this
        "supports_temperature": False,  # GPT-5 only supports default temp=1
    }

    GPT4_PARAMS = {
        "tokens_param": "max_tokens",  # GPT-4 and earlier use this
        "supports_temperature": True,
    }

    def __init__(self, config: Optional[OpenAICompatibleConfig] = None) -> None:
        self.config = config or OpenAICompatibleConfig()

    def make_request_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def build_payload(self, request: Request, model: str) -> Dict:
        def to_content(message: Message) -> Dict[str, object]:
            role = str(message.payload.get("role", "assistant"))
            text = message.content or ""
            return {
                "role": role,
                "content": text,
            }

        # Choose config based on model
        params = self.GPT5_PARAMS if model.startswith("gpt-5") else self.GPT4_PARAMS

        payload: Dict[str, object] = {
            "model": model,
            "messages": [to_content(m) for m in request.messages],
            "stream": False,
        }

        # Add temperature if provided and supported
        if request.temperature is not None and params["supports_temperature"]:
            payload["temperature"] = request.temperature
        elif request.temperature is not None and not params["supports_temperature"]:
            logging.info(f"Temperature parameter not supported for {model}, ignoring requested value {request.temperature}")

        # Add tokens with correct parameter name
        payload[params["tokens_param"]] = request.max_tokens or 4000

        return {key: value for key, value in payload.items() if value is not None}

    def parse_response(self, response_data: Dict, model: str, start_time: int) -> Response:
        choices: List[Message] = []

        # Standard OpenAI chat completions format
        choices_data = response_data.get("choices", [])
        for choice in choices_data:
            message_data = choice.get("message", {})
            content = message_data.get("content", "")

            # For models with reasoning (like gpt-oss), check reasoning field if content is empty
            if not content and "reasoning" in message_data:
                content = message_data.get("reasoning", "")

            if content:
                message = Message(
                    payload={"role": message_data.get("role", "assistant"), "index": choice.get("index", 0)},
                    content=content,
                )
                choices.append(message)

        # Log usage if available
        usage = response_data.get("usage", {})
        if usage:
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            logging.info(
                f"OpenAI-Compatible Usage - Model: {model}, Input: {prompt_tokens}, "
                f"Output: {completion_tokens}, Total: {total_tokens}"
            )

        if not choices:
            logging.error("OpenAI-Compatible parsed no choices from: %s", response_data)

        return Response(
            id=response_data.get("id"),
            model=response_data.get("model", model),
            choices=choices,
            created=response_data.get("created", start_time),
        )

    def chat(self, request: Request) -> Response:
        model = request.model or self.config.default_model
        url = f"{self.config.api_base}/chat/completions"

        headers = self.make_request_headers()
        payload = self.build_payload(request, model)
        start_time = int(time.time())

        logging.info(f"OpenAI-Compatible Provider: {self.config.api_base}, Model: {model}")
        logging.debug(f"OpenAI-Compatible request to {url} with model {model}")

        response = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        if response.status_code >= 400:
            logging.error("OpenAI-Compatible response %s: %s", response.status_code, response.text)
        response.raise_for_status()
        response_data = response.json()

        if not response_data.get("choices"):
            logging.error("OpenAI-Compatible empty choices: %s", response_data)

        return self.parse_response(response_data, model, start_time)

    async def async_chat(self, request: Request) -> Response:
        return self.chat(request)
