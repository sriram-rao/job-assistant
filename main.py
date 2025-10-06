import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from assistant import Assistant
from ml.openai import OpenAI
from util.tex import compile_to_pdf

def discard(value: object) -> None:
    """Ignore a value."""
    pass


def setup_logging(dir_path: Path | None = None, level: int = logging.INFO) -> None:
    dir_path = dir_path or Path("target/logs")
    dir_path.mkdir(parents=True, exist_ok=True)
    log_file = dir_path / "app.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(log_file) for h in root.handlers):
        root.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        root.addHandler(stream_handler)


def generate_pdfs() -> None:
    """Compile resume and cover letter PDFs."""
    discard(compile_to_pdf("main", Path("resume"), "resume"))
    discard(compile_to_pdf("simplecover", Path("letter"), "letter"))


def demo_llm(url) -> None:
    # Placeholder URL and question; replace with a real job posting for actual use
    url = url or "file:///Users/sriramrao/Code/job-assistant/target/openings/Founding%20Engineer%20at%20Noise%20%E2%80%A2%20New%20York%20%E2%80%A2%20Remote%20(Work%20from%20Home)%20_%20Wellfound.html"
    question = "Write a cover letter showing my suitability for the role"
    letter: dict[str, str] = json.loads(Assistant(OpenAI()).generate_application(url, custom_prompt=question))["letter"]
    print("Generated Cover Letter:\n\n\t", "\n\t".join(letter.values()))


def generate_application_from_url(url: str, output_dir: Path | None = None) -> dict[str, Path]:
    """Generate and save tailored application materials (cover letter and resume) for a job posting URL.
    
    Args:
        url: Job posting URL to generate application for
        output_dir: Directory to save application files (defaults to "target")
    
    Returns:
        Dict mapping "letter" and "resume" to their respective file paths
    """
    setup_logging()
    logging.info(f"Generating application for: {url}")
    
    output_paths = Assistant(OpenAI()).generate_and_save_application(url, output_dir)
    
    logging.info(f"Application saved to: {output_paths}")
    return output_paths


if __name__ == "__main__":
    import sys
    
    parser = argparse.ArgumentParser(description="Generate tailored resume and cover letter from job posting URL")
    _ = parser.add_argument("url", nargs="?", help="Job posting URL")
    _ = parser.add_argument("-a", "--ask", action="store_true", help="Answer a question instead of generating PDFs")
    _ = parser.add_argument("-o", "--output", type=Path, help="Output directory (default: target)")
    _ = parser.add_argument("-q", "--question", type=str, help="Question to ask the assistant")
    
    args = parser.parse_args()
    
    if args.ask or args.question:
        prompt = args.question or "Write a cover letter showing my suitability for the role"
        print(Assistant(OpenAI()).ask_about(prompt, args.url))
    elif args.url:
        _ = generate_application_from_url(args.url, args.output)
    else:
        print("Usage: python main.py <job_url>")
        sys.exit(1)
