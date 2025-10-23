# filepath: ml/claude_sdk.py
"""
Minimal Claude (Anthropic) Python SDK usage.
No custom Request/Response classes or protocols.
"""

import os
from typing import cast, override
import anthropic
from anthropic.types import Message
from anthropic.types.beta import FileMetadata
from ml.llm_protocol import LLMProtocol

class ClaudeSDK(LLMProtocol):
    api_key: str
    client: anthropic.Anthropic

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            default_headers={"anthropic-beta": "files-api-2025-04-14"}
        )

    @override
    def chat_full(self, messages: list[dict[str, str]], model: str = "claude-haiku-4-5", max_tokens: int = 1024, system: str = "", temperature: float = 1.0) -> Message:
        """
        messages: list of {"role": "user"|"assistant", "content": str}
        """
        return self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=cast("list[anthropic.types.MessageParam]", messages),
            temperature=temperature,
            system=system
        )

    @override
    def chat(self, prompt: str) -> str:
        """
        Simple chat interface: single prompt in, string out.
        """
        response = self.chat_full([{"role": "user", "content": prompt}])
        return "".join(block.text for block in response.content)

    def upload_file(self, local_path: str) -> FileMetadata:
        filename = os.path.basename(local_path)
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
            content_type = f"application/{ext}"
        else:
            content_type = "application/octet-stream"
        with open(local_path, "rb") as f:
            return self.client.beta.files.upload(
                file=(filename, f, content_type),
            )

# Example usage:
if __name__ == "__main__":
    claude = ClaudeSDK()
    print(claude.chat("Hey gpT"))
    # Upload a file
    # res = claude.upload_file("/path/to/document.pdf")
    # print(res)

    # Chat example
    # response = claude.chat([
    #     {"role": "user", "content": "Hello Claude, summarize this for me."}
    # ])
    # print(response)
