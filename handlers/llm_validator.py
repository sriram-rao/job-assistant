from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import cast, override

from config import VALIDATION_MODEL, VALIDATION_MAX_TOKENS, VALIDATION_TEMPERATURE

from .handler import Handler
from ml.claude import Claude


LLM_LOG_DIR = Path("target/logs")
LLM_CACHE_FILE = LLM_LOG_DIR / "last_llm_response.txt"
LLM_DEBUG_FILE = LLM_LOG_DIR / "llm_response_debug.txt"


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class Validator(Handler[dict[str, str], dict[str, object]]):
    """Validates resume ATS compatibility using ClaudeSDK."""

    def __init__(
        self,
        api_key: str = "",
        model: str = VALIDATION_MODEL,
        temperature: float = VALIDATION_TEMPERATURE,
        max_tokens: int = VALIDATION_MAX_TOKENS,
    ) -> None:
        self.claude: Claude = Claude(api_key=api_key)
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
                    file_metadata
                ]
            }],
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        response_text = "".join(raw_response)

        # Save debug response
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        _ =LLM_DEBUG_FILE.write_text(response_text, encoding="utf-8")
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
            "Score on 0-10 scale where 0 means very bad and 10 means excellent.\n\n"
            "Provide your assessment in JSON format with:\n"
            "- ats_score: integer 0-10\n"
            "- feedback: brief paragraph explaining the score\n"
            "- suggestions: array of 3-5 specific improvements\n\n"
            "Output ONLY valid JSON, no other text."
        )

    def parse_validation_response(self, response: str) -> dict[str, object]:
        json_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_block:
            response = json_block.group(1)
            self.log.info("Extracted JSON from markdown code block")

        # Try to parse as-is first
        try:
            data: dict[str, object] = json.loads(response.strip())
        except json.JSONDecodeError as e:
            self.log.warning("Initial JSON parse failed: %s. Attempting to fix escape sequences.", e)
            cleaned_response = response.strip()

            # Fix invalid escape sequences:
            # Valid JSON escapes are: \" \\ \/ \b \f \n \r \t \uXXXX
            # Replace any backslash not followed by valid escape chars with double backslash
            cleaned_response = re.sub(
                r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})',
                r'\\\\',
                cleaned_response
            )

            try:
                data = json.loads(cleaned_response)
                self.log.info("Successfully parsed JSON after fixing escape sequences")
            except json.JSONDecodeError as e2:
                self.log.error("Failed to parse JSON even after cleanup. Original error: %s, New error: %s", e, e2)
                self.log.error("Cleaned response (first 1000 chars): %s", cleaned_response[:1000])
                raise

        suggestions_raw = data.get("suggestions", [])
        suggestions = (
            [str(item) for item in suggestions_raw]
            if isinstance(suggestions_raw, list)
            else [str(suggestions_raw)]
        )
        return {
            "ats_score": cast(int, data.get("ats_score", 0)),
            "feedback": str(data.get("feedback", "")),
            "suggestions": suggestions,
        }

