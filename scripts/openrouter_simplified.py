#!/usr/bin/env python3
"""
Simplified script to test OpenRouter API using the exact format from their documentation.
"""
import os
import json
import requests
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

def test_openrouter():
    """Test OpenRouter with a minimal example from their docs."""
    print(f"Testing OpenRouter with API key: {api_key[:10]}... (length: {len(api_key)})")
    
    # API endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Headers according to OpenRouter docs
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Minimal payload
    payload = {
        "model": "openai/gpt-3.5-turbo", # Try with a simple model
        "messages": [
            {"role": "user", "content": "Say hello!"}
        ]
    }
    
    # Print what we're sending
    print("\nRequest:")
    print(f"URL: {url}")
    print(f"Headers: {json.dumps({k: (v[:10] + '...' if k == 'Authorization' else v) for k, v in headers.items()})}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Make the request
        print("\nSending request...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # Print response
        print(f"\nResponse status code: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS!")
            response_data = response.json()
            
            # Print the response content (truncated)
            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0].get("message", {}).get("content", "")
                if content:
                    print(f"\nResponse content: {content}")
        else:
            try:
                error_data = response.json()
                print(f"Error: {json.dumps(error_data, indent=2)}")
                
                # Look for specific error messages
                if "error" in error_data:
                    error_message = error_data["error"].get("message", "")
                    if "No auth credentials found" in error_message:
                        print("\nPossible authentication issues:")
                        print("1. API key format is invalid (should be 'sk-or-v1-...')")
                        print("2. API key has expired or been revoked")
                        print("3. You need to create a new API key in OpenRouter dashboard")
            except:
                print(f"Raw response: {response.text}")
    
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    # Try the models endpoint as a control test
    try:
        print("\n\nTrying models endpoint as control test...")
        models_url = "https://openrouter.ai/api/v1/models"
        models_response = requests.get(models_url, headers=headers, timeout=10)
        
        print(f"Models endpoint status code: {models_response.status_code}")
        
        if models_response.status_code == 200:
            print("Models endpoint SUCCESS!")
            # Count models returned
            models_data = models_response.json()
            model_count = len(models_data.get("data", []))
            print(f"Found {model_count} available models")
        else:
            print("Models endpoint failed")
            try:
                error_data = models_response.json()
                print(f"Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw response: {models_response.text}")
    
    except Exception as e:
        print(f"Models endpoint exception: {str(e)}")

if __name__ == "__main__":
    if not api_key:
        print("No OpenRouter API key found in .env file")
        exit(1)
    
    test_openrouter() 