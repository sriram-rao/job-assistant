from __future__ import annotations

import logging
import threading
from abc import abstractmethod
from pathlib import Path
from typing import cast

from .handler import Handler
from defaults import EXPERIENCE_MAP
from util.file import make_letter, make_resume, replace
from util import strings


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class DocumentGenerator(Handler[dict[str, object], None]):
    """Base class for generating LaTeX documents from application data."""

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    @abstractmethod
    def process(self, application: dict[str, object]) -> None:
        """Generate and write document files."""
        ...


class LetterGenerator(DocumentGenerator):
    """Generates cover letter LaTeX files from application data."""

    def process(self, application: dict[str, object]) -> None:
        """Generate and write letter LaTeX files."""
        details = cast(dict[str, str], application.get("details", {}))
        letter = cast(dict[str, str], application["letter"])

        letter_dir = Path("letter")
        letter_content = make_letter(details, letter)
        strings.write_to_file(letter_dir / "body.tex", letter_content)

        letter_info_content = replace("letter/info_template.tex", details)
        strings.write_to_file(letter_dir / "info.tex", letter_info_content)


class ResumeGenerator(DocumentGenerator):
    """Generates resume LaTeX files from application data."""

    def process(self, application: dict[str, object]) -> None:
        """Generate and write resume LaTeX files."""
        # Extract components
        details = cast(dict[str, str], application.get("details", {}))
        skills = cast(list[str], application.get("skills", []))
        languages = cast(list[str], application.get("languages", []))
        work_experience_bullets = cast(dict[str, list[str]], application.get("work_experience", {}))

        # Merge work experience
        work_experience = [
            {**meta, "bullets": work_experience_bullets.get(slug, []), "slug": slug}
            for slug, meta in EXPERIENCE_MAP.items()
        ]

        # Merge details with lists
        details_with_lists = {**details, "skills": skills, "languages": languages}

        resume_dir = Path("resume")
        workexp_content, resume_info_content = make_resume(work_experience, details_with_lists)
        strings.write_to_file(resume_dir / "workexperience.tex", workexp_content)
        strings.write_to_file(resume_dir / "info.tex", resume_info_content)
