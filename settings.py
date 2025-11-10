# Prompt configuration for LLM resume generation
from defaults import LETTER_CONTENT

CONTEXT_INSTRUCTIONS = (
    "Expert in ATS-optimized résumés/letters for tech roles. Tailor to job/company. Job-relevant skills only, no duplicates.\n"
)

REQUIREMENTS: dict[str, str] = {
    "details": "First-person, concise, professional. REQUIRED: Tailored tagline (max 4 lines, font 9) for role. No pronouns/candidate name.",
    "letter": f"Full sentences. 4 keys in order: {','.join(LETTER_CONTENT.keys())}. Match reference tone/tense. Length ±25%. Use exact role name.",
    "work_experience": "2-5 bullets/role. No personal pronouns (I, my, me). Action verbs, quantified. **Bold** job-relevant keywords. Match job phrasing. Retain meaning, rephrase only.",
    "skills": "10–15 job-relevant skills, ordered by relevance.",
    "languages": "8–12 programming languages (not frameworks), ordered by relevance.",
    "output": "Return ONLY minified JSON. No markdown. Never fabricate.",
}

SCHEMAS: dict[str, str] = {
    "letter_schema": "{"
    + ",".join([f'"{k}":""' for k in LETTER_CONTENT.keys()])
    + "}",
    "work_experience_schema": '{"gsr":[""],"dremio":[""],"microsoft":[""],"internmicrosoft":[""],"drexel":[""],"ta":[""]}',
    "skills_schema": '[""]',
    "languages_schema": '[""]',
    "details_schema": '{"company":"","role":"","recipient":"","city":"","state":"","tagline":""}',
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
