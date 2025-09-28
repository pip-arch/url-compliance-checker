#!/usr/bin/env python3
"""
Test Admiral Markets mention detection with a URL that we know works and mentions Admiral Markets.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
from app.services.crawlers.firecrawl_service import FirecrawlService
import logging

logging.basicConfig(level=logging.INFO)

async def test_admiral_detection():
    """Test with a URL that definitely mentions Admiral Markets."""
    
    # URL that works and is about Admiral Markets
    test_url = "https://www.forexpeacearmy.com/forex-reviews/1825/admirals-forex-broker"
    
    print(f"\n=== Testing Admiral Markets Mention Detection ===")
    print(f"URL: {test_url}\n")
    
    # Test with Crawl4AI (since it's working)
    service = Crawl4AIService()
    
    try:
        result = await service.extract_content(test_url)
        
        if result.get("success"):
            print(f"✅ Successfully crawled the page")
            print(f"   Content length: {len(result.get('markdown', ''))} chars")
            
            if result.get("skip_analysis"):
                print(f"\n⚠️  SKIPPED: {result.get('skip_reason')}")
                print("   This should NOT happen for this URL!")
            else:
                mentions = result.get('admiral_mentions', 0)
                print(f"\n✅ Found {mentions} Admiral Markets mentions!")
                
                contexts = result.get('mention_contexts', [])
                if contexts:
                    print(f"\n📝 Mention contexts found:")
                    for i, context in enumerate(contexts[:5], 1):  # Show first 5
                        print(f"\n   Mention #{i}:")
                        print(f"   Text: '{context['mention_text']}'")
                        print(f"   Position: {context['position_in_text']['percentage']:.1f}% into the document")
                        print(f"   Context preview:")
                        preview = context['context'][:200].replace('\n', ' ')
                        print(f"   ...{preview}...")
            
            # Save full content for inspection
            output_file = "data/admiral_markets_content_sample.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {test_url}\n")
                f.write(f"Admiral mentions: {result.get('admiral_mentions', 0)}\n")
                f.write(f"Skip analysis: {result.get('skip_analysis', False)}\n")
                f.write("\n--- CONTENT SAMPLE (first 2000 chars) ---\n")
                f.write(result.get('markdown', '')[:2000])
            print(f"\n💾 Saved content sample to {output_file}")
            
        else:
            print(f"❌ Failed to crawl: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Also test pattern matching directly on known content
    print("\n\n=== Testing Pattern Matching Directly ===")
    test_content = """
    Admirals (formerly Admiral Markets) is a forex broker.
    Many traders use Admiral Markets for trading.
    The company Admiral-Markets has been around for years.
    Visit admiralmarkets.com for more info.
    """
    
    service = Crawl4AIService()
    mentions = service._find_admiral_mentions(test_content)
    
    print(f"Test content has {len(mentions)} mentions:")
    for start, end, text in mentions:
        print(f"  - Found '{text}' at position {start}-{end}")

if __name__ == "__main__":
    asyncio.run(test_admiral_detection()) 