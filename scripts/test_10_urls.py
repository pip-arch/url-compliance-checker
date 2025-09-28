#!/usr/bin/env python3
"""Test the system with just 10 URLs to verify everything is working."""

import subprocess
import sys

def test_10_urls():
    """Extract 10 URLs and test the system."""
    
    # First, extract 10 random URLs
    print("Extracting 10 test URLs...")
    with open("data/test_files/all_admiral_urls.csv", "r") as f:
        lines = f.readlines()
    
    # Write header and 10 URLs
    with open("data/test_files/test_10_urls.csv", "w") as f:
        f.write(lines[0])  # Header
        for line in lines[1:11]:  # Next 10 lines
            f.write(line)
    
    print("Created test_10_urls.csv with 10 URLs")
    
    # Now run the processing
    print("\nRunning URL processing...")
    cmd = [
        sys.executable,
        "scripts/run_improved_process.py",
        "--file", "data/test_files/test_10_urls.csv",
        "--column", "url",
        "--limit", "10"
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
    success = test_10_urls()
    sys.exit(0 if success else 1) 