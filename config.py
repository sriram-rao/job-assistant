from pathlib import Path

# Main application generation
OPENAI_MODEL = "gpt-5-mini"
OPENAI_TIER = "flex"
RESPONSES_MAX_OUTPUT_TOKENS = 16000
REASONING_EFFORT = "low"

# Job description extraction
OPENAI_EXTRACTION_MODEL = "gpt-5-nano"
EXTRACTION_MAX_TOKENS = 4096
EXTRACTION_TEMPERATURE = 0.3

# ATS validation
VALIDATION_MAX_TOKENS = 2000
VALIDATION_TEMPERATURE = 0.3

# LLM handler
HANDLER_MAX_TOKENS = 8192
HANDLER_TEMPERATURE = 1.0

# General
OPENAI_TIMEOUT = 300.0

# Cache directories
JOB_LISTING_CACHE_DIR = Path("target/job_listing_cache")
