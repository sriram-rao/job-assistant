from pathlib import Path
import logging
import threading
from util import strings as string
from net.web import get_html
from ml.llm import to_request, LLM
import re
import html as htmlmod
from defaults import PERSON, EXPERIENCE, SKILLS, SKILLS_CONSOLIDATED, LETTER_CONTENT


def replace(file: str, data: dict) -> str:
    with open(Path('resume') / file, encoding='utf-8') as f:
        content = f.read()
        for key, value in data.items():
            content = content.replace(string.pad(key), value)
        return content


def thread_logger() -> logging.Logger:
    name = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class Assistant:
    def __init__(self, llm: LLM | None = None) -> None:
        self.llm = llm
        
    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def fetch(self, url: str) -> str:
        self.log.info("fetching %s", url)
        return get_html(url)

    def ask(self, prompt: str, *, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> str:
        req = to_request(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        res = self.llm.chat(req)  # type: ignore[union-attr]
        return res.choices[0].message.content if res.choices else "No response"

    def to_text(self, html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"(?i)<\s*br\s*/?>|</\s*p\s*>|</\s*div\s*>|</\s*h[1-6]\s*>|</\s*li\s*>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = htmlmod.unescape(text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(\s*\n\s*)+", "\n", text)
        return text.strip()

    def build_llm_data(self, html: str, *, include_raw_html: bool = False) -> dict:
        skills_all = list(dict.fromkeys(s for d in (SKILLS, SKILLS_CONSOLIDATED) for v in d.values() for s in v if s))
        return {
            "page_text": self.to_text(html),
            "person": PERSON,
            "experience": EXPERIENCE,
            "skills": skills_all,
            "cover_letter": LETTER_CONTENT,
            **({"page_html": html} if include_raw_html else {}),
        }

    def generate_application(
        self,
        html: str,
        *,
        model: str | None = None,
        temperature: float | None = 0.2,
        max_tokens: int | None = 800,
    ) -> str:
        data = self.build_llm_data(html)
        letter_keys = list(LETTER_CONTENT.keys())
        ref_letter = "\n".join([LETTER_CONTENT.get(k, "") for k in letter_keys]).strip()
        ref_len = max(80, len(ref_letter.split()))

        letter_schema = "{" + ",".join([f'\"{k}\":\"...\"' for k in letter_keys]) + "}"
        schema = (
            '{"letter":' + letter_schema + ',"work_experience":[{"company":"...","role":"...","start":"...","end":"...","location":"...","bullets":["..."]}],"skills":["..."]}'
        )

        keys_list = ", ".join([f'"{k}"' for k in letter_keys])
        prompt = (
            "You are assisting with a job application.\n"
            "Use the provided candidate data and the plaintext job description to draft output.\n"
            "Requirements:\n"
            f"- Cover letter must have exactly these 4 keys (in order): {keys_list}.\n"
            f"- Match the reference letter's tone and be {ref_len}±15% words.\n"
            "- Do not fabricate facts; rephrase candidate experience to suit the role while staying truthful.\n"
            "- Work experience must be resume-ready bullet points (3–6 concise bullets per role, action verbs, quantify impact).\n"
            "- Choose 8–12 skills that occur in the job text or are close synonyms from the provided skills list.\n"
            "- Keep first-person voice, concise, professional.\n"
            "Output schema: return ONLY minified JSON (no markdown, no commentary).\n"
            f"{schema}\n\n"
            f"Candidate: {data['person']}\n"
            f"Experience: {data['experience']}\n"
            f"Skills pool: {', '.join(data['skills'])}\n"
            f"Reference letter content (structure/length guide):\n{ref_letter}\n\n"
            f"Job description (plaintext):\n{data['page_text']}\n"
        )
        return self.ask(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
