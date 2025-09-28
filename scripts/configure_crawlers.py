#!/usr/bin/env python3
"""Configure crawler settings for optimal performance without Firecrawl."""

import os
from pathlib import Path

def configure_crawlers(disable_firecrawl=True):
    """Configure crawler settings in .env file."""
    
    env_path = Path(".env")
    
    # Read current .env
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Settings to update
    settings = {
        'USE_FIRECRAWL': 'false' if disable_firecrawl else 'true',
        'CRAWLER_TIMEOUT': '15',  # Reduced timeout for faster fallback
        'CRAWLER_MAX_RETRIES': '2',  # Fewer retries for faster processing
        'CRAWL4AI_TIMEOUT': '20',  # Reasonable timeout for Crawl4AI
        'CUSTOM_CRAWLER_TIMEOUT': '10',  # Fast timeout for custom crawler
        'CRAWLER_PRIORITY': 'crawl4ai,custom',  # Priority order
    }
    
    # Update or add settings
    updated_lines = []
    settings_found = set()
    
    for line in lines:
        key = line.split('=')[0].strip()
        if key in settings:
            updated_lines.append(f"{key}={settings[key]}\n")
            settings_found.add(key)
        else:
            updated_lines.append(line)
    
    # Add missing settings
    for key, value in settings.items():
        if key not in settings_found:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ Crawler Configuration Updated:")
    print(f"  - Firecrawl: {'Disabled' if disable_firecrawl else 'Enabled'}")
    print(f"  - Primary crawler: Crawl4AI")
    print(f"  - Fallback: Custom crawler")
    print(f"  - Timeouts optimized for speed")
    print("\n💡 You can now run URL processing without Firecrawl!")

if __name__ == "__main__":
    configure_crawlers(disable_firecrawl=True) 