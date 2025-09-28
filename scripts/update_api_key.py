#!/usr/bin/env python3
"""
Script to update the OpenRouter API key in the .env file.
"""
import os
import sys

def update_openrouter_api_key(new_api_key):
    """
    Update the OpenRouter API key in the .env file.
    
    Args:
        new_api_key (str): The new OpenRouter API key
    """
    # Path to the .env file
    env_file_path = ".env"
    
    if not os.path.exists(env_file_path):
        print(f"Error: .env file not found at {env_file_path}")
        return False
    
    # Read the current content of the .env file
    with open(env_file_path, "r") as f:
        lines = f.readlines()
    
    # Update the API key line
    updated_lines = []
    api_key_updated = False
    
    for line in lines:
        if line.startswith("OPENROUTER_API_KEY="):
            updated_lines.append(f"OPENROUTER_API_KEY={new_api_key}\n")
            api_key_updated = True
        else:
            updated_lines.append(line)
    
    # Write the updated content back to the .env file
    with open(env_file_path, "w") as f:
        f.writelines(updated_lines)
    
    if api_key_updated:
        print(f"OpenRouter API key has been updated successfully in {env_file_path}")
    else:
        print(f"OpenRouter API key line not found in {env_file_path}")
    
    return api_key_updated

if __name__ == "__main__":
    # Check if the API key is provided
    if len(sys.argv) < 2:
        print("Usage: python update_api_key.py <new_api_key>")
        sys.exit(1)
    
    # Get the new API key from command line argument
    new_api_key = sys.argv[1]
    
    # Update the API key
    update_openrouter_api_key(new_api_key) 