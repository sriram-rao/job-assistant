import html as htmlmod
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from defaults import EXPERIENCE, LETTER_CONTENT, PERSON, SKILLS, SKILLS_CONSOLIDATED
from ml.llm import DUMMY_LLM, LLM, to_request
from net.web import get_html
from util import strings as string


class LLMData(TypedDict):
    page_text: str
    person: dict[str, str | dict[str, str]]
    experience: list[dict[str, str | list[str]]]
    skills: list[str]
    cover_letter: dict[str, str]
    page_html: NotRequired[str]


def replace(file: str, data: dict[str, str]) -> str:
    file_path = Path(file) if '/' in file else Path('resume') / file
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
        for key, value in data.items():
            content = content.replace(string.pad(key), value)
        return content


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


class Assistant:
    llm: LLM

    def __init__(self, llm: LLM = DUMMY_LLM) -> None:
        self.llm = llm

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def fetch(self, url: str) -> str:
        self.log.info("fetching %s", url)
        return get_html(url)

    def ask(self, prompt: str, *, model: str | None = None, temperature: float | None = None,
            max_tokens: int | None = None) -> str:
        req = to_request(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        res = self.llm.chat(req)
        return res.choices[0].message.content if res.choices else "No response"

    async def schedule_ask(self, prompt: str, *, model: str | None = None, temperature: float | None = None,
                           max_tokens: int | None = None) -> str:
        req = to_request(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        res = await self.llm.async_chat(req)
        return res.choices[0].message.content if res.choices else "No response"

    def build_llm_data(self, html: str, *, include_raw_html: bool = False) -> LLMData:
        skills_all: list[str] = list(
            dict.fromkeys(s for d in (SKILLS, SKILLS_CONSOLIDATED) for v in d.values() for s in v if s))
        data: LLMData = {
            "page_text": html_to_text(html),
            "person": PERSON,
            "experience": EXPERIENCE,
            "skills": skills_all,
            "cover_letter": LETTER_CONTENT,
        }
        if include_raw_html:
            data["page_html"] = html
        return data

    def make_letter(self, details: dict[str, str], letter: dict[str, str]) -> str:
        letter_keys = list(LETTER_CONTENT.keys())
        letter_parts = [letter.get(key, "") for key in letter_keys]
        return "\n\n".join(part for part in letter_parts if part.strip())

    def make_resume(self, work_experience: list[dict[str, str | list[str]]], skills: list[str]) -> tuple[str, str]:
        work_commands = []
        for i, exp in enumerate(work_experience):
            company = exp.get("company", "")
            role = exp.get("role", "")
            start = exp.get("start", "")
            end = exp.get("end", "")
            location = exp.get("location", "")
            bullets = exp.get("bullets", [])
            
            time_range = f"{start} - {end}" if start and end else start or end or ""
            
            bullet_items = "\n".join([f"        \\item {bullet}" for bullet in bullets]) if bullets else ""
            bullets_block = f"""    {{
    \\begin{{itemize}}
{bullet_items}
    \\end{{itemize}}
    }}""" if bullet_items else "    {}"
            
            work_cmd = f"\\makework{{exp{i}}}\n    {{{company}}}\n    {{{role}}}\n    {{{time_range}}}\n    {{{location}}}\n{bullets_block}"
            work_commands.append(work_cmd)
        
        workexperience_content = "\n\n".join(work_commands)
        skills_text = ", ".join(skills)
        
        workexp_content = replace("workexperience_template.tex", {
            "WORK_EXPERIENCE": workexperience_content,
        })
        
        info_content = replace("resume/info_template.tex", {
            "SKILLS": skills_text
        })
        
        return workexp_content, info_content

    def generate_letter_files(self, details: dict[str, str], letter: dict[str, str]) -> None:
        """Generate and write letter LaTeX files."""
        letter_dir = Path("letter")
        
        letter_content = self.make_letter(details, letter)
        string.write_to_file(letter_dir / "body.tex", letter_content)
        
        letter_info_content = replace("letter/info_template.tex", details)
        string.write_to_file(letter_dir / "info.tex", letter_info_content)

    def generate_resume_files(self, work_experience: list[dict[str, str | list[str]]], skills: list[str]) -> None:
        """Generate and write resume LaTeX files."""
        resume_dir = Path("resume")
        
        workexp_content, resume_info_content = self.make_resume(work_experience, skills)
        string.write_to_file(resume_dir / "workexperience.tex", workexp_content)
        string.write_to_file(resume_dir / "info.tex", resume_info_content)

    def archive_old_pdfs(self, target_dir: Path) -> None:
        """Move existing PDFs in target directory to an old/ subdirectory."""
        import shutil
        from datetime import datetime
        
        old_pdfs = list(target_dir.glob("*.pdf"))
        if old_pdfs:
            old_dir = target_dir / "old"
            old_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for pdf in old_pdfs:
                old_file = old_dir / f"{timestamp}_{pdf.name}"
                shutil.move(str(pdf), str(old_file))

    def compile_pdfs(self, target_dir: Path) -> None:
        """Compile letter and resume LaTeX files to PDFs."""
        import subprocess
        
        letter_dir = Path("letter")
        resume_dir = Path("resume")
        
        self.log.info("Compiling letter to PDF")
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(target_dir.absolute()), "simplecover.tex"],
            cwd=letter_dir, check=False, capture_output=True
        )
        
        self.log.info("Compiling resume to PDF")
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(target_dir.absolute()), "main.tex"],
            cwd=resume_dir, check=False, capture_output=True
        )

    def rename_pdfs(self, target_dir: Path, company_name: str) -> tuple[Path, Path]:
        """Rename generated PDFs with company name and return final paths."""
        import shutil
        
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

    def store_application(self, application: dict[str, Any], out_dir: Path | None = None) -> dict[str, Path]:
        """Store application materials: generate LaTeX files, compile to PDFs, and organize outputs."""
        details = application.get("details", {})
        
        self.generate_letter_files(details, application["letter"])
        self.generate_resume_files(application["work_experience"], application["skills"])
        
        target_dir = Path("target/autogen")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        self.archive_old_pdfs(target_dir)
        self.compile_pdfs(target_dir)
        
        letter_pdf_final, resume_pdf_final = self.rename_pdfs(target_dir, details.get("company", ""))
        
        return {
            "letter_tex": Path("letter") / "body.tex",
            "letter_pdf": letter_pdf_final,
            "resume_tex": Path("resume") / "workexperience.tex",
            "resume_pdf": resume_pdf_final
        }

    def generate_application(self, url: str, *, model: str = "", temperature: float = 0.2,
                             max_tokens: int = 2000, custom_prompt: str = "") -> str:
        prompt = "\n".join([str(custom_prompt), self.get_context(url), self.get_full_requirements()])
        return self.ask(prompt, model=model , temperature=temperature, max_tokens=max_tokens)

    def generate_and_save_application(self, url: str, out_dir: Path | None = None) -> dict[str, Path]:
        """Generate application from URL and save to disk."""
        application = json.loads(self.generate_application(url))
        return self.store_application(application, out_dir)

    def ask_about(self, question: str, about_url: str) -> str:
        return self.generate_application(about_url, custom_prompt=self.get_context(about_url) + question)

    def get_full_requirements(self) -> str:
        return ("Requirements:\n" + "\n".join(self.requirements.values())
                + "Schema: " + self.get_schema("full"))

    def get_schema(self, type: str) -> str:
        if type in self.schema or type != "full":
            return self.schema.get(type, "")
        return ("{"
                f"'details': {self.schema['details_schema']},"
                f"'letter': {self.schema['letter_schema']},"
                f"'work_experience':[{self.schema['work_experience_schema']}],"
                f"'skills':{self.schema['skills_schema']}"
                "}")

    def get_context(self, url: str) -> str:
        data = self.build_llm_data(self.fetch(url))
        return (
            "You are an expert in writing résumés and cover letters for tech job applications.\n"
            "You can tailor résumés so they get past the ATS.\n"
            "You are given candidate data and plaintext job description to draft output.\n"
            "Make all content as specific to the job description and the company as possible.\n"
            "You are allowed to use online facts about the company. Facts. \n"
            "You are strictly not allowed to use any other external resources (e.g., Google Docs, Word, ...) "
            "nor any external tools (e.g., Google Sheets, Word, ...) "
            "nor any external libraries (e.g., Pandas, Numpy, ...).\n"
            f"Candidate: {data['person']}\n"
            f"Experience: {data['experience']}\n"
            f"Skills pool: {', '.join(data['skills'])}\n"
            f"Reference letter content (structure/length guide):\n{data['cover_letter']}\n\n"
            f"Job description (plaintext):\n{data['page_text']}\n\n"
        )

    requirements: dict[str, str] = {
        "letter": (
            f"- Cover letter must have exactly these 4 keys (in order): {','.join(LETTER_CONTENT.keys())}. The content is just a guideline."
            f"- Match the reference letter's tone. Keep the number of words within 25% of the reference letter's.\n"),

        "work_experience": ("- Work experience must be résumé-ready (2-5 concise bullets per role).\n"
                            "- Use strong action verbs, quantify result/impact.\n"
                            "- Use keywords from the job text where applicable, especially in work-experience bullets; prefer exact matches.\n"),

        "skills": "- Choose 10–15 skills related to the job; prefer skills in the job text.\n",
        "generic": "- Keep first-person voice, concise, professional.",
        "output": ("Output schema: return ONLY minified JSON (no markdown, no commentary).\n"
                   "- Most importantly, do not fabricate facts; rephrase candidate's experience to suit the role while staying truthful.")

    }

    schema: dict[str, str] = {
        "letter_schema": "{" + ",".join([f'"{k}":"..."' for k in LETTER_CONTENT.keys()]) + "}",
        "work_experience_schema": '{"company":"...","role":"...","start":"...",'
                                  '"end":"...","location":"...","bullets":["..."]}',
        "skills_schema": '["..."]',
        "details_schema": '{"company":"...","role":"...","recipient":"...","city":"...","state":"..."}',
    }