from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import cast

from defaults import EXPERIENCE, LETTER_CONTENT, PERSON, SKILLS
from handlers.document_generator import LetterGenerator, ResumeGenerator
from handlers.llm_handler import LLMHandler
from handlers.llm_response_parser import LLMResponseParser
from handlers.web_parser import WebParser
from ml.gpt import GPT
from ml.agent import Agent
from settings import (
    CONTEXT_INSTRUCTIONS,
    FULL_SCHEMA,
    OPENAI_MODEL,
    REQUIREMENTS,
    RESPONSES_MAX_OUTPUT_TOKENS,
)
from util.file import archive_old_pdfs, compile_pdfs, html_to_text, rename_pdfs


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


def build_llm_data(html: str) -> dict[str, object]:
    """Build structured data for LLM from HTML."""
    # Only send core technical skills (exclude verbose "areas", "ecosystems", "data_science")
    core_skill_keys = ["languages", "databases", "compute_platforms", "backend", "infrastructure", "automation"]
    skills_filtered = [
        skill
        for key in core_skill_keys
        if key in SKILLS
        for skill in SKILLS[key]
    ]

    # Remove "category" field from experience (not needed for LLM)
    experience_clean = [
        {k: v for k, v in exp.items() if k != "category"}
        for exp in EXPERIENCE
    ]

    return {
        "page_text": html_to_text(html),
        "person": PERSON,
        "experience": experience_clean,
        "skills": list(dict.fromkeys(skills_filtered)),  # Remove duplicates, preserve order
        "cover_letter": LETTER_CONTENT,
    }


def get_context(url: str) -> str:
    """Build full prompt context from URL."""
    thread_logger().info("Fetching job text")

    web_parser = WebParser(GPT())
    html = web_parser.process(url)
    data = build_llm_data(html)
    person = cast(dict[str, str], data['person'])
    skills = ', '.join(cast(list[str], data['skills']))

    return (
        f"{CONTEXT_INSTRUCTIONS}"
        f"Candidate: {data['person']}\n"
        f"Experience: {data['experience']}\n"
        f"Skills: {skills}\n"
        f"Reference tagline: {person.get('tagline', '')}\n"
        f"Reference letter:\n{data['cover_letter']}\n\n"
        f"Job description:\n{data['page_text']}\n\n"
    )


def generate_application(
    job_text: str,
    llm: Agent,
    *,
    model: str = "",
    temperature: float = 0.2,
    max_tokens: int = RESPONSES_MAX_OUTPUT_TOKENS,
    custom_prompt: str = "",
    reasoning_effort: str = "low",
) -> str:
    """Generate application JSON from URL."""
    log = thread_logger()
    requirements = "\n".join(REQUIREMENTS.values())
    prompt = f"{custom_prompt}\n{job_text}\n{requirements}\nSchema: {FULL_SCHEMA}"

    log.info("About to generate application via LLM")
    client = LLMHandler(
        llm,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort
    )
    return client.process(prompt)


def generate_and_save_application(
    url: str,
    llm: Agent,
    out_dir: Path | None = None
) -> dict[str, Path]:
    """Generate application from URL and save to disk."""
    log = thread_logger()

    # text = WebParser().process(url)

    log.info("Generating application JSON")
    raw_response = generate_application(get_context(url), llm)

    response_parser = LLMResponseParser()
    application = response_parser.process(raw_response)

    log.info("Generating letter files")
    letter_generator = LetterGenerator()
    letter_generator.process(application)

    log.info("Generating resume files")
    resume_generator = ResumeGenerator()
    resume_generator.process(application)

    target_dir = Path("target/autogen")
    target_dir.mkdir(parents=True, exist_ok=True)

    log.info("Archiving old PDFs")
    archive_old_pdfs(target_dir)

    log.info("Compiling PDFs")
    compile_pdfs(target_dir)

    log.info("Renaming/moving PDFs to final location")
    company = cast(dict[str, str], application.get("details", {})).get("company", "")
    letter_pdf_final, resume_pdf_final = rename_pdfs(target_dir, company)


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
    gpt_client = AgentHandler(llm, model=OPENAI_MODEL, temperature=1, max_tokens=RESPONSES_MAX_OUTPUT_TOKENS)
    return gpt_client.process(prompt)
