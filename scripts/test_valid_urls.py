#!/usr/bin/env python3
"""Test with URLs that are known to be accessible."""

import subprocess
import sys
import socket
from urllib.parse import urlparse
from pathlib import Path
import random

def is_url_accessible(url, timeout=2):
    """Quick check if a URL's domain is accessible."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        # Quick socket test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
    except:
        return False

def get_valid_test_urls():
    """Get a mix of valid test URLs from the dataset."""
    
    print("Finding valid, accessible URLs...")
    
    valid_urls = []
    checked_domains = set()
    
    # Read all URLs
    with open("data/test_files/all_admiral_urls.csv", "r") as f:
        header = f.readline()
        all_urls = [line.strip() for line in f if line.strip()]
    
    # Shuffle to get variety
    random.shuffle(all_urls)
    
    # Check URLs until we have 10 valid ones
    for url in all_urls:
        if len(valid_urls) >= 10:
            break
            
        # Skip if we already checked this domain
        domain = urlparse(url).netloc
        if domain in checked_domains:
            continue
        
        checked_domains.add(domain)
        
        # Skip problematic patterns
        if any(pattern in url for pattern in ['104.196.161.100', '0874.info', '10minutetrainerfree.com']):
            continue
        
        # Skip IP addresses
        if any(c.isdigit() and '.' in domain for c in domain.split('.')[0]):
            continue
        
        print(f"  Checking {domain}...", end='', flush=True)
        
        if is_url_accessible(url):
            print(" ✅ Accessible")
            valid_urls.append(url)
        else:
            print(" ❌ Not accessible")
    
    return header, valid_urls

def test_valid_urls():
    """Test with validated URLs."""
    
    header, valid_urls = get_valid_test_urls()
    
    if not valid_urls:
        print("❌ No valid URLs found!")
        return False
    
    # Write test file
    test_file = "data/test_files/test_valid_urls.csv"
    with open(test_file, "w") as f:
        f.write(header)
        for url in valid_urls:
            f.write(url + "\n")
    
    print(f"\n✅ Created {test_file} with {len(valid_urls)} valid URLs:")
    for i, url in enumerate(valid_urls, 1):
        print(f"  {i}. {url}")
    
    # Run the processing
    print("\n🚀 Starting URL processing...")
    cmd = [
        sys.executable,
        "scripts/run_improved_process.py",
        "--file", test_file,
        "--column", "url",
        "--limit", str(len(valid_urls))
    ]
    
    # Set environment
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    # Run with real-time output
    process = subprocess.Popen(
        cmd, 
        env=env, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Stream output
    for line in iter(process.stdout.readline, ''):
        if line:
            print(line.rstrip())
    
    process.wait()
    
    return process.returncode == 0

if __name__ == "__main__":
    success = test_valid_urls()
    sys.exit(0 if success else 1)