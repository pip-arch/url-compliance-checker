#!/usr/bin/env python3
"""
Apply speed optimizations to crawler configurations.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Update crawler timeouts
updates = [
    ("app/services/crawlers/firecrawl_service.py", [
        ("timeout = int(os.getenv('FIRECRAWL_TIMEOUT', '30'))", 
         "timeout = int(os.getenv('FIRECRAWL_TIMEOUT', '10'))"),
        ("self.max_retries = 3", 
         "self.max_retries = 1"),
        ("delay = min(60, (2 ** attempt) * 2)", 
         "delay = 1  # Fixed 1 second delay")
    ]),
    ("app/services/crawlers/crawl4ai_service.py", [
        ("page_timeout=20000",
         "page_timeout=10000"),
        ("self.max_retries = 3",
         "self.max_retries = 1"),
        ("delay = min(60, (2 ** attempt) * 2)",
         "delay = 1  # Fixed 1 second delay")
    ]),
    ("app/services/crawler.py", [
        ("self.timeout = aiohttp.ClientTimeout(total=30)",
         "self.timeout = aiohttp.ClientTimeout(total=10)"),
        ("self.max_retries = 3",
         "self.max_retries = 1"),
        ("await asyncio.sleep(attempt)",
         "await asyncio.sleep(1)")
    ])
]

print("⚡ Applying speed optimizations...\n")

for filename, replacements in updates:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read()
        
        original_content = content
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                print(f"✅ {filename}: {old[:30]}... → {new[:30]}...")
        
        if content != original_content:
            with open(filename, 'w') as f:
                f.write(content)
            print(f"   Updated {filename}\n")
    else:
        print(f"❌ File not found: {filename}\n")

print("\n✅ Speed optimizations applied!")
print("\nSettings changed:")
print("- Timeouts: 30s → 10s")
print("- Retries: 3 → 1") 
print("- Retry delay: Exponential → Fixed 1s")
print("\nThis will make processing ~5x faster but may miss some slow sites.") 