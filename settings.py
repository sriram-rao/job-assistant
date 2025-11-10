# Prompt configuration for LLM resume generation
from defaults import LETTER_CONTENT

CONTEXT_INSTRUCTIONS = (
    "Expert in ATS-optimized résumés and cover letters for tech roles.\n"
    "Tailor all content to the job description and company (use factual company info).\n"
    "Prioritize job-relevant skills from candidate's profile. No duplicates.\n"
)

REQUIREMENTS: dict[str, str] = {
    "details": (
        "- First-person, concise, professional.\n"
        "- REQUIRED: Generate tailored tagline (max 4 lines, font 9) highlighting role-specific strengths. Use reference tagline as base, customize for job.\n"
        "- Professional, concise style. No pronouns or candidate name. May mention company names.\n"
    ),
    "letter": (
        f"- Must have these 4 keys in order: {','.join(LETTER_CONTENT.keys())}.\n"
        f"- Match reference letter's tone, tense, grammatical person. Length within 25% of reference. Use exact role name from posting.\n"
    ),
    "work_experience": (
        "- 2-5 tailored bullets per role as SEPARATE ARRAY ITEMS. Action verbs, quantified impact.\n"
        "- **Bold** job-relevant keywords (exact matches preferred). Unique bolded terms only.\n"
        "- Match job description phrasing. Ensure semantic accuracy. Maintain similar length to input.\n"
        "- Retain most bullets, rephrased to fit job application."
        "- Meaning of contributions in bullet points must not change. Only phrasing can change."
    ),
    "skills": (
        "- 10–15 job-relevant skills from job text, ordered by relevance.\n"
    ),
    "languages": (
        "- 8–12 programming languages (not frameworks/tools), ordered by job relevance.\n"
    ),
    "output": (
        "- Return ONLY minified JSON (no markdown, no commentary).\n"
        "- Never fabricate; rephrase truthfully to suit role.\n"
    ),
}

SCHEMAS: dict[str, str] = {
    "letter_schema": "{"
    + ",".join([f'"{k}":"..."' for k in LETTER_CONTENT.keys()])
    + "}",
    "work_experience_schema": '{"gsr":["..."],"dremio":["..."],"microsoft":["..."],"internmicrosoft":["..."],"drexel":["..."],"ta":["..."]}',
    "skills_schema": '["..."]',
    "languages_schema": '["..."]',
    "details_schema": '{"company":"...","role":"...","recipient":"...","city":"...","state":"...","tagline":"..."}',
}

# Pre-computed full schema
FULL_SCHEMA = (
    "{"
    f'"details": {SCHEMAS["details_schema"]},'
    f'"letter": {SCHEMAS["letter_schema"]},'
    f'"work_experience":{SCHEMAS["work_experience_schema"]},'
    f'"skills":{SCHEMAS["skills_schema"]},'
    f'"languages":{SCHEMAS["languages_schema"]}'
    "}"
)
