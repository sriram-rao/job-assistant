#!/usr/bin/env python3
"""Test script to verify OpenAI API connectivity."""

import os
import sys
from ml.openai import ChatGPT, ChatRequest
from ml.llm import user

def test_openai():
    """Test OpenAI API connectivity with a simple completion request."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return False
    
    try:
        client = ChatGPT()
        response = client.chat(ChatRequest(
            messages=[user("Say 'Hello, world!'")],
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        ))
        
        if not response.choices:
            print("Error: No choices in response")
            return False
            
        print("OpenAI API is working!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"Error testing OpenAI API: {e}")
        return False

if __name__ == "__main__":
    success = test_openai()
    sys.exit(0 if success else 1)
