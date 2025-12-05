from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import cast, override

from .handler import Handler
from defaults import EXPERIENCE_MAP, PERSON
from util.file import make_letter, make_resume, replace
from util import strings
from util.document import fill_docx


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class DocumentGenerator(Handler[dict[str, object], None], ABC):
    """Base class for generating LaTeX documents from application data."""

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    @abstractmethod
    @override
    def process(self, application: dict[str, object]) -> None:
        """Generate and write document files."""
        ...


class LetterGenerator(DocumentGenerator):
    """Generates cover letter LaTeX files from application data."""

    @override
    def process(self, application: dict[str, object]) -> None:
        """Generate and write letter LaTeX files."""
        details = cast(dict[str, str], application.get("details", {}))
        letter = cast(dict[str, str], application["letter"])
        details["state"] = details.get("state", "") or details.get("country", "")

        letter_dir = Path("letter")
        letter_content = make_letter(details, letter)
        strings.write_to_file(letter_dir / "body.tex", letter_content)

        letter_info_content = replace("letter/info_template.tex", details)
        strings.write_to_file(letter_dir / "info.tex", letter_info_content)


class ResumeGenerator(DocumentGenerator):
    """Generates resume LaTeX files from application data."""

    @override
    def process(self, application: dict[str, object]) -> None:
        """Generate and write resume LaTeX files."""
        work_experience_bullets = cast(dict[str, list[str]], application.get("work_experience", {}))
        work_experience = [
            {**meta, "bullets": work_experience_bullets.get(slug, []), "slug": slug}
            for slug, meta in EXPERIENCE_MAP.items()
        ]

        resume_dir = Path("resume")
        workexp_content, resume_info_content = make_resume(work_experience, application)
        strings.write_to_file(resume_dir / "workexperience.tex", workexp_content)
        strings.write_to_file(resume_dir / "info.tex", resume_info_content)


class ResumeDocxGenerator(DocumentGenerator):
    """Generates resume .docx files from application data."""

    @override
    def process(self, application: dict[str, object]) -> None:
        """Generate and write resume .docx file."""
        work_experience = cast(dict[str, list[str]], application["work_experience"])
        work_experience = [
            {
                "company": details["company"],
                "role": details["role"],
                "start": details["start"],
                "end": details["end"],
                "location": details["location"],
                "bullets": work_experience.get(xp_key, []),
                "xp_key": xp_key
            }
            for xp_key, details in EXPERIENCE_MAP.items()
        ]

        details: dict[str, object] = cast(dict[str, object], application["details"])
        details.update({"skills": application["skills"], "languages": application["languages"] })
        output_dir = cast(Path, application.get("output_dir", Path("target/autogen")))

        _ = generate_resume_docx(work_experience, details, output_dir)
        self.log.info(f"Generated resume .docx in {output_dir}")


def generate_resume_docx(work_experience: list[dict[str, str | list[str]]], details: dict[str, object], output_dir: Path) -> Path:
    """Generate resume .docx from template and return path."""
    details.update({"work_experience": work_experience})

    document = fill_docx(Path("resume") / "resume_template.docx", details)
    company_key = str(details.get("company", "custom")).lower().replace(" ", "_")
    full_name = f"{PERSON['first_name']}_{PERSON['last_name']}".replace(" ", "_")

    output_path = output_dir / f"{full_name}_{company_key}_resume.docx"
    document.save(str(output_path))
    return output_path

