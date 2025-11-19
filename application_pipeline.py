from __future__ import annotations

import json
import logging
import shutil
import threading
from pathlib import Path
from typing import cast

from defaults import EXPERIENCE_MAP, LETTER_CONTENT, PERSON, get_skills
from handlers.document_generator import LetterGenerator, ResumeGenerator, ResumeDocxGenerator
from handlers.pdf_generator import DocxPDFGenerator
from handlers.llm_handler import LLMHandler
from handlers.llm_response_parser import LLMResponseParser
from handlers.web_parser import WebParser
from ml.gpt import GPT
from ml.agent import Agent
from config import OPENAI_MODEL, RESPONSES_MAX_OUTPUT_TOKENS
from settings import CONTEXT_INSTRUCTIONS, REQUIREMENTS, SCHEMAS
from util.file import html_to_text
from util.docx_util import archive_old_docx


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


def build_validation_context(validation_results: dict[str, object]) -> str:
    """Build context string from validation results."""
    context = (
        f"Previous ATS Validation Feedback:\n"
        f"Score: {validation_results.get('ats_score', 'N/A')}/100\n"
        f"Feedback: {validation_results.get('feedback', '')}\n"
        f"Suggestions:\n"
    )
    for suggestion in validation_results.get('suggestions', []):
        context += f"- {suggestion}\n"
    context += (
        f"\nNote: Not all suggestions may apply, especially if they recommend skills or experience "
        f"not present in the candidate's background. Focus on improvements that align with the candidate's actual qualifications.\n\n"
    )

    if "previous_application" in validation_results:
        context += f"Previous Resume Output:\n{json.dumps(validation_results['previous_application'], separators=(',', ':'))}\n\n"

    return context


def get_context(job_listing: str, validation_results: dict[str, object] | None = None) -> str:
    """Build full prompt context from job listing text."""
    log = thread_logger()
    log.info(f"Building context with job listing ({len(job_listing)} chars): {job_listing[:500]}...")
    skills = get_skills()

    context = (
        f"{CONTEXT_INSTRUCTIONS}"
        f"Candidate:\n{json.dumps(PERSON, separators=(',', ':'))}\n"
        f"Experience:\n{json.dumps(EXPERIENCE_MAP, separators=(',', ':'))}\n"
        f"Skills:\n{json.dumps(skills, separators=(',', ':'))}\n"
        f"Reference tagline (customize for job): {PERSON.get('tagline', '')}\n"
        f"Reference letter:\n{json.dumps(LETTER_CONTENT, separators=(',', ':'))}\n\n"
    )

    if validation_results:
        log.info("Including validation feedback in context")
        context += build_validation_context(validation_results)

    context += f"Job listing:\n{html_to_text(job_listing)}\n\n"
    return context


def build_schema(include_list: list[str]) -> str:
    schema_parts = ['"details": ' + SCHEMAS['details_schema']]
    if "letter" in include_list:
        schema_parts.append('"letter": ' + SCHEMAS['letter_schema'])

    if "resume" in include_list:
        schema_parts.extend([
            '"work_experience":' + SCHEMAS['work_experience_schema'],
            '"skills":' + SCHEMAS['skills_schema'],
            '"languages":' + SCHEMAS['languages_schema']
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


def customise_application(job_listing: str, llm: Agent, out_dir: Path,
                          include_list: list[str] = ["resume"],
                          validation_file: Path | None = None) -> dict[str, object]:
    """Generate application from job listing text and save to disk.

    Args:
        job_listing: Job listing text
        llm: LLM agent to use
        out_dir: Output directory (unused, for compatibility)
        include_list: List of components to include (letter, resume). Defaults to ["resume"]
        validation_file: Optional path to validation JSON file to include feedback in prompt

    Returns:
        Dict containing output paths and application data
    """
    log = thread_logger()

    validation_results = None
    if validation_file and validation_file.exists():
        log.info(f"Loading validation results from {validation_file}")
        with open(validation_file, "r", encoding="utf-8") as f:
            validation_results = json.load(f)

    log.info(f"Generating application JSON for: {include_list}")
    raw_response = generate_application(include_list, get_context(job_listing, validation_results), llm)
    application = LLMResponseParser().process(raw_response)

    if "letter" in include_list:
        log.info("Generating letter files")
        LetterGenerator().process(application)

    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Archiving old .docx and PDFs")
    archive_old_docx(out_dir)

    if "resume" in include_list:
        log.info("Generating resume .docx")
        application["output_dir"] = out_dir
        ResumeDocxGenerator().process(application)

        company = cast(dict[str, str], application.get("details", {})).get("company", "")
        company_slug = company.lower().replace(" ", "_")
        full_name = f"{PERSON['first_name']}_{PERSON['last_name']}".replace(" ", "_")

        docx_path = out_dir / f"{full_name}_{company_slug}_resume.docx"

        log.info("Converting .docx to PDF")
        pdf_path = DocxPDFGenerator().process(docx_path)

    return {
        "resume_docx": docx_path,
        "resume_pdf": pdf_path,
        "application_data": application,
    }


def ask_about(question: str, about_url: str, llm: Agent) -> str:
    """Ask a question about a job posting."""
    log = thread_logger()
    log.info("Asking assistant a question")

    prompt = (
        f"Answer the following question concisely based on the candidate information and job description provided.\n\n"
        f"Candidate:\n{json.dumps(PERSON, separators=(',', ':'))}\n"
        f"Experience:\n{json.dumps(EXPERIENCE_MAP, separators=(',', ':'))}\n"
        f"Skills:\n{json.dumps(get_skills(), separators=(',', ':'))}\n"
        f"Job description:\n{html_to_text(WebParser(GPT()).process(about_url))}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )
    gpt_client = LLMHandler(llm, model=OPENAI_MODEL, temperature=1, max_tokens=RESPONSES_MAX_OUTPUT_TOKENS)
    return gpt_client.process(prompt)
