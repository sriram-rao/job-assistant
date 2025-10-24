#!/usr/bin/env python
"""Test script for GPT class."""

from ml.gpt import GPT


def main():
    print("Testing GPT class")
    print("=" * 60)

    gpt = GPT()
    print(f"Model: {gpt.model}")

    messages = [{"role": "user", "content": "Say hello"}]
    responses = gpt.chat_full(messages, max_tokens=200)
    print(f"Response: {responses[0]}")

    print("=" * 60)
    print("GPT test passed!")


if __name__ == "__main__":
    main()
