#!/usr/bin/env python3
"""Quick test of Gemini API to debug generation issue."""

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {bool(gemini_api_key)}")
print(f"API Key (first 20 chars): {gemini_api_key[:20] if gemini_api_key else 'NONE'}...")

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Return a JSON object with this exact structure:
{
  "rounds": [
    {
      "id": "test-1",
      "type": "text",
      "promptText": "Test prompt",
      "items": ["Item 1", "Item 2", "Item 3"]
    },
    {
      "id": "test-2",
      "type": "text",
      "promptText": "Test prompt 2",
      "items": ["Item A", "Item B", "Item C"]
    }
  ]
}"""
        
        print("\nCalling Gemini API...")
        response = model.generate_content(prompt, request_options={"timeout": 12})
        print(f"Success! Response length: {len(response.text)}")
        print(f"\nResponse:\n{response.text[:500]}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
else:
    print("ERROR: API key not found in .env")
