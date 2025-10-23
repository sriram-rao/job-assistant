#!/usr/bin/env python
"""Test script for LLMValidator with OpenAI resume PDF."""

import os
from handlers.web_parser import WebParser
from handlers.llm_client import LLMValidator

def main():
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Fetch job text from URL
    url = "https://jobs.ashbyhq.com/openai/2b5e8e15-7952-4170-a927-2ad68e318ed6"
    print(f"Fetching job description from: {url}")
    parser = WebParser()
    job_text = parser.process(url)
    print(f"Fetched {len(job_text)} characters of job text\n")

    # Initialize validator
    validator = LLMValidator(api_key=api_key)

    # Test with OpenAI resume
    resume_path = "target/autogen/openai_resume.pdf"

    print(f"Testing LLMValidator with resume: {resume_path}")
    print("=" * 60)

    result = validator.process({
        "job_text": job_text,
        "resume_pdf_path": resume_path
    })

    print(f"\nATS Score: {result['ats_score']}/100")
    print(f"\nFeedback:\n{result['feedback']}")
    print(f"\nSuggestions:")
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"{i}. {suggestion}")

if __name__ == "__main__":
    main()
