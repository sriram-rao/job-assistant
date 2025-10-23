from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import override

from .handler import Handler
from ml.llm import DUMMY_LLM, LLM, to_request
from ml.claude_sdk import ClaudeSDK
from settings import OPENAI_MODEL, REASONING_EFFORT


LLM_LOG_DIR = Path("target/logs")
LLM_CACHE_FILE = LLM_LOG_DIR / "last_llm_response.txt"
LLM_DEBUG_FILE = LLM_LOG_DIR / "llm_response_debug.txt"


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class GPTClient(Handler[str, str]):
    """Handles GPT communication and caching."""

    def __init__(
        self,
        llm: LLM = DUMMY_LLM,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.llm = llm
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def read_cached_llm_output(self) -> str | None:
        if not LLM_CACHE_FILE.exists():
            return None
        return LLM_CACHE_FILE.read_text(encoding="utf-8")

    def write_cached_llm_output(self, raw_output: str) -> None:
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        LLM_CACHE_FILE.write_text(raw_output, encoding="utf-8")

    @override
    def process(self, input_data: str) -> str:
        """Send prompt to LLM and return response."""
        req = to_request(
            input_data,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            reasoning_effort=self.reasoning_effort or REASONING_EFFORT,
        )
        self.log.info("Calling LLM.chat, model=%s", self.model or OPENAI_MODEL)
        res = self.llm.chat(req)
        if not res.choices:
            self.log.error("LLM returned no content, see logs for provider call details")
            raise RuntimeError("LLM returned no choices/content")
        return res.choices[0].content


class LLMValidator(Handler[dict[str, str], dict[str, object]]):
    """Validates resume ATS compatibility using ClaudeSDK."""

    def __init__(
        self,
        api_key: str = "",
        *,
        model: str = "claude-haiku-4-5",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> None:
        self.claude: ClaudeSDK = ClaudeSDK(api_key=api_key)
        self.model: str = model
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    @override
    def process(self, input_data: dict[str, str]) -> dict[str, object]:
        # DEBUG: Uncomment to use cached response
        # if LLM_DEBUG_FILE.exists():
        #     self.log.info("Reading cached LLM response from %s", LLM_DEBUG_FILE)
        #     response_text = LLM_DEBUG_FILE.read_text(encoding="utf-8")
        #     return self.parse_validation_response(response_text)

        job_text = input_data["job_text"]
        resume_pdf_path = input_data["resume_pdf_path"]

        self.log.info("Uploading resume PDF: %s", resume_pdf_path)
        file_metadata = self.claude.upload_file(resume_pdf_path)

        self.log.info("Validating resume ATS compatibility with %s", self.model)
        prompt_text = self.build_validation_prompt(job_text)

        raw_response = self.claude.chat_full(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "document", "source": {"type": "file", "file_id": file_metadata.id}}
                ]
            }],
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        response_text = "".join(block.text for block in raw_response.content)

        # Save debug response
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        LLM_DEBUG_FILE.write_text(response_text, encoding="utf-8")
        self.log.info("Saved LLM response to %s", LLM_DEBUG_FILE)

        return self.parse_validation_response(response_text)

    def build_validation_prompt(self, job_text: str) -> str:
        return (
            "You are an ATS (Applicant Tracking System) expert. Analyze the attached resume "
            "against the job description and evaluate its ATS compatibility.\n\n"
            "Job Description:\n"
            f"{job_text}\n\n"
            "Evaluate the resume on:\n"
            "1. Keyword matching with job description\n"
            "2. Formatting compatibility with ATS systems\n"
            "3. Section organization and clarity\n"
            "4. Quantifiable achievements alignment\n\n"
            "Provide your assessment in JSON format with:\n"
            "- ats_score: integer 0-100 (100 = perfect ATS compatibility)\n"
            "- feedback: brief paragraph explaining the score\n"
            "- suggestions: array of 3-5 specific improvements\n\n"
            "Output ONLY valid JSON, no other text."
        )

    def parse_validation_response(self, response: str) -> dict[str, object]:
        json_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_block:
            response = json_block.group(1)
            self.log.info("Extracted JSON from markdown code block")
        data: dict[str, object] = json.loads(response.strip())
        suggestions_raw = data.get("suggestions", [])
        suggestions = (
            [str(item) for item in suggestions_raw]
            if isinstance(suggestions_raw, list)
            else [str(suggestions_raw)]
        )
        return {
            "ats_score": int(data.get("ats_score", 0)),
            "feedback": str(data.get("feedback", "")),
            "suggestions": suggestions,
        }
