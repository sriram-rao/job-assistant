from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast, override

from config import APPLICATION_MODEL
from defaults import build_profile
from util.safe import suppress_errors
from ml.agent import Agent
from .handler import Handler
from net.browser import Browser
from net.form import values_from_defaults, get_contact_attribute

def thread_logger() -> logging.Logger:
    name = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


@dataclass
class AutofillRequest:
    browser: Browser
    llm: Agent
    values: dict[str, Any] = field(default_factory=dict)
    uploads: dict[str, Path] = field(default_factory=dict)
    job_text: str = ""
    application_data: dict[str, object] | None = None
    model: str = APPLICATION_MODEL
    max_tokens: int = 512
    timeout_ms: int = 60_000
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "domcontentloaded"
    snapshot: Path | None = None


@dataclass
class AutofillResult:
    matched: list[str]
    missing: list[str]
    url: str
    field_count: int
    snapshot_path: Path | None
    uploads: dict[str, Path] = field(default_factory=dict)


class FormAutofill(Handler[AutofillRequest, AutofillResult]):
    """Fill a loaded form without submitting."""

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    def normalize(self, text: str) -> str:
        return " ".join(
            "".join(char.lower() if char.isalnum() else " " for char in text).split()
        )

    def match_field(self, target: str, profile: dict[str, object]) -> str | None:
        if not target:
            return None
        person = cast(dict[str, object], profile.get("person", {}))
        contact = cast(dict[str, object], profile.get("contact", {}))
        uploads = cast(dict[str, object], profile.get("uploads", {}) or {})
        skills = cast(dict[str, object], profile.get("skills", []))
        languages = cast(dict[str, object], profile.get("languages", []))
        cover_text = cast(dict[str, object], profile.get("cover_text", ""))
        tests: list[tuple[list[str], str | object | None]] = [
            (["resume", "cv"], uploads.get("resume")),
            (["cover", "letter", "motivation"], uploads.get("cover")),
            (["first", "name"], person.get("first_name")),
            (["last", "name"], person.get("last_name")),
            (["full", "name"], person.get("full_name")),
            (["email"], contact.get("email")),
            (["phone", "tel", "mobile"], contact.get("phone")),
            (["linkedin"], get_contact_attribute("linkedin.com/in", str(contact.get("linkedin", "")))),
            (["github"], get_contact_attribute("github.com", str(contact.get("github", "")))),
            (["website"], get_contact_attribute(str(contact.get("website", "")), "")),
            (["portfolio"], get_contact_attribute(str(contact.get("website", "")), "")),
            (["city", "location"], person.get("location")),
            (["skill"], ", ".join(s for s in str(skills)) if skills else None),
            (["language"], ", ".join(lang for lang in str(languages)) if languages else None),
            (["cover", "letter"], cover_text or None),
        ]
        for keywords, value in tests:
            if value is not None and all(k in target for k in keywords):
                return str(value)
        return None

    def fill_easy_fields(
        self,
        request: AutofillRequest,
        fields: list[dict[str, object]],
        profile: dict[str, object],
    ) -> dict[str, object]:
        values = values_from_defaults(fields)
        for field in fields:
            identifier = (
                str(field.get("name") or "")
                or str(field.get("id") or "")
                or str(field.get("aria-label") or "")
            )
            if not identifier:
                continue
            label = str(field.get("label")) or ""
            placeholder = str(field.get("placeholder")) or ""
            target = self.normalize(" ".join([identifier, label, placeholder]))
            ftype = (str(field.get("type") or "")).lower()

            if ftype == "file":
                hint = self.match_field(target, profile)
                if not hint:
                    continue
                values.setdefault(identifier, str(hint))

            hint = self.match_field(target, profile)
            if hint:
                values.setdefault(identifier, hint)

        values.update(request.values)
        for name, path in request.uploads.items():
            values.setdefault(name, str(path))
        return values

    def fill_files_only(
        self,
        request: AutofillRequest,
        fields: list[dict[str, object]],
    ) -> dict[str, object]:
        values: dict[str, object] = {}
        uploads = request.uploads or {}
        for f in fields:
            ident = (
                str(f.get("name") or "")
                or str(f.get("id") or "")
                or str(f.get("aria-label") or "")
            )
            if not ident:
                continue
            if (f.get("type") or "").lower() != "file":
                continue
            lid = ident.lower()
            if "resume" in lid and "resume" in uploads:
                values[ident] = uploads["resume"]
            if ("cover" in lid or "cover_letter" in lid) and "cover" in uploads:
                values[ident] = uploads["cover"]
        return values

    def llm_fill(
        self,
        request: AutofillRequest,
        fields: list[dict[str, object]],
        current: dict[str, object],
        profile: dict[str, object],
    ) -> dict[str, object]:
        llm = request.llm
        remaining = [
            f
            for f in fields
            if (f.get("name") or f.get("id") or f.get("aria-label")) not in current
        ]
        if not remaining:
            return {}
        payload = {
            "profile": {
                "person": profile.get("person"),
                "contact": profile.get("contact"),
                "skills": profile.get("skills"),
                "languages": profile.get("languages"),
                "details": (profile.get("application") or {}).get("details") if profile.get("application") else {},
            },
            "job_text": request.job_text[:4000],
            "fields": [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "aria": f.get("aria-label"),
                    "label": f.get("label"),
                    "placeholder": f.get("placeholder"),
                    "type": f.get("type"),
                    "options": f.get("options"),
                }
                for f in remaining
            ],
        }
        prompt = (
            "Given candidate data, job description, and form fields, fill values. "
            "Return JSON: {\"values\": {\"field_identifier\": \"value\"}}. "
            "Leave empty object if unsure. Skip buttons."
            f"\nPayload:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            raw = llm.chat(prompt, request.model, request.max_tokens, 0.2, "low")
            data = json.loads(raw)
            values = data.get("values") if isinstance(data, dict) else {}
            if isinstance(values, dict):
                return {str(k): v for k, v in values.items()}
        except Exception:
            return {}
        return {}

    def snapshot_dom(self, browser: Browser, snapshot: Path | None) -> Path | None:
        if not snapshot:
            return None
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(browser.page.content(), encoding="utf-8")
        return snapshot

    @override
    def process(self, input_data: AutofillRequest) -> AutofillResult:
        browser = input_data.browser
        browser.page.wait_for_load_state(input_data.wait_until, timeout=input_data.timeout_ms)

        profile = build_profile(input_data.application_data, input_data.uploads)
        fields = browser.extract_inputs(timeout_ms=input_data.timeout_ms)
        names = {
            str(f.get("name") or f.get("id") or f.get("aria-label") or "")
            for f in fields
            if f.get("name") or f.get("id") or f.get("aria-label")
        }
        # Default: files only; let user/plugins fill text fields
        values = self.fill_files_only(input_data, fields)

        browser.fill_fields(values)
        _ = suppress_errors(lambda: browser.page.evaluate("() => window.scrollTo(0,0)"))

        matched = sorted(k for k in values if k in names)
        missing = sorted(k for k in values if k not in names)
        snap = self.snapshot_dom(browser, input_data.snapshot)

        return AutofillResult(
            matched=matched,
            missing=missing,
            url=browser.page.url,
            field_count=len(fields),
            snapshot_path=snap,
            uploads={k: Path(v) if isinstance(v, (str, Path)) else Path() for k, v in (input_data.uploads or {}).items()},
        )
