#!/usr/bin/env python3
"""
Script to replace the OpenRouter API key in the .env file and test if it works.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

def replace_openrouter_key(new_key):
    """Replace the OpenRouter API key in the .env file."""
    print(f"Replacing API key with: {new_key[:10]}... (length: {len(new_key)})")
    
    # Read the .env file
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"ERROR: {env_file} not found.")
        return False
    
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Replace the key
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("OPENROUTER_API_KEY="):
            new_lines.append(f"OPENROUTER_API_KEY={new_key}\n")
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        print("WARNING: OPENROUTER_API_KEY not found in .env file. Adding it.")
        new_lines.append(f"OPENROUTER_API_KEY={new_key}\n")
    
    # Write the updated file
    with open(env_file, "w") as f:
        f.writelines(new_lines)
    
    print("API key updated successfully.")
    return True

def test_openrouter():
    """Test if the new API key works with OpenRouter."""
    print("\nTesting OpenRouter API key...")
    
    # Reload environment variables
    load_dotenv(override=True)
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Headers for the API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test endpoints
    endpoints = [
        {
            "name": "Models List",
            "url": "https://openrouter.ai/api/v1/models",
            "method": "GET",
            "payload": None
        },
        {
            "name": "Chat Completion",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "method": "POST",
            "payload": {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Say hello!"}
                ]
            }
        }
    ]
    
    success = True
    
    for endpoint in endpoints:
        print(f"\nTesting endpoint: {endpoint['name']}")
        
        try:
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], headers=headers, timeout=30)
            else:
                response = requests.post(endpoint["url"], headers=headers, json=endpoint["payload"], timeout=30)
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ SUCCESS!")
                
                if endpoint["name"] == "Models List":
                    models_data = response.json()
                    model_count = len(models_data.get("data", []))
                    print(f"Found {model_count} available models")
                
                if endpoint["name"] == "Chat Completion":
                    response_data = response.json()
                    if "choices" in response_data and response_data["choices"]:
                        content = response_data["choices"][0].get("message", {}).get("content", "")
                        if content:
                            print(f"Response: {content[:100]}...")
            else:
                success = False
                print("✗ FAILED")
                try:
                    error_data = response.json()
                    print(f"Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error: {response.text}")
        
        except Exception as e:
            success = False
            print(f"✗ ERROR: {str(e)}")
    
    if success:
        print("\n===========================================")
        print("✅ ALL TESTS PASSED - OPENROUTER IS WORKING!")
        print("===========================================")
        print("\nYou can now use the OpenRouter API for your URL analysis.")
        print("Run: python reanalyze_remaining_with_openai.py")
    else:
        print("\n=================================================")
        print("❌ SOME TESTS FAILED - OPENROUTER IS NOT WORKING")
        print("=================================================")
        print("\nCheck your OpenRouter account and API key permissions.")
        print("You can still use the OpenAI fallback for URL analysis:")
        print("Run: python reanalyze_remaining_with_openai.py")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python replace_openrouter_key.py YOUR_NEW_API_KEY")
        return
    
    new_key = sys.argv[1]
    if replace_openrouter_key(new_key):
        test_openrouter()

if __name__ == "__main__":
    main() 