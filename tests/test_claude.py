#!/usr/bin/env python
"""Test script for Claude class."""

import os
from ml.claude import Claude


def main():
    print("Testing Claude class")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    claude = Claude(api_key=api_key)
    print(f"Model: claude-haiku-4-5")

    messages = [{"role": "user", "content": "Say hello"}]
    responses = claude.chat_full(messages, max_tokens=200)
    print(f"Response: {responses[0]}")

    print("=" * 60)
    print("Claude test passed!")


if __name__ == "__main__":
    main()
