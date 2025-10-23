
import os
from typing import Any, Dict, List, Optional, override
from ml.llm import LLM, Request, Response, Message

ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
ANTHROPIC_TIMEOUT = float(os.environ.get("ANTHROPIC_TIMEOUT", 30))

class Claude(LLM):
    def __init__(self,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 timeout: Optional[float] = None):
        self.model = model or ANTHROPIC_DEFAULT_MODEL
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.timeout = timeout or ANTHROPIC_TIMEOUT

    def _make_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    def _to_anthropic_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        return [
            {"role": m.payload.get("role", "user"), "content": m.content}
            for m in messages
        ]

    @override
    def chat(self, request: Request) -> Response:
        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "max_tokens": request.max_tokens or 1024,
            "messages": self._to_anthropic_messages(list(request.messages))
        }
        # Optionally add system prompt
        system_prompt = next((m.content for m in request.messages
                              if m.payload.get("role") == "system"), None)
        if system_prompt:
            payload["system"] = system_prompt
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        resp = requests.post(
            ANTHROPIC_API_URL,
            headers=self._make_headers(),
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        resp_data = resp.json()

        # Extract content and wrap as llm.Response
        content_blocks = resp_data.get("content", [])
        text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        role = "assistant"

        msg = Message(payload={"role": role, "finish_reason": resp_data.get("stop_reason")}, content=text)
        return Response(
            id=resp_data.get("id"),
            model=resp_data.get("model"),
            choices=[msg],
            created=resp_data.get("created")
        )

    @override
    async def async_chat(self, request: Request) -> Response:
        # For simplicity, run chat in sync. For real async, use httpx.AsyncClient.
        return self.chat(request)

    def upload_file(self, local_path: str) -> dict:
        """
        Uploads a file to the Anthropic Files API.
        Returns the parsed JSON response (should contain file id and metadata).
        """
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        filename = os.path.basename(local_path)
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
            content_type = f"application/{ext}"
        else:
            content_type = "application/octet-stream"
        with open(local_path, "rb") as f:
            return client.beta.files.upload(
                file=(filename, f, content_type),
            )

