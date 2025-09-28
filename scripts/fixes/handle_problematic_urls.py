#!/usr/bin/env python3
"""Handle problematic URLs that fail with crawlers."""

import re
from urllib.parse import urlparse
import socket

def is_valid_url(url):
    """Check if URL is valid and accessible."""
    try:
        parsed = urlparse(url)
        
        # Check for IP-based URLs
        if re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc):
            # Try to resolve IP
            try:
                socket.gethostbyname(parsed.netloc)
            except:
                return False, "IP address not reachable"
        
        # Check for invalid TLDs
        if '.' not in parsed.netloc:
            return False, "No valid TLD"
        
        # Check for dead domains
        problematic_domains = [
            '0874.info',
            '044bdeanjeffery.balticwebdev1.co.uk',
            '104.196.161.100'
        ]
        
        for domain in problematic_domains:
            if domain in parsed.netloc:
                return False, f"Known problematic domain: {domain}"
        
        return True, "Valid URL"
        
    except Exception as e:
        return False, str(e)

def should_skip_url(url):
    """Determine if URL should be skipped entirely."""
    skip_patterns = [
        r'^\d+\.\d+\.\d+\.\d+',  # IP addresses
        r'\.local$',  # Local domains
        r'\.test$',   # Test domains
        r'\.invalid$', # Invalid domains
    ]
    
    parsed = urlparse(url)
    for pattern in skip_patterns:
        if re.search(pattern, parsed.netloc):
            return True
    
    return False

if __name__ == "__main__":
    # Test problematic URLs
    test_urls = [
        "http://0874.info/2020/05/page/80/",
        "http://044bdeanjeffery.balticwebdev1.co.uk/2020/02/page/4/",
        "http://104.196.161.100/2019/03/top-10-forex-trading-tips-for-beginners/",
        "https://www.example.com",
        "https://admiralmarkets.com"
    ]
    
    print("Testing URL validation:\n")
    for url in test_urls:
        valid, reason = is_valid_url(url)
        skip = should_skip_url(url)
        print(f"URL: {url}")
        print(f"  Valid: {valid} - {reason}")
        print(f"  Should Skip: {skip}")
        print()