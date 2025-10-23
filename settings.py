OPENAI_MODEL = "gpt-5-nano"
OPENAI_TIMEOUT = 300.0
RESPONSES_MAX_OUTPUT_TOKENS = 16000
REASONING_EFFORT = "low"


# Prompt configuration for LLM resume generation
from defaults import LETTER_CONTENT

CONTEXT_INSTRUCTIONS = (
    "You are an expert in writing résumés and cover letters for tech job applications.\n"
    "You can tailor résumés so they get past the ATS.\n"
    "You are given candidate data and plaintext job description to draft output.\n"
    "Make all content as specific to the job description and the company as possible.\n"
    "You are allowed to use online facts about the company. Facts only. \n"
    "Pick skills mentioned in the job description that are close to skills in the input candidate's list and place them first in the output returned. No duplicates.\n"
)

REQUIREMENTS: dict[str, str] = {
    "details": (
        "- Generate a tailored tagline (max. 4 lines on A4, font size 9) highlighting strengths for this role (can include technical expertise).\n"
        "- Match the style of the reference tagline: professional, concise, without using personal pronouns or the person's name.\n"
        "- Feel free to mention company names from the candidate's experience.\n"
    ),
    "letter": (
        f"- Cover letter must have exactly these 4 keys (in order): {','.join(LETTER_CONTENT.keys())}. The content is just a guideline."
        f"- Match the reference letter's tone. Keep the number of words within 25% of the reference letter's.\n"
        f"- Use the exact role name from the job posting when referring to the position.\n"
    ),
    "work_experience": (
        "- Generate tailored bullet points (2-5 bullets per role) for each position. Only bullet points must be part of the output schema.\n"
        "- Use strong action verbs, quantify result/impact.\n"
        "- Use **bold** for keywords from the job text where applicable for matching skills, prefer exact matches. All bolded keywords must be unique, no repeats.\n"
        "- Match language and phrasing with job description where possible. Ensure all content makes semantic sense, e.g. a lakehouse cannot power low-latency systems.\n"
        "- Length of work experience (when on a page) should be roughly the same as that in the input."
    ),
    "skills": (
        "- Choose 10–15 skills related to the job; prefer skills in the job text.\n"
        "- Order skills based on relevance to the job description (most relevant first).\n"
    ),
    "languages": (
        "- Choose 8–12 programming languages from the skills pool based on job relevance.\n"
        "- Order languages based on relevance.\n"
        "- Only include programming languages (e.g., Python, Java, C++, not frameworks or tools).\n"
    ),
    "generic": "- Keep first-person voice, concise, professional.",
    "output": (
        "Output schema: return ONLY minified JSON (no markdown, no commentary).\n"
        "- Most importantly, do not fabricate facts; rephrase candidate's experience to suit the role while staying truthful."
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
    f"'details': {SCHEMAS['details_schema']},"
    f"'letter': {SCHEMAS['letter_schema']},"
    f"'work_experience':{SCHEMAS['work_experience_schema']},"
    f"'skills':{SCHEMAS['skills_schema']},"
    f"'languages':{SCHEMAS['languages_schema']}"
    "}"
)
