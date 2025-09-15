# Job Assistant

Automates parts of the job-application process. I’m starting with auto-tuning applications: programmatically tailoring resumes and cover letters for each role using tokenized templates and sensible defaults.

## What It Does (today)
- Tokenized replacements: placeholders like `%%myname%%` replaced via `util/strings.py`.
- Central defaults: `defaults.py` provides personal data, skills, and letter/resume values.
- PDF builds: `main.py` uses `util.tex.compile_to_pdf(...)` for resume/letter PDFs.
- Assistant + LLM: fetch a job page, extract text, build structured data, and generate a tailored application JSON (letter, work experience bullets, skills).

## Workflow Overview
1. Author LaTeX templates in `resume/` and `letter/` with placeholders like `%%myname`, `%%company`, etc.
2. Provide data via `defaults.py` and/or a small dict at use time.
3. Build artifacts by running `python main.py` (or integrate the `assistant.replace(...)` helper in other scripts).

## Roadmap
- Job description parsing to extract skills, keywords, and requirements.
- Company and role research signals to guide customization.
- Template selection and content blocks based on extracted signals.
- Portal autofill and submission helpers (safe, review-first flow).
- Application tracking and iteration loops to improve targeting.

## Usage (basic)
- Edit values in `defaults.py` to set personal data, experience, skills, and letter snippets.
- Use `%%token` placeholders in your LaTeX files under `resume/` and `letter/`.
- Run: `python main.py` to compile the resume and cover letter PDFs.

## Assistant + LLM
- Networking: `net.web.get_html(url) -> str` fetches HTML; `net.web.download_page(url) -> Path` saves it.
- Assistant: `assistant.Assistant(llm)` exposes:
  - `fetch(url) -> str`: returns HTML string.
  - `to_text(html) -> str`: plaintext from HTML (scripts/styles removed; structure-aware newlines).
  - `build_llm_data(html) -> dict`: merges page text + your details/experience/skills/letter content.
  - `generate_application(html, *, model=None, temperature=0.2, max_tokens=800) -> str`: returns minified JSON.

Output schema (JSON):
- letter: object with 4 keys from `defaults.LETTER_CONTENT` (same order).
- work_experience: [{ company, role, start, end, location, bullets: [string] }].
- skills: 8–12 items chosen from job text or close synonyms from your skills pool.

Example:
- from assistant import Assistant
- from ml.openai import ChatGPT
- html = Assistant().fetch("https://example.com/job")
- result_json = Assistant(ChatGPT()).generate_application(html)

Tip: Save beautified JSON
- import json, pathlib as P
- p = P.Path("target/job.html")
- data = json.loads(result_json)
- (p.with_suffix(".application.json")).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

## Logging
- `main.setup_logging()` writes to `target/logs/app.log` (10 MB rotate, 5 backups) and stdout.
- Thread-aware logger names for Assistant (`assistant.<thread-name>`); main sets the default thread name to `main`.

Notes
- Keep secrets (API keys, tokens) out of the repo; prefer environment variables or local config files ignored by Git.
- LaTeX and any required tooling must be installed locally for PDF builds.
