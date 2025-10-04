from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Sequence
from typing import Literal, Protocol, overload, cast, override


Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class Message:
    payload: dict[str, object]
    content: str


@dataclass(slots=True)
class Request:
    messages: Sequence[Message]
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


@dataclass(slots=True)
class Response:
    id: str | None
    model: str | None
    choices: list[Message]
    created: int | None = None


class LLM(Protocol):
    """
    Interface for Large Language Model chat clients.

    Implementations should convert between provider-specific request/response
    schemas and these simple dataclasses.
    """

    def chat(self, request: Request) -> Response:
        """Synchronous chat completion call."""
        ...

    async def async_chat(self, request: Request) -> Response:  # pragma: no cover
        ...


# Convenience helpers

def user(text: str) -> Message:
    return Message(payload={"role": "user"}, content=text)


def system(text: str) -> Message:
    return Message(payload={"role": "system"}, content=text)


def assistant(text: str) -> Message:
    return Message(payload={"role": "assistant"}, content=text)


@overload

def to_request(
    prompt: str,
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> Request: ...


@overload

def to_request(
    prompt: Iterable[str],
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> Request: ...


@overload

def to_request(
    prompt: Sequence[Message],
    *,
    model: str | None = ...,
    temperature: float | None = ...,
    max_tokens: int | None = ...,
    stream: bool = ...,
) -> Request: ...


def to_request(
    prompt: str | Iterable[str] | Sequence[Message],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
) -> Request:
    """Build a Request from a prompt.

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

    return Request(
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
    def chat(self, request: Request) -> Response:
        return Response(
            id=None,
            model=request.model,
            choices=[Message(payload={"role": "assistant", "index": 0, "finish_reason": "stop"}, content="")],
            created=None,
        )

    @override
    async def async_chat(self, request: Request) -> Response:  # pragma: no cover
        return self.chat(request)


# Shared singleton instance to use as a safe default
DUMMY_LLM: LLM = DummyLLM()
