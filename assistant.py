import json
import logging
import threading
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from defaults import EXPERIENCE, LETTER_CONTENT, PERSON, SKILLS, SKILLS_CONSOLIDATED
from util.file import (
    archive_old_pdfs,
    compile_pdfs,
    generate_letter_files,
    generate_resume_files,
    html_to_text,
    rename_pdfs,
)
from ml.llm import DUMMY_LLM, LLM, to_request
from net.web import get_html


class LLMData(TypedDict):
    page_text: str
    person: dict[str, str | dict[str, str]]
    experience: list[dict[str, str | list[str]]]
    skills: list[str]
    cover_letter: dict[str, str]
    page_html: NotRequired[str]


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class Assistant:
    llm: LLM
    requirement: dict[str, str]
    schema: dict[str, str]

    def __init__(self, llm: LLM = DUMMY_LLM) -> None:
        self.llm = llm

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def fetch(self, url: str) -> str:
        self.log.info("fetching %s", url)
        self.log.info("About to fetch URL: %s", url)
        return get_html(url)

    def ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        req = to_request(
            prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )
        self.log.info("Calling LLM.chat, model=%s", model or "<default>")
        res = self.llm.chat(req)
        return res.choices[0].content if res.choices else "No response"

    async def schedule_ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        req = to_request(
            prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )
        self.log.info("Calling LLM.async_chat, model=%s", model or "<default>")
        res = await self.llm.async_chat(req)
        return res.choices[0].content if res.choices else "No response"

    def build_llm_data(self, html: str, *, include_raw_html: bool = False) -> LLMData:
        skills_all: list[str] = list(
            dict.fromkeys(
                s
                for d in (SKILLS, SKILLS_CONSOLIDATED)
                for v in d.values()
                for s in v
                if s
            )
        )
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

    def store_application(
        self, application: dict[str, object], out_dir: Path | None = None
    ) -> dict[str, Path]:
        """Store application materials: generate LaTeX files, compile to PDFs, and organize outputs."""
        details: dict[str, str] = cast(dict[str, str], application.get("details", {}))

        self.log.info("Generating letter files")
        generate_letter_files(details, cast(dict[str, str], application["letter"]))

        self.log.info("Generating resume files")
        generate_resume_files(
            cast(list[dict[str, str | list[str]]], application["work_experience"]),
            cast(list[str], application["skills"]),
        )

        target_dir = Path("target/autogen")
        target_dir.mkdir(parents=True, exist_ok=True)

        self.log.info("Archiving old PDFs")
        archive_old_pdfs(target_dir)

        self.log.info("Compiling PDFs")
        compile_pdfs(target_dir)

        self.log.info("Renaming/moving PDFs to final location")
        letter_pdf_final, resume_pdf_final = rename_pdfs(
            target_dir, details.get("company", "")
        )

        return {
            "letter_tex": Path("letter") / "body.tex",
            "letter_pdf": letter_pdf_final,
            "resume_tex": Path("resume") / "workexperience.tex",
            "resume_pdf": resume_pdf_final,
        }

    def generate_application(
        self,
        url: str,
        *,
        model: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2000,
        custom_prompt: str = "",
    ) -> str:
        prompt: str = "\n".join(
            [str(custom_prompt), self.get_context(url), self.get_full_requirements()]
        )
        self.log.info("About to generate application via LLM")
        return self.ask(
            prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )

    def generate_and_save_application(
        self, url: str, out_dir: Path | None = None
    ) -> dict[str, Path]:
        """Generate application from URL and save to disk."""
        self.log.info("Generating application JSON")
        application: dict[str, object] = cast(
            dict[str, object], json.loads(self.generate_application(url))
        )
        self.log.info("Storing application to disk")
        return self.store_application(application, out_dir)

    def ask_about(self, question: str, about_url: str) -> str:
        self.log.info("Asking assistant a question")
        return self.ask(
            self.get_context(about_url) + "\n" + question,
            model="gpt-5-mini",
            temperature=1,
            max_tokens=3000,
        )

    def get_full_requirements(self) -> str:
        return (
            "Requirements:\n"
            + "\n".join(self.requirement.values())
            + "Schema: "
            + self.get_schema("full")
        )

    def get_schema(self, type: str) -> str:
        if type in self.schema or type != "full":
            return self.schema.get(type, "")
        return (
            "{"
            f"'details': {self.schema['details_schema']},"
            f"'letter': {self.schema['letter_schema']},"
            f"'work_experience':[{self.schema['work_experience_schema']}],"
            f"'skills':{self.schema['skills_schema']}"
            "}"
        )

    def get_context(self, url: str) -> str:
        data = self.build_llm_data(self.fetch(url))
        return (
            "You are an expert in writing résumés and cover letters for tech job applications.\n"
            "You can tailor résumés so they get past the ATS.\n"
            "You are given candidate data and plaintext job description to draft output.\n"
            "Make all content as specific to the job description and the company as possible.\n"
            "You are allowed to use online facts about the company. Facts only. \n"
            "You are strictly not allowed to use any other external resources (e.g., Google Docs, Word, ...) "
            "nor any external tools (e.g., Google Sheets, Word, ...) "
            "nor any external libraries (e.g., Pandas, Numpy, ...).\n"
            f"Candidate: {data['person']}\n"
            f"Experience: {data['experience']}\n"
            f"Skills pool: {', '.join(data['skills'])}\n"
            f"Reference letter content (structure/length guide):\n{data['cover_letter']}\n\n"
            f"Job description (plaintext):\n{data['page_text']}\n\n"
        )

    requirement: dict[str, str] = {
        "letter": (
            f"- Cover letter must have exactly these 4 keys (in order): {','.join(LETTER_CONTENT.keys())}. The content is just a guideline."
            f"- Match the reference letter's tone. Keep the number of words within 25% of the reference letter's.\n"
        ),
        "work_experience": (
            "- Work experience must be r\u00e9sum\u00e9-ready (2-5 concise bullets per role).\n"
            "- Use strong action verbs, quantify result/impact.\n"
            "- Use keywords from the job text where applicable, especially in work-experience bullets; prefer exact matches.\n"
        ),
        "skills": "- Choose 10–15 skills related to the job; prefer skills in the job text.\n",
        "generic": "- Keep first-person voice, concise, professional.",
        "output": (
            "Output schema: return ONLY minified JSON (no markdown, no commentary).\n"
            "- Most importantly, do not fabricate facts; rephrase candidate's experience to suit the role while staying truthful."
        ),
    }

    schema: dict[str, str] = {
        "letter_schema": "{"
        + ",".join([f'"{k}":"..."' for k in LETTER_CONTENT.keys()])
        + "}",
        "work_experience_schema": '{"company":"...","role":"...","start":"...","end":"...",'
        + '"location":"...","bullets":["..."]}',
        "skills_schema": '["..."]',
        "details_schema": '{"company":"...","role":"...","recipient":"...","city":"...","state":"..."}',
    }
