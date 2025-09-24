# Job Assistant

A small helper to tailor resumes and cover letters for specific job posts using templates, sensible defaults, and an LLM.

### Features
- Token replacement in LaTeX/text templates via `util/strings.py` (`%%token%%`).
- Central defaults in `defaults.py`: `PERSON`, `EXPERIENCE`, `SKILLS (+ CONSOLIDATED)`, `LETTER_CONTENT`.
- Assistant + LLM: fetch URL → extract text → build candidate data → generate application JSON.
- PDF build for resume and letter (LaTeX required).

### Install
- Python 3.11+
- Optional: LaTeX (TeX Live/MiKTeX) for PDFs
- Install deps as needed for your LLM client (see `ml/`).

### Setup
1) Edit `defaults.py` to add your details and letter sections.
2) Put templates in `resume/` and `letter/` using tokens like `%%first_name%%`, `%%company%%`.

### Quickstart
```python
from assistant import Assistant
from ml.openai import ChatGPT

url = "https://example.com/job-post"
assistant = Assistant(ChatGPT())  # or Assistant() to use the dummy LLM
result_json_str = assistant.generate_application(url)
```

Pretty-print and save next to an HTML file you saved:
```python
import json
from pathlib import Path as P
p = P("target/openings/job.html")
data = json.loads(result_json_str)
(p.with_suffix(".application.json")).write_text(
    json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
)
```

### CLI / scripts (`main.py`)
- `demo_llm()` – quick demo that prints a generated letter.
- `generate_pdfs()` – compiles LaTeX in `resume/` and `letter/`.
- `textify_file(path)` – prints plaintext from an HTML file.
- Logging: `setup_logging()` writes to `target/logs/app.log` and stdout.

### Assistant API (cheatsheet)
- `Assistant.fetch(url) -> str` – HTML.
- `Assistant.to_text(html) -> str` – plaintext.
- `Assistant.build_llm_data(html, include_raw_html=False) -> dict` – merges page text + your data.
- `Assistant.generate_application(url, *, model=None, temperature=0.2, max_tokens=800, custom_prompt=None) -> str` – minified JSON string.
- `Assistant.ask_about(question, about_url) -> str` – same as above, with your question prepended.
- `Assistant.store_application(application: dict, out_dir=Path("target")) -> {"letter": Path, "resume": Path}` – writes `letter.txt` and `resume.txt`.

### Output schema (returned JSON string)
```json
{
  "letter": { "Intro": "...", "Why do I want to join this company?": "...", "Why should this company pick me?": "...", "Outro": "..." },
  "work_experience": [ { "company": "...", "role": "...", "start": "...", "end": "...", "location": "...", "bullets": ["..."] } ],
  "skills": ["..."]
}
```

### Notes
- Keep secrets out of the repo (use env vars/local config).
- `make_resume(...)` is a placeholder—fill in as needed.
- LaTeX is only required if you build PDFs.
