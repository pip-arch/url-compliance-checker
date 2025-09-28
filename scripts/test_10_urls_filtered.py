#!/usr/bin/env python3
"""Test the system with 10 URLs, filtering out problematic ones."""

import subprocess
import sys
import re
from urllib.parse import urlparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fixes.handle_problematic_urls import is_valid_url, should_skip_url

def test_10_urls_filtered():
    """Extract 10 valid URLs and test the system."""
    
    # First, extract URLs and filter them
    print("Extracting and filtering test URLs...")
    
    valid_urls = []
    with open("data/test_files/all_admiral_urls.csv", "r") as f:
        header = f.readline()
        
        for line in f:
            url = line.strip()
            if url:
                # Check if URL is valid
                valid, reason = is_valid_url(url)
                skip = should_skip_url(url)
                
                if valid and not skip:
                    valid_urls.append(url)
                    if len(valid_urls) >= 10:
                        break
    
    if len(valid_urls) < 10:
        print(f"Warning: Only found {len(valid_urls)} valid URLs")
    
    # Write filtered URLs
    with open("data/test_files/test_10_urls_filtered.csv", "w") as f:
        f.write(header)
        for url in valid_urls:
            f.write(url + "\n")
    
    print(f"Created test_10_urls_filtered.csv with {len(valid_urls)} valid URLs")
    
    # Show the URLs we're testing
    print("\nURLs to test:")
    for i, url in enumerate(valid_urls, 1):
        print(f"  {i}. {url}")
    
    # Now run the processing
    print("\nRunning URL processing...")
    cmd = [
        sys.executable,
        "scripts/run_improved_process.py",
        "--file", "data/test_files/test_10_urls_filtered.csv",
        "--column", "url",
        "--limit", str(len(valid_urls))
    ]
    
    # Set PYTHONPATH
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    # Run the command
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    print("\nSTDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    return result.returncode == 0

if __name__ == "__main__":
    success = test_10_urls_filtered()
    sys.exit(0 if success else 1)