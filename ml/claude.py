import logging
import os
from typing import cast, override

import anthropic
from anthropic.types.beta import FileMetadata
from ml.agent import Agent, Message

class Claude(Agent):
    api_key: str
    client: anthropic.Anthropic

    def __init__(self, model: str = "claude-haiku-4-5", system_prompt: str = "", api_key: str = ""):
        super().__init__(model, system_prompt, api_key)
        self.api_key = api_key
        self.client = anthropic.Anthropic(
            api_key=self.api_key or os.environ.get("ANTHROPIC_API_KEY"),
            default_headers={"anthropic-beta": "files-api-2025-04-14"}
        )

    @override
    def chat_full(self, messages: list[Message], model: str = "claude-haiku-4-5", max_tokens: int = 1024, temperature: float = 1.0, reasoning: str = "low") -> list[str]:
        """
        messages: list of {"role": "user"|"assistant", "content": str}
        """
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=cast("list[anthropic.types.MessageParam]", messages),
            temperature=temperature,
            system=self.system_prompt
        )
        logging.info("\033[33mLLM %s tokens - input: %s, output: %s\033[0m", model, response.usage.input_tokens, response.usage.output_tokens)
        return [block.text for block in response.content if block.type == "text"]

    @override
    def upload_file(self, local_path: str) -> Message:
        filename = os.path.basename(local_path)
        ext, content_type = "", "application/octet-stream"
        if "." in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
            content_type = f"application/{ext}"
        with open(local_path, "rb") as f:
            return self.make_file_message(self.client.beta.files.upload(
                file=(filename, f, content_type))
            )

    def make_file_message(self, file_metadata: FileMetadata) -> Message:
        return {"type": "document", "source": {
            "type": "file",
            "file_id": file_metadata.id
        }}

# Example usage:
if __name__ == "__main__":
    claude = Claude()
    print(claude.chat("Hey gpT"))
    # Upload a file
    # res = claude.upload_file("/path/to/document.pdf")
    # print(res)

    # Chat example
    # response = claude.chat([
    #     {"role": "user", "content": "Hello Claude, summarize this for me."}
    # ])
    # print(response)
