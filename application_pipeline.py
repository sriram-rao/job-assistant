from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import cast

from defaults import EXPERIENCE_MAP, LETTER_CONTENT, PERSON, get_skills
from handlers.browser_loader import BrowserLoader, wait_until_literal
from handlers.document_generator import LetterGenerator, ResumeDocxGenerator
from handlers.form_autofill import AutofillRequest, AutofillResult, FormAutofill
from handlers.llm_handler import LLMHandler
from handlers.llm_response_parser import LLMResponseParser
from handlers.pdf_generator import DocxPDFGenerator, LatexPDFGenerator
from handlers.web_parser import WebParser
from ml.gpt import GPT
from ml.agent import Agent
from net.browser import Browser
from config import APPLICATION_MODEL, RESPONSES_MAX_OUTPUT_TOKENS
from net.web import sanitize_filename
from settings import CONTEXT_INSTRUCTIONS, REQUIREMENTS, SCHEMAS
from util.file import html_to_text
from util.document import archive_old_docx
import shutil


def get_thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


def open_browser_for(
    url: str,
    headless: bool = True,
    wait_until: wait_until_literal = "domcontentloaded",
    timeout_ms: int = 60_000,
    executable_path: str | None = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    user_data_dir: Path | None = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser-Autofill",
) -> Browser:
    """Load page once and return the live browser instance."""
    return BrowserLoader(
        headless=headless,
        wait_until=wait_until,
        timeout_ms=timeout_ms,
        executable_path=executable_path,
        user_data_dir=user_data_dir,
    ).process(url)


