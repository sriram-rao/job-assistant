from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Sequence
from typing import Literal, Protocol, overload, cast, override


Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str


@dataclass(slots=True)
class ChatRequest:
    messages: Sequence[Message]
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class ChatChoice:
    index: int
    message: Message
    finish_reason: str | None = None


@dataclass(slots=True)
class ChatResponse:
    id: str | None
    model: str | None
    choices: list[ChatChoice]
    usage: Usage | None = None
    created: int | None = None


class LLM(Protocol):
    """
    Interface for Large Language Model chat clients.

    Implementations should convert between provider-specific request/response
    schemas and these simple dataclasses.
    """

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Synchronous chat completion call."""
        ...

    async def async_chat(self, request: ChatRequest) -> ChatResponse:  # pragma: no cover
        ...

    def count_prompt_tokens(self, messages: Sequence[Message], model: str | None = None) -> int:
        """Return the number of input tokens for the given messages and model."""
        ...

    def price_for_prompt_tokens(self, token_count: int, model: str | None = None) -> float:
        """Return the price in USD for a prompt consisting of token_count tokens."""
        ...

    def price_for_prompt(self, messages: Sequence[Message], model: str | None = None) -> float:
        """Convenience wrapper around count_prompt_tokens + price_for_prompt_tokens."""
        ...


# Convenience helpers

def user(text: str) -> Message:
    return Message(role="user", content=text)


def system(text: str) -> Message:
    return Message(role="system", content=text)


def assistant(text: str) -> Message:
    return Message(role="assistant", content=text)


@overload

def to_request(
    prompt: str,
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> ChatRequest: ...


@overload

def to_request(
    prompt: Iterable[str],
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> ChatRequest: ...


@overload

def to_request(
    prompt: Sequence[Message],
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> ChatRequest: ...


def to_request(
    prompt: str | Iterable[str] | Sequence[Message],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
) -> ChatRequest:
    """Build a ChatRequest from a prompt.

    - If a string is provided, it's treated as a single user message.
    - If an iterable of strings is provided, they're treated as sequential user messages.
    - If a sequence of Message is provided, it's used directly.
    """
    if isinstance(prompt, str):
        messages: list[Message] = [user(prompt)]
    elif isinstance(prompt, Sequence):
        seq = list(prompt)
        if seq and isinstance(seq[0], Message):
            messages = cast(list[Message], seq)
        else:
            messages = [user(cast(str, p)) for p in seq]
    else:
        messages = [user(p) for p in prompt]

    return ChatRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )


class DummyLLM(LLM):
    """No-op LLM implementation used as a safe default.

    Returns an empty assistant message and zero token/accounting data.
    """

    @override
    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            id=None,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=Message(role="assistant", content=""),
                    finish_reason="stop",
                )
            ],
            usage=Usage(),
            created=None,
        )

    @override
    async def async_chat(self, request: ChatRequest) -> ChatResponse:  # pragma: no cover
        return self.chat(request)

    @override
    def count_prompt_tokens(self, messages: Sequence[Message], model: str | None = None) -> int:
        return 0

    @override
    def price_for_prompt_tokens(self, token_count: int, model: str | None = None) -> float:
        return 0.0

    @override
    def price_for_prompt(self, messages: Sequence[Message], model: str | None = None) -> float:
        return 0.0


# Shared singleton instance to use as a safe default
DUMMY_LLM: LLM = DummyLLM()
