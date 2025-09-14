from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal, Optional, Protocol, Sequence


Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str


@dataclass(slots=True)
class ChatRequest:
    messages: Sequence[Message]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
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
    finish_reason: Optional[str] = None


@dataclass(slots=True)
class ChatResponse:
    id: Optional[str]
    model: Optional[str]
    choices: List[ChatChoice]
    usage: Optional[Usage] = None
    created: Optional[int] = None


class LLM(Protocol):
    """
    Interface for Large Language Model chat clients.

    Implementations should convert between provider-specific request/response
    schemas and these simple dataclasses.
    """

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Synchronous chat completion call.

        Implementations may raise exceptions on transport or API errors.
        """
        ...

    # Optional async interface; implement if the client supports it
    async def async_chat(self, request: ChatRequest) -> ChatResponse:  # pragma: no cover
        ...

    # Tokenization and pricing helpers (to be implemented by concrete clients)
    def count_prompt_tokens(
        self, messages: Sequence[Message], model: Optional[str] = None
    ) -> int:
        """Return the number of input tokens for the given messages and model."""
        ...

    def price_for_prompt_tokens(
        self, token_count: int, model: Optional[str] = None
    ) -> float:
        """Return the price in USD for a prompt consisting of token_count tokens."""
        ...

    def price_for_prompt(
        self, messages: Sequence[Message], model: Optional[str] = None
    ) -> float:
        """Convenience wrapper around count_prompt_tokens + price_for_prompt_tokens."""
        ...


# Convenience helpers

def user(text: str) -> Message:
    return Message(role="user", content=text)


def system(text: str) -> Message:
    return Message(role="system", content=text)


def assistant(text: str) -> Message:
    return Message(role="assistant", content=text)


def to_request(
    prompt: str | Iterable[str] | Sequence[Message],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    stream: bool = False,
) -> ChatRequest:
    """Build a ChatRequest from a prompt.

    - If a string is provided, it's treated as a single user message.
    - If an iterable of strings is provided, they're treated as sequential user messages.
    - If a sequence of Message is provided, it's used directly.
    """
    if isinstance(prompt, str):
        messages: List[Message] = [user(prompt)]
    else:
        # Best-effort detection: if it's already Messages, keep them
        seq = list(prompt)  # type: ignore[arg-type]
        if seq and isinstance(seq[0], Message):  # type: ignore[unreachable]
            messages = seq  # type: ignore[assignment]
        else:
            messages = [user(p) for p in seq]  # type: ignore[union-attr]

    return ChatRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )
