import argparse
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from application_pipeline import ask_about, generate_and_save_application, generate_application
from handlers.llm_validator import Validator
from handlers.web_parser import WebParser
from ml.gpt import GPT
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


def demo_llm(url: str) -> None:
    # Placeholder URL and question; replace with a real job posting for actual use
    url = (
        url
        or "file:///Users/sriramrao/Code/job-assistant/target/openings/Founding%20Engineer%20at%20Noise%20%E2%80%A2%20New%20York%20%E2%80%A2%20Remote%20(Work%20from%20Home)%20_%20Wellfound.html"
    )
    question = "Write a cover letter showing my suitability for the role"
    logging.info("About to call generate_application (LLM call)...")
    letter = cast(
        dict[str, str],
        json.loads(
        generate_application(WebParser().process(url), GPT(), custom_prompt=question)
        )["letter"],
    )
    logging.info("LLM returned generated letter")
    print("Generated Cover Letter:\n\n\t", "\n\t".join(letter.values()))


def generate_application_from_url(
    url: str, output_dir: Path | None = None
) -> dict[str, Path]:
    """Generate and save tailored application materials (cover letter and resume) for a job posting URL.

    Args:
        url: Job posting URL to generate application for
        output_dir: Directory to save application files (defaults to "target")

    Returns:
        Dict mapping "letter" and "resume" to their respective file paths
    """
    setup_logging()
    logging.info(f"Generating application for: {url}")
    logging.info(
        "About to call generate_and_save_application (LLM call + file IO)..."
    )

    output_paths = generate_and_save_application(url, GPT(), output_dir)
    validate_resume(url, output_paths["resume_pdf"])

    return output_paths


def validate_resume(job_url: str, resume_pdf: Path):
    """
    Validate a resume using the provided job URL and resume PDF.
    """
    text = WebParser().process(job_url)
    logging.info("Running ATS validation")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    validator = Validator(api_key=api_key)
    validation_result = validator.process({
        "job_text": text,
        "resume_pdf_path": str(resume_pdf)
    })
    logging.info("ATS Score: %s/100", validation_result["ats_score"])
    logging.info("Feedback: %s", validation_result["feedback"])
    logging.info("Suggestions: %s", ", ".join(cast(list[str], validation_result["suggestions"])))


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

    args = parser.parse_args()

    if args.ask or args.question is not None:
        prompt = (
            args.question if args.question else "Write a cover letter showing my suitability for the role"
        )
        logging.info("About to ask assistant (LLM call) with provided prompt")
        print(ask_about(prompt, args.url, GPT()))
        logging.info("Assistant completed question response")
    elif args.url:
        logging.info("About to generate application for URL: %s", args.url)
        _ = generate_application_from_url(args.url, args.output)
        logging.info("Finished application generation")
    else:
        logging.info("No URL provided; showing usage")
        print("Usage: python main.py <job_url>")
