#!/usr/bin/env python3
"""
Fix crawler settings to properly extract content from dynamic pages.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from app.services.crawlers.crawl4ai_service import Crawl4AIService
import logging

logging.basicConfig(level=logging.INFO)

async def test_improved_crawling():
    """Test with improved crawler settings."""
    
    test_url = "https://www.forexpeacearmy.com/forex-reviews/1825/admirals-forex-broker"
    
    print(f"\n=== Testing Improved Crawler Settings ===")
    print(f"URL: {test_url}\n")
    
    # Configure browser for better content extraction
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        java_script_enabled=True,
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    # Configure crawler to wait for content
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30000,  # 30 seconds
        wait_until="domcontentloaded",  # Don't wait for all network activity
        excluded_tags=["script", "style", "noscript", "meta", "link"],
        exclude_external_links=True
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=crawler_config)
            
            if result.success:
                print(f"✅ Successfully crawled")
                print(f"   HTML length: {len(result.cleaned_html)} chars")
                print(f"   Markdown length: {len(result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else result.markdown)} chars")
                
                # Check the content
                content = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else result.markdown
                
                # Look for "Admiral" in any form
                admiral_count = content.lower().count("admiral")
                print(f"\n📊 'Admiral' appears {admiral_count} times in the content")
                
                # Save for inspection
                with open("data/improved_crawl_test.txt", "w", encoding="utf-8") as f:
                    f.write(f"URL: {test_url}\n")
                    f.write(f"Admiral count: {admiral_count}\n\n")
                    f.write("--- FIRST 3000 CHARS ---\n")
                    f.write(content[:3000])
                    
                print(f"\n💾 Saved to data/improved_crawl_test.txt")
                
                # Show a sample where "admiral" appears
                admiral_pos = content.lower().find("admiral")
                if admiral_pos > -1:
                    start = max(0, admiral_pos - 100)
                    end = min(len(content), admiral_pos + 100)
                    print(f"\n📝 Sample around first 'admiral' mention:")
                    print(f"   ...{content[start:end]}...")
                
            else:
                print(f"❌ Failed: {result.error_message}")
                
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_improved_crawling()) 