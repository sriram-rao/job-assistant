from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import cast

from defaults import EXPERIENCE, LETTER_CONTENT, PERSON, get_skills
from handlers.document_generator import LetterGenerator, ResumeGenerator
from handlers.llm_handler import LLMHandler
from handlers.llm_response_parser import LLMResponseParser
from handlers.web_parser import WebParser
from ml.gpt import GPT
from ml.agent import Agent
from settings import (
    CONTEXT_INSTRUCTIONS,
    OPENAI_MODEL,
    REQUIREMENTS,
    RESPONSES_MAX_OUTPUT_TOKENS,
)
from settings import SCHEMAS
from util.file import archive_old_pdfs, compile_pdfs, html_to_text, rename_pdfs


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


def get_context(url: str) -> str:
    """Build full prompt context from URL."""
    thread_logger().info("Fetching job text")

    web_parser = WebParser(GPT())
    html = web_parser.process(url)
    skills = get_skills()

    return (
        f"{CONTEXT_INSTRUCTIONS}"
        f"Candidate: {PERSON}\n"
        f"Experience: {EXPERIENCE}\n"
        f"Skills: {skills}\n"
        f"Reference tagline: {PERSON.get('tagline', '')}\n"
        f"Reference letter:\n{LETTER_CONTENT}\n\n"
        f"Job description:\n{html_to_text(html)}\n\n"
    )


def build_schema(include_list: list[str]) -> str:
    schema_parts = ["'details': " + SCHEMAS['details_schema']]
    if "letter" in include_list:
        schema_parts.append("'letter': " + SCHEMAS['letter_schema'])

    if "resume" in include_list:
        schema_parts.extend([
            "'work_experience':" + SCHEMAS['work_experience_schema'],
            "'skills':" + SCHEMAS['skills_schema'],
            "'languages':" + SCHEMAS['languages_schema']
        ])
    return "{" + ",".join(schema_parts) + "}"



def build_requirements(include: list[str]) -> str:
    required_keys = ["details"]
    if "letter" in include:
        required_keys.append("letter")
    if "resume" in include:
        required_keys.extend(["work_experience", "skills", "languages"])
    required_keys.append("output")
    return "\n".join(value for key, value in REQUIREMENTS.items() if key in required_keys)


def generate_application(include_list: list[str], job_text: str, llm: Agent, model: str = "",
                         temperature: float = 0.2, max_tokens: int = RESPONSES_MAX_OUTPUT_TOKENS, 
                         custom_prompt: str = "", reasoning_effort: str = "low") -> str:
    log = thread_logger()
    include_list = include_list or ["resume"]

    prompt = (f"{custom_prompt}\n{job_text}\n"
        f"{build_requirements(include_list)}\n"
        f"Schema: {build_schema(include_list)}")

    log.info("Generating application via LLM (including: %s)", ", ".join(include_list))
    client = LLMHandler(llm, model, max_tokens, temperature, reasoning_effort)
    return client.process(prompt)


def customise_application(url: str, llm: Agent, out_dir: Path,
                          include_list: list[str] = ["resume"]) -> dict[str, Path]:
    """Generate application from URL and save to disk.

    Args:
        url: Job posting URL
        llm: LLM agent to use
        out_dir: Output directory (unused, for compatibility)
        include_list: List of components to include (letter, resume). Defaults to ["resume"]
    """
    log = thread_logger()

    log.info(f"Generating application JSON for: {include_list}")
    raw_response = generate_application(include_list, get_context(url), llm)
    application = LLMResponseParser().process(raw_response)

    if "letter" in include_list:
        log.info("Generating letter files")
        LetterGenerator().process(application)

    if "resume" in include_list:
        log.info("Generating resume files")
        ResumeGenerator().process(application)

    out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Archiving old PDFs")
    archive_old_pdfs(out_dir)

    log.info("Compiling PDFs")
    compile_pdfs(out_dir)

    log.info("Renaming/moving PDFs to final location")
    company = cast(dict[str, str], application.get("details", {})).get("company", "")
    letter_pdf_final, resume_pdf_final = rename_pdfs(out_dir, company, include_list)

    return {
        "letter_tex": Path("letter") / "body.tex",
        "letter_pdf": letter_pdf_final,
        "resume_tex": Path("resume") / "workexperience.tex",
        "resume_pdf": resume_pdf_final,
    }


def ask_about(question: str, about_url: str, llm: Agent) -> str:
    """Ask a question about a job posting."""
    log = thread_logger()
    log.info("Asking assistant a question")

    prompt = get_context(about_url) + "\n" + question
    gpt_client = LLMHandler(llm, model=OPENAI_MODEL, temperature=1, max_tokens=RESPONSES_MAX_OUTPUT_TOKENS)
    return gpt_client.process(prompt)
