import argparse
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from application_pipeline import ask_about, customise_application
from handlers.llm_validator import Validator
from handlers.web_parser import WebParser
from ml.gpt import GPT
from net.web import sanitize_filename
from util.tex import compile_to_pdf

_ = load_dotenv()


def discard(_: object) -> None:
    """Ignore a value."""
    pass


def setup_logging(dir_path: Path | None = None, level: int = logging.INFO) -> None:
    dir_path = dir_path or Path("target/logs")
    dir_path.mkdir(parents=True, exist_ok=True)
    log_file = dir_path / "app.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers that would cause duplicates or write to stderr.
    for h in list(root.handlers):
        try:
            if isinstance(h, RotatingFileHandler) and getattr(
                h, "baseFilename", ""
            ) == str(log_file):
                root.removeHandler(h)
            if isinstance(h, logging.StreamHandler):
                root.removeHandler(h)
        except Exception:
            # If handler introspection fails for any reason, remove it to keep logging predictable.
            try:
                root.removeHandler(h)
            except Exception:
                pass

        # Add a fresh rotating file handler (writes to target/logs/app.log)
    file_handler = RotatingFileHandler(
        str(log_file), maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    # Add a stream handler that explicitly writes to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(level)
    root.addHandler(stream_handler)


def generate_pdfs() -> None:
    """Compile resume and cover letter PDFs."""
    logging.info("Compiling resume PDF...")
    discard(compile_to_pdf("main", Path("resume"), "resume"))
    logging.info("Compiling cover letter PDF...")
    discard(compile_to_pdf("simplecover", Path("letter"), "letter"))


def generate_application_from_url(
    url: str, output_dir: Path = Path("target/autogen"), include: list[str] | None = None,
    use_validation: bool = False
) -> dict[str, Path]:
    """Generate and save tailored application materials (cover letter and resume) for a job posting URL.

    Args:
        url: Job posting URL to generate application for
        output_dir: Directory to save application files (defaults to "target")
        include: List of components to include (letter, resume, validation)

    Returns:
        Dict mapping "letter" and "resume" to their respective file paths
    """
    setup_logging()
    include = include if include is not None else []

    logging.info(f"Generating application for: {url}")
    logging.info(f"Including: {', '.join(include) if include else 'none'}")
    logging.info(
        "About to call generate_and_save_application (LLM call + file IO)..."
    )

    # Fetch job listing once
    job_listing = WebParser(GPT()).process(url)

    # Check for existing validation file if requested
    validation_file = None
    if use_validation:
        vf = Path("target/validate") / f"{sanitize_filename(url)}.json"
        logging.info(f"Looking for validation file at: {vf}")
        if vf.exists():
            validation_file = vf
            logging.info(f"Found validation file: {validation_file}")
        else:
            logging.warning(f"Validation file not found: {vf}")

    # Only include docs that are in the include list
    docs_to_generate = [doc for doc in ["letter", "resume"] if doc in include]
    result = customise_application(job_listing, GPT(), output_dir, docs_to_generate, validation_file) if docs_to_generate else {}

    if "validation" not in include:
        return result

    resume_pdfs = list(output_dir.glob("*_resume.pdf"))
    if not resume_pdfs:
        return result

    latest_resume = max(resume_pdfs, key=lambda p: p.stat().st_mtime)
    validate_resume(job_listing, latest_resume, url, result.get("application_data"))
    return result


def validate_resume(job_listing: str, resume_pdf: Path, url: str, application_data: dict[str, object] | None = None):
    """
    Validate a resume using the provided job listing text and resume PDF.
    Save validation results along with application data for next iteration if provided.
    """
    logging.info("Running ATS validation")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    validator = Validator(api_key=api_key)
    validation_result = validator.process({
        "job_text": job_listing,
        "resume_pdf_path": str(resume_pdf)
    })

    # Save validation results to file
    output_dir = Path("target/validate")
    output_dir.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_filename(url)
    validation_file = output_dir / f"{sanitized}.json"

    # Include application data for next iteration only if provided
    if application_data: application_data["output_dir"] = str(application_data["output_dir"])
    save_data = {**validation_result, "previous_application": application_data} if application_data else validation_result

    with open(validation_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    logging.info("ATS Score: %s/100", validation_result["ats_score"])
    logging.info("Feedback: %s", validation_result["feedback"])
    logging.info("Suggestions: %s", "\n".join(cast(list[str], validation_result["suggestions"])))
    logging.info("Validation results saved to: %s", validation_file)


if __name__ == "__main__":
    # ensure logging is configured for both file and stdout
    setup_logging()
    logging.info("Starting job-assistant (CLI)")

    parser = argparse.ArgumentParser(
        description="Generate tailored resume and cover letter from job posting URL"
    )
    _ = parser.add_argument("url", nargs="?", help="Job posting URL")
    _ = parser.add_argument(
        "-a",
        "--ask",
        action="store_true",
        help="Answer a question instead of generating PDFs",
    )
    _ = parser.add_argument(
        "-o", "--output", type=Path, help="Output directory (default: target)"
    )
    _ = parser.add_argument(
        "-q", "--question", type=str, help="Question to ask the assistant"
    )
    _ = parser.add_argument(
        "-i",
        "--include",
        type=str,
        default="all",
        help="Comma-separated list of components to include (default: all). Options: letter, resume, validation, all"
    )
    _ = parser.add_argument(
        "-v",
        "--use-validation",
        action="store_true",
        help="Include validation feedback in resume generation prompt"
    )

    args = parser.parse_args()

    # Parse comma-separated include list
    valid_choices = {"letter", "resume", "validation", "all"}
    include_list = [item.strip() for item in args.include.split(",") if item.strip()]
    invalid_items = set(include_list) - valid_choices
    if invalid_items:
        parser.error(f"Invalid include options: {', '.join(invalid_items)}. Choose from: letter, resume, validation, all")

    # Expand "all" to all components
    if "all" in include_list:
        args.include = ["letter", "resume", "validation"]
    else:
        args.include = include_list

    if args.ask or args.question is not None:
        if not args.url:
            parser.error("URL is required when using -q/--question or -a/--ask")
        prompt = (
            args.question if args.question else "Write a cover letter showing my suitability for the role"
        )
        logging.info("About to ask assistant (LLM call) with provided prompt")
        print(ask_about(prompt, args.url, GPT()))
        logging.info("Assistant completed question response")
    elif args.url:
        logging.info("About to generate application for URL: %s", args.url)
        _ = generate_application_from_url(
            args.url,
            args.output or Path("target/autogen").resolve(),
            args.include,
            args.use_validation
        )
        logging.info("Finished application generation")
    else:
        logging.info("No URL provided; showing usage")
        print("Usage: python main.py <job_url>")
