from __future__ import annotations

import html as htmlmod
import logging
import re
import subprocess
import shutil
import threading
from datetime import datetime
from pathlib import Path

from defaults import LETTER_CONTENT
from util import strings as string


def escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    escaped = text
    for char, repl in replacements.items():
        escaped = escaped.replace(char, repl)
    return escaped


def thread_logger() -> logging.Logger:
    name = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


def html_to_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\\1>", " ", html)
    text = re.sub(r"(?i)<\s*br\s*/?>|</\s*p\s*>|</\s*div\s*>|</\s*h[1-6]\s*>|</\s*li\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = htmlmod.unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\s*\n\s*)+", "\n", text)
    return text.strip()


def replace(file: str, data: dict[str, str]) -> str:
    file_path = Path(file) if '/' in file else Path('resume') / file
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
        for key, value in data.items():
            content = content.replace(string.pad(key), value)
        return content


def make_letter(details: dict[str, str], letter: dict[str, str]) -> str:
    letter_keys = list(LETTER_CONTENT.keys())
    letter_parts = [letter.get(key, "") for key in letter_keys]
    return "\n\n".join(part for part in letter_parts if part.strip())


def make_resume(work_experience: list[dict[str, str | list[str]]], details: dict[str, str | list[str]]) -> tuple[str, str]:
    work_commands = []
    for i, exp in enumerate(work_experience):
        slug = str(exp.get("slug", f"exp{i}"))
        company = exp.get("company", "")
        role = exp.get("role", "")
        start = exp.get("start", "")
        end = exp.get("end", "")
        location = exp.get("location", "")
        bullets = exp.get("bullets", [])

        time_range = f"{start} - {end}" if start and end else start or end or ""

        # Convert markdown bold (**text**) to LaTeX bold (\textbf{text})
        latex_bullets = [re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', str(bullet)) for bullet in bullets]
        bullet_items = "\n".join([f"        \\item {bullet}" for bullet in latex_bullets]) if latex_bullets else ""
        bullets_block = f"""    {{
    \\begin{{itemize}}
{bullet_items}
    \\end{{itemize}}
    }}""" if bullet_items else "    {}"

        work_cmd = f"\\makework{{{slug}}}\n    {{{company}}}\n    {{{role}}}\n    {{{time_range}}}\n    {{{location}}}\n{bullets_block}"
        work_commands.append(work_cmd)

    workexperience_content = "\n\n".join(work_commands)

    skills = details.get("skills", [])
    languages = details.get("languages", [])
    skills_values = (
        [str(item).strip() for item in skills if str(item).strip()]
        if isinstance(skills, list)
        else ([str(skills).strip()] if str(skills).strip() else [])
    )
    language_values = (
        [str(item).strip() for item in languages if str(item).strip()]
        if isinstance(languages, list)
        else ([str(languages).strip()] if str(languages).strip() else [])
    )
    deduped_languages = string.dedupe_ordered(language_values, key=lambda value: value.lower())
    deduped_skills = string.dedupe_ordered(skills_values, key=lambda value: value.lower())
    escaped_skills = [escape_latex(value) for value in deduped_skills]
    skills_text = ", ".join(escaped_skills)
    languages_text = ", ".join(deduped_languages)
    tagline_raw = str(details.get("tagline", ""))
    tagline = string.strip_inline_markdown(tagline_raw)

    workexp_content = replace("workexperience_template.tex", {
        "WORK_EXPERIENCE": workexperience_content,
    })

    info_content = replace("resume/info_template.tex", {
        "SKILLS": skills_text,
        "LANGUAGES": languages_text,
        "tagline": tagline
    })

    return workexp_content, info_content


def generate_letter_files(application: dict[str, object]) -> None:
    """Generate and write letter LaTeX files."""
    from typing import cast

    details = cast(dict[str, str], application.get("details", {}))
    letter = cast(dict[str, str], application["letter"])

    letter_dir = Path("letter")
    letter_content = make_letter(details, letter)
    string.write_to_file(letter_dir / "body.tex", letter_content)

    letter_info_content = replace("letter/info_template.tex", details)
    string.write_to_file(letter_dir / "info.tex", letter_info_content)


def generate_resume_files(application: dict[str, object]) -> None:
    """Generate and write resume LaTeX files."""
    from typing import cast
    from defaults import EXPERIENCE_MAP

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
    string.write_to_file(resume_dir / "workexperience.tex", workexp_content)
    string.write_to_file(resume_dir / "info.tex", resume_info_content)


def archive_old_pdfs(target_dir: Path) -> None:
    """Move existing PDFs in target directory to an old/ subdirectory."""
    old_pdfs = list(target_dir.glob("*.pdf"))
    if old_pdfs:
        old_dir = target_dir / "old"
        old_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for pdf in old_pdfs:
            old_file = old_dir / f"{timestamp}_{pdf.name}"
            shutil.move(str(pdf), str(old_file))


def compile_pdfs(target_dir: Path) -> None:
    """Compile letter and resume LaTeX files to PDFs."""
    log = thread_logger()
    
    letter_dir = Path("letter")
    resume_dir = Path("resume")
    
    log.info("Compiling letter to PDF")
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(target_dir.absolute()), "simplecover.tex"],
        cwd=letter_dir, check=False, capture_output=True
    )
    
    log.info("Compiling resume to PDF")
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(target_dir.absolute()), "main.tex"],
        cwd=resume_dir, check=False, capture_output=True
    )


def rename_pdfs(target_dir: Path, company_name: str) -> tuple[Path, Path]:
    """Rename generated PDFs with company name and return final paths."""
    company_slug = company_name.lower().replace(" ", "_")
    
    letter_pdf_generated = target_dir / "simplecover.pdf"
    resume_pdf_generated = target_dir / "main.pdf"
    letter_pdf_final = target_dir / f"{company_slug}_letter.pdf"
    resume_pdf_final = target_dir / f"{company_slug}_resume.pdf"
    
    if letter_pdf_generated.exists():
        shutil.move(str(letter_pdf_generated), str(letter_pdf_final))
    if resume_pdf_generated.exists():
        shutil.move(str(resume_pdf_generated), str(resume_pdf_final))
    
    return letter_pdf_final, resume_pdf_final
