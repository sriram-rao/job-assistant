import json
import logging
import re
import threading
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from defaults import EXPERIENCE, LETTER_CONTENT, PERSON, SKILLS
from settings import CONTEXT_INSTRUCTIONS, FULL_SCHEMA, OPENAI_MODEL, REASONING_EFFORT, REQUIREMENTS, RESPONSES_MAX_OUTPUT_TOKENS
from util.file import (
    archive_old_pdfs,
    compile_pdfs,
    generate_letter_files,
    generate_resume_files,
    html_to_text,
    rename_pdfs,
)
from ml.llm import DUMMY_LLM, LLM, to_request
from net.web import get_html


LLM_LOG_DIR = Path("target/logs")
LLM_CACHE_FILE = LLM_LOG_DIR / "last_llm_response.txt"


class LLMData(TypedDict):
    page_text: str
    person: dict[str, str | dict[str, str]]
    experience: list[dict[str, str | list[str]]]
    skills: list[str]
    cover_letter: dict[str, str]
    page_html: NotRequired[str]


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class Assistant:
    llm: LLM

    def __init__(self, llm: LLM = DUMMY_LLM) -> None:
        self.llm = llm

    def _read_cached_llm_output(self) -> str | None:
        if not LLM_CACHE_FILE.exists():
            return None
        return LLM_CACHE_FILE.read_text(encoding="utf-8")

    def _write_cached_llm_output(self, raw_output: str) -> None:
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        _ = LLM_CACHE_FILE.write_text(raw_output, encoding="utf-8")

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def fetch(self, url: str) -> str:
        self.log.info("Fetching URL: %s", url)
        return get_html(url)

    def _make_request(
        self,
        prompt: str,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
        reasoning_effort: str | None,
    ):
        return to_request(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort or REASONING_EFFORT,
        )

    def ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        req = self._make_request(prompt, model, temperature, max_tokens, reasoning_effort)
        self.log.info("Calling LLM.chat, model=%s", model or OPENAI_MODEL)
        res = self.llm.chat(req)
        if not res.choices:
            self.log.error("LLM returned no content, see logs for provider call details")
            raise RuntimeError("LLM returned no choices/content")
        return res.choices[0].content

    async def schedule_ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        req = self._make_request(prompt, model, temperature, max_tokens, reasoning_effort)
        self.log.info("Calling LLM.async_chat, model=%s", model or OPENAI_MODEL)
        res = await self.llm.async_chat(req)
        if not res.choices:
            self.log.error("Async LLM call returned no content, see logs for provider call details")
            raise RuntimeError("LLM returned no choices/content")
        return res.choices[0].content

    def build_llm_data(self, html: str, *, include_raw_html: bool = False) -> LLMData:
        skills_all: list[str] = list(
            dict.fromkeys(
                skill for values in SKILLS.values() for skill in values if skill
            )
        )
        data: LLMData = {
            "page_text": html_to_text(html),
            "person": PERSON,
            "experience": EXPERIENCE,
            "skills": skills_all,
            "cover_letter": LETTER_CONTENT,
        }
        if include_raw_html:
            data["page_html"] = html
        return data

    def store_application(
        self, application: dict[str, object], out_dir: Path | None = None
    ) -> dict[str, Path]:
        """Store application materials: generate LaTeX files, compile to PDFs, and organize outputs."""
        self.log.info("Generating letter files")
        generate_letter_files(application)

        self.log.info("Generating resume files")
        generate_resume_files(application)

        target_dir = Path("target/autogen")
        target_dir.mkdir(parents=True, exist_ok=True)

        self.log.info("Archiving old PDFs")
        archive_old_pdfs(target_dir)

        self.log.info("Compiling PDFs")
        compile_pdfs(target_dir)

        self.log.info("Renaming/moving PDFs to final location")
        company = cast(dict[str, str], application.get("details", {})).get("company", "")
        letter_pdf_final, resume_pdf_final = rename_pdfs(target_dir, company)

        return {
            "letter_tex": Path("letter") / "body.tex",
            "letter_pdf": letter_pdf_final,
            "resume_tex": Path("resume") / "workexperience.tex",
            "resume_pdf": resume_pdf_final,
        }

    def generate_application(
        self,
        url: str,
        *,
        model: str = "",
        temperature: float = 0.2,
        max_tokens: int = RESPONSES_MAX_OUTPUT_TOKENS,
        custom_prompt: str = "",
    ) -> str:
        # cached = self._read_cached_llm_output()
        # if cached is not None:
        #     self.log.info("Using cached LLM response from %s", LLM_CACHE_FILE)
        #     return cached

        prompt: str = "\n".join([
            str(custom_prompt),
            self.get_context(url),
            "Requirements:\n" + "\n".join(REQUIREMENTS.values()) + "Schema: " + FULL_SCHEMA
        ])
        self.log.info("About to generate application via LLM")
        raw_output = self.ask(
            prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )
        # self._write_cached_llm_output(raw_output)
        return raw_output

    def generate_and_save_application(
        self, url: str, out_dir: Path | None = None
    ) -> dict[str, Path]:
        """Generate application from URL and save to disk."""
        self.log.info("Generating application JSON")
        raw_response = self.generate_application(url)
        self.log.info(f"Raw LLM response (first 500 chars): {raw_response[:500]}")

        # Strip reasoning output (for models like GPT-OSS, DeepSeek-R1)
        raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)

        # Strip markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw_response, re.DOTALL)
        if json_match:
            raw_response = json_match.group(1)
            self.log.info("Extracted JSON from markdown code block")

        raw_response = raw_response.strip()
        application: dict[str, object] = json.loads(raw_response)

        self.log.info("Storing application to disk")
        return self.store_application(application, out_dir)

    def ask_about(self, question: str, about_url: str) -> str:
        self.log.info("Asking assistant a question")
        return self.ask(
            self.get_context(about_url) + "\n" + question,
            model=OPENAI_MODEL,
            temperature=1,
            max_tokens=RESPONSES_MAX_OUTPUT_TOKENS,
        )


    def get_context(self, url: str) -> str:
        data = self.build_llm_data(self.fetch(url))
        return (
            f"{CONTEXT_INSTRUCTIONS}"
            f"Candidate: {data['person']}\n"
            f"Experience: {data['experience']}\n"
            f"Skills pool: {', '.join(data['skills'])}\n"
            f"Reference tagline (style guide): {data['person'].get('tagline', '')}\n"
            f"Reference letter content (structure/length guide):\n{data['cover_letter']}\n\n"
            f"Job description (plaintext):\n{data['page_text']}\n\n"
        )
