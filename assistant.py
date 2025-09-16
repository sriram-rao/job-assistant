from pathlib import Path
import logging
import threading
from util import strings as string
from net.web import get_html
from ml.llm import to_request, LLM, DUMMY_LLM
import re
import html as htmlmod
from defaults import PERSON, EXPERIENCE, SKILLS, SKILLS_CONSOLIDATED, LETTER_CONTENT
from typing import TypedDict, NotRequired


class LLMData(TypedDict):
    page_text: str
    person: dict[str, object]
    experience: list[dict[str, object]]
    skills: list[str]
    cover_letter: dict[str, str]
    page_html: NotRequired[str]


def replace(file: str, data: dict[str, str]) -> str:
    with open(Path('resume') / file, encoding='utf-8') as f:
        content = f.read()
        for key, value in data.items():
            content = content.replace(string.pad(key), value)
        return content


def thread_logger() -> logging.Logger:
    name = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


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

    def ask(self, prompt: str, *, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> str:
        req = to_request(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        res = self.llm.chat(req)
        return res.choices[0].message.content if res.choices else "No response"

    async def schedule_ask(self, prompt: str, *, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> str:
        req = to_request(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        res = await self.llm.async_chat(req)
        return res.choices[0].message.content if res.choices else "No response"

    def to_text(self, html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\\1>", " ", html)
        text = re.sub(r"(?i)<\s*br\s*/?>|</\s*p\s*>|</\s*div\s*>|</\s*h[1-6]\s*>|</\s*li\s*>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = htmlmod.unescape(text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(\s*\n\s*)+", "\n", text)
        return text.strip()

    def build_llm_data(self, html: str, *, include_raw_html: bool = False) -> LLMData:
        skills_all: list[str] = list(dict.fromkeys(s for d in (SKILLS, SKILLS_CONSOLIDATED) for v in d.values() for s in v if s))
        data: LLMData = {
            "page_text": self.to_text(html),
            "person": PERSON,
            "experience": EXPERIENCE,
            "skills": skills_all,
            "cover_letter": LETTER_CONTENT,
        }
        if include_raw_html:
            data["page_html"] = html
        return data

    def store_application(self, _application: dict[str, object], out_dir: Path | None = None) -> dict[str, Path]:
        # TODO: write cover letter/resume outputs and return file paths
        if out_dir is None:
            out_dir = Path("target")
        paths: dict[str, Path] = {}
        return paths

    def generate_application_prompt(self, data: LLMData, cover_letter: str, letter_keys: list[str]) -> str:
        base_words = max(80, len(cover_letter.split()))
        min_words = max(60, int(base_words * 0.85))
        max_words = int(base_words * 1.15)

        bullets_min, bullets_max = 3, 6
        skills_min, skills_max = 8, 12

        letter_schema = "{" + ",".join([f'"{k}":"..."' for k in letter_keys]) + "}"
        schema = (
            '{"letter":' + letter_schema + ',"work_experience":[{"company":"...","role":"...","start":"...","end":"...","location":"...","bullets":["..."]}],"skills":["..."]}'
        )

        keys_list = ", ".join([f'"{k}"' for k in letter_keys])
        return (
            "You are assisting with a job application.\n"
            "Use the provided candidate data and the plaintext job description to draft output.\n"
            "Requirements:\n"
            f"- Cover letter must have exactly these 4 keys (in order): {keys_list}.\n"
            f"- Match the reference letter's tone and be between {min_words} and {max_words} words.\n"
            "- Do not fabricate facts; rephrase candidate experience to suit the role while staying truthful.\n"
            f"- Work experience must be resume-ready bullet points ({bullets_min}–{bullets_max} concise bullets per role, action verbs, quantify impact).\n"
            "- Use job-description keywords wherever applicable in BOTH the work-experience bullets and the skills list; prefer exact matches or close synonyms.\n"
            f"- Choose {skills_min}–{skills_max} skills that occur in the job text or are close synonyms from the provided skills list.\n"
            "- Keep first-person voice, concise, professional.\n"
            "Output schema: return ONLY minified JSON (no markdown, no commentary).\n"
            f"{schema}\n\n"
            f"Candidate: {data['person']}\n"
            f"Experience: {data['experience']}\n"
            f"Skills pool: {', '.join(data['skills'])}\n"
            f"Reference letter content (structure/length guide):\n{cover_letter}\n\n"
            f"Job description (plaintext):\n{data['page_text']}\n"
        )

    def generate_application(
        self,
        url: str,
        *,
        model: str | None = None,
        temperature: float | None = 0.2,
        max_tokens: int | None = 800,
        custom_prompt: str | None = None,
    ) -> str:
        data = self.build_llm_data(self.fetch(url))
        letter_keys = list(LETTER_CONTENT.keys())
        ref_letter = "\n".join([LETTER_CONTENT.get(k, "") for k in letter_keys]).strip()

        prompt = custom_prompt or self.generate_application_prompt(data, ref_letter, letter_keys)
        return self.ask(prompt, model=model, temperature=temperature, max_tokens=max_tokens)

    def ask_about(self, question: str, about_url: str) -> str:
        return self.generate_application(about_url, custom_prompt=question)