def autofill_form(
    browser: Browser,
    llm: Agent,
    values: dict[str, object] | None = None,
    uploads: dict[str, Path] | None = None,
    job_text: str = "",
    application_data: dict[str, object] | None = None,
    *,
    snapshot: Path | None = None,
    wait_until: wait_until_literal = "domcontentloaded",
    timeout_ms: int = 60_000,
) -> AutofillResult:
    """Fill fields (no submit) using a shared browser session."""
    resolved_uploads: dict[str, Path] = dict(uploads or {})
    if not resolved_uploads:
        autogen = Path("target/autogen")
        resumes = sorted(
            list(autogen.glob("*_resume.docx"))
            + list(autogen.glob("*_resume.pdf")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        covers = sorted(
            list(autogen.glob("*_cover_letter.pdf")) + list(autogen.glob("*_letter.pdf")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if resumes:
            resolved_uploads["resume"] = resumes[0]
        if covers:
            path = covers[0]
            resolved_uploads.setdefault("cover", path)
            resolved_uploads.setdefault("cover_letter", path)
    request = AutofillRequest(
        browser=browser,
        values=values or {},
        uploads=resolved_uploads,
        llm=llm,
        job_text=job_text,
        application_data=application_data,
        snapshot=snapshot,
        wait_until=wait_until,
        timeout_ms=timeout_ms,
    )
    return FormAutofill().process(request)


def autofill_with_outputs(
    url: str,
    *,
    llm: Agent,
    job_text: str,
    application_data: dict[str, object] | None,
    resume_pdf: Path | str | None = None,
    letter_pdf: Path | str | None = None,
    headless: bool = False,
    timeout_ms: int = 60_000,
) -> tuple[AutofillResult, Browser]:
    """Open page and autofill using generated artifacts; caller closes browser."""
    browser = open_browser_for(url, headless, "networkidle", timeout_ms)
    uploads: dict[str, Path] = {}
    if resume_pdf:
        uploads["resume"] = Path(resume_pdf)
    if letter_pdf:
        uploads["cover"] = Path(letter_pdf)
    snapshot = Path("target/autofill") / f"{sanitize_filename(url)}.html"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    result = autofill_form(
        browser,
        llm,
        values={},
        uploads=uploads,
        job_text=job_text,
        application_data=application_data,
        snapshot=snapshot,
        wait_until="networkidle",
        timeout_ms=timeout_ms,
    )
    return result, browser


def generate_output_filename(application: dict[str, object], out_dir: Path, suffix: str) -> Path:
    """Return output filename for application documents.
    """
    company = cast(dict[str, str], application.get("details", {})).get("company", "")
    company_slug = company.lower().replace(" ", "_")
    full_name = f"{PERSON['first_name']}_{PERSON['last_name']}".replace(" ", "_")
    return out_dir / f"{full_name}_{company_slug}_{suffix}"


def build_validation_context(validation_results: dict[str, str | list[str]]) -> str:
    """Build context string from validation results."""
    context = (
        f"Previous ATS Validation Feedback:\n"
        f"Score: {validation_results.get('ats_score', 'N/A')}/100\n"
        f"Feedback: {validation_results.get('feedback', '')}\n"
        f"Suggestions:\n"
    )
    suggestions = [ f"- {suggestion}" for suggestion  in validation_results.get("suggestions", []) ]
    context += "\n".join(suggestions) + (
        "\nNote: Not all suggestions may apply, especially if they recommend skills or experience "
        "not present in the candidate's background. Focus on improvements that align with the candidate's actual qualifications.\n\n"
    )

    if "previous_application" not in validation_results:
        return context
    return context + (
        f"Previous Resume Output (use as reference for resume and improve based on feedback above):\n"
        f"{json.dumps(validation_results['previous_application'], separators=(',', ':'))}\n\n"
    )


def make_llm_context(job_listing: str, validation_results: dict[str, str | list[str]] | None = None) -> str:
    """Build full prompt context from job listing text."""
    log = get_thread_logger()
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


def generate_application(include_list: list[str], job_text: str, llm: Agent, model: str = APPLICATION_MODEL,
                         temperature: float = 0.2, max_tokens: int = RESPONSES_MAX_OUTPUT_TOKENS,
                         custom_prompt: str = "", reasoning_effort: str = "low") -> str:
    log = get_thread_logger()
    include_list = include_list or ["resume"]

    prompt = (f"{custom_prompt}\n{job_text}\n"
        f"{build_requirements(include_list)}\n"
        f"Schema: {build_schema(include_list)}")

    log.info("Generating application via LLM (including: %s)", ", ".join(include_list))
    client = LLMHandler(llm, model, max_tokens, temperature, reasoning_effort)
    return client.process(prompt)

def get_previous_validation(file: Path | None):
    if not (file and file.exists()):
        return None
    get_thread_logger().info(f"Loading validation results from {file}")
    with file.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_letter(application: dict[str, object], out_dir: Path) -> str | Path:
    log = get_thread_logger()
    log.info("Generating letter files")
    LetterGenerator().process(application)

    log.info("Compiling letter to PDF")
    letter_tex = Path("letter/simplecover.tex")
    _ = LatexPDFGenerator().process(letter_tex)

    letter_pdf_path = shutil.copy2(Path("letter/simplecover.pdf"),
                                   generate_output_filename(application, out_dir, "cover_letter.pdf"))
    log.info(f"Copied letter PDF to {letter_pdf_path}")
    return letter_pdf_path

def generate_resume(application, out_dir) -> tuple[str | Path, str | Path]:
    pass

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
    log = get_thread_logger()

    response: dict[str, object] = {}
    previous_validation = get_previous_validation(validation_file) if "validate" in include_list else None

    log.info(f"Generating application JSON for: {include_list}")
    response["application_data"] = LLMResponseParser().process(
        generate_application(include_list, 
                             make_llm_context(job_listing, previous_validation), llm)
    )

    log.info("Archiving old .docx and PDFs")
    archive_old_docx(out_dir)

    if "letter" in include_list:
        response["letter_path"] = generate_letter(response["application_data"], out_dir)


    if "resume" in include_list:
        application = response["application_data"]
        log.info("Generating resume .docx")
        application["output_dir"] = out_dir
        ResumeDocxGenerator().process(application)

        response["resume_docx"] = generate_output_filename(application, out_dir, "resume.docx")

        log.info("Converting .docx to PDF")
        response["resume_pdf"] = DocxPDFGenerator().process(response["resume_docx"])

    return response


def ask_about(question: str, about_url: str, llm: Agent) -> str:
    """Ask a question about a job posting."""
    log = get_thread_logger()
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
    gpt_client = LLMHandler(llm, model=APPLICATION_MODEL, temperature=1, max_tokens=RESPONSES_MAX_OUTPUT_TOKENS)
    return gpt_client.process(prompt)
