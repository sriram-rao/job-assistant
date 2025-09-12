# Job Assistant

Automates parts of the job-application process. I’m starting with auto-tuning applications: programmatically tailoring resumes and cover letters for each role using tokenized templates and sensible defaults.

## What It Does (today)
- Tokenized replacements: use placeholders like `%%myname` in templates; they’re replaced via a simple helper in `util/string.py` and data you provide.
- Central defaults: `defaults.py` defines `Common`, `Letter`, and `Resume` plus `with_overrides()` to merge and override values.
- PDF builds: `main.py` invokes `tex.compile_to_pdf(...)` to produce PDFs for the resume and a simple cover letter from LaTeX sources in `resume/` and `letter/`.

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
- Edit values in `defaults.py` to set your personal and letter/resume defaults.
- Use `%%token` placeholders in your LaTeX files under `resume/` and `letter/`.
- Run: `python main.py` to compile the resume and cover letter PDFs.

Notes
- Keep secrets (API keys, tokens) out of the repo; prefer environment variables or local config files ignored by Git.
- LaTeX and any required tooling must be installed locally for PDF builds.

