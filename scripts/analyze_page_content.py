#!/usr/bin/env python3
"""
Analyze what content is being extracted from pages.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
import re

async def analyze_content():
    """Analyze extracted content to understand what we're getting."""
    
    test_url = "https://www.forexpeacearmy.com/forex-reviews/1825/admirals-forex-broker"
    
    print(f"\n=== Content Analysis ===")
    print(f"URL: {test_url}\n")
    
    service = Crawl4AIService()
    result = await service.scrape_url(test_url)
    
    if result.get("success"):
        content = result.get("data", {}).get("markdown", "")
        
        print(f"✅ Successfully crawled")
        print(f"   Total content length: {len(content)} chars")
        
        # Analyze content structure
        lines = content.split('\n')
        print(f"   Total lines: {len(lines)}")
        
        # Count different elements
        link_count = content.count('](')
        header_count = len([l for l in lines if l.strip().startswith('#')])
        list_count = len([l for l in lines if l.strip().startswith('*') or l.strip().startswith('-')])
        
        print(f"\n📊 Content structure:")
        print(f"   Links: {link_count}")
        print(f"   Headers: {header_count}")
        print(f"   List items: {list_count}")
        
        # Look for specific keywords that should be in a review
        keywords = ['review', 'rating', 'broker', 'trading', 'forex', 'spread', 'platform']
        print(f"\n🔍 Keyword occurrences:")
        for keyword in keywords:
            count = content.lower().count(keyword)
            if count > 0:
                print(f"   '{keyword}': {count} times")
        
        # Check if it's mostly navigation
        nav_indicators = ['Home', 'Menu', 'Login', 'Sign up', 'Blog', 'About']
        nav_count = sum(content.count(indicator) for indicator in nav_indicators)
        print(f"\n🧭 Navigation elements: {nav_count}")
        
        # Find unique words to understand content
        words = re.findall(r'\b\w+\b', content.lower())
        unique_words = set(words)
        print(f"\n📝 Unique words: {len(unique_words)}")
        
        # Save full content for manual inspection
        with open("data/full_content_analysis.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {test_url}\n")
            f.write(f"Content length: {len(content)}\n")
            f.write(f"Lines: {len(lines)}\n")
            f.write("\n--- FULL CONTENT ---\n")
            f.write(content)
        
        print(f"\n💾 Full content saved to data/full_content_analysis.txt")
        
        # Show a middle section of content (avoiding navigation)
        if len(lines) > 50:
            middle_start = len(lines) // 3
            print(f"\n📄 Middle section of content (lines {middle_start}-{middle_start+10}):")
            for i in range(middle_start, min(middle_start + 10, len(lines))):
                if lines[i].strip():
                    print(f"   {lines[i][:80]}...")
    else:
        print(f"❌ Failed to crawl: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(analyze_content()) 