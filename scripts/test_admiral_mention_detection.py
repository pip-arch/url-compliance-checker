#!/usr/bin/env python3
"""
Test script to verify Admiral Markets mention detection in crawlers.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
from app.services.crawlers.firecrawl_service import FirecrawlService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mention_detection():
    """Test Admiral Markets mention detection on sample URLs."""
    
    # Test URLs - one with mentions, one without
    test_urls = [
        "https://www.investopedia.com/articles/forex/11/how-to-choose-a-forex-broker.asp",  # Likely has Admiral Markets mention
        "https://www.example.com",  # Unlikely to have Admiral Markets mention
    ]
    
    # Test with Crawl4AI
    print("\n=== Testing Crawl4AI Service ===")
    crawl4ai_service = Crawl4AIService()
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            result = await crawl4ai_service.extract_content(url)
            
            if result.get("success"):
                if result.get("skip_analysis"):
                    print(f"✓ Page skipped: {result.get('skip_reason')}")
                else:
                    print(f"✓ Found {result.get('admiral_mentions', 0)} Admiral Markets mentions")
                    contexts = result.get('mention_contexts', [])
                    if contexts:
                        print(f"  First mention context: {contexts[0]['context'][:100]}...")
            else:
                print(f"✗ Error: {result.get('error')}")
                
        except Exception as e:
            print(f"✗ Exception: {str(e)}")
    
    # Test with Firecrawl (if API key is set)
    if os.getenv("FIRECRAWL_API_KEY"):
        print("\n\n=== Testing Firecrawl Service ===")
        try:
            firecrawl_service = FirecrawlService()
            
            for url in test_urls:
                print(f"\nTesting URL: {url}")
                try:
                    result = await firecrawl_service.extract_content(url)
                    
                    if result.get("success"):
                        if result.get("skip_analysis"):
                            print(f"✓ Page skipped: {result.get('skip_reason')}")
                        else:
                            print(f"✓ Found {result.get('admiral_mentions', 0)} Admiral Markets mentions")
                            contexts = result.get('mention_contexts', [])
                            if contexts:
                                print(f"  First mention context: {contexts[0]['context'][:100]}...")
                    else:
                        print(f"✗ Error: {result.get('error')}")
                        
                except Exception as e:
                    print(f"✗ Exception: {str(e)}")
                    
        except ValueError as e:
            print("✗ Firecrawl not configured (missing API key)")
    else:
        print("\n\n✗ Skipping Firecrawl test - FIRECRAWL_API_KEY not set")

if __name__ == "__main__":
    asyncio.run(test_mention_detection()) 