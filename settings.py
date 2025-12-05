# Prompt configuration for LLM resume generation
from defaults import LETTER_CONTENT

CONTEXT_INSTRUCTIONS = (
    "Expert in ATS-optimized résumés/letters for tech roles. Tailor to job/company. Job-relevant skills only, no duplicates.\n"
    "CRITICAL: Only use information from candidate data provided. Never fabricate or invent experiences, skills, or accomplishments.\n"
)

REQUIREMENTS: dict[str, str] = {
    "details": "First-person, concise, professional. REQUIRED: Tailored tagline (max 4 lines, font 9) for role. No pronouns/candidate name. Perfect grammar and punctuation mandatory.",
    "letter": f"First-person full sentences (use I, my, me). 4 keys in order: {','.join(LETTER_CONTENT.keys())}. Match reference tone/tense. Length should be roughly the same. Use exact role name.",
    "work_experience": "2-5 bullets/role. No personal pronouns (I, my, me). Action verbs, quantified. **Bold** job-relevant keywords. Match job phrasing. Retain meaning, rephrase only.\nEach array element must represent a single bullet point.",
    "skills": "Multiple categories of job-relevant skills. Must not include languages.",
    "languages": "Programming languages (not frameworks), ordered by relevance.",
    "output": "CRITICAL: Response must be valid, parseable JSON. Verify syntax before responding.",
}

SCHEMAS: dict[str, str] = {
    "letter_schema": "{"
    + ",".join([f'"{k}":""' for k in LETTER_CONTENT.keys()])
    + "}",
    "work_experience_schema": '{"gsr":["string",...],"dremio":["string",...],"microsoft":["string",...],"internmicrosoft":["string",...],"drexel":["string",...],"ta":["string",...]}',
    "skills_schema": '[{"Backend":["Spring","REST",...]},{"Data Systems":["Spark","Trino",...]},...]',
    "languages_schema": '[{"Languages":["Java","Python","C++",...]}]',
    "details_schema": '{"company":"string","role":"string","recipient":"string","city":"string","state":"string","country":"string","tagline":"string"}',
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
