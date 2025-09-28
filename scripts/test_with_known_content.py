#!/usr/bin/env python3
"""
Test with a page that we know mentions Admiral Markets.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
from app.services.crawlers.firecrawl_service import FirecrawlService
import logging

logging.basicConfig(level=logging.INFO)

async def test_with_known_content():
    """Test with pages more likely to have Admiral Markets content."""
    
    # URLs that are more likely to mention Admiral Markets
    test_urls = [
        # Try TrustPilot reviews
        "https://www.trustpilot.com/review/www.admiralmarkets.com",
        # Try a forex comparison site that's more reliable
        "https://www.forexbrokers.com/reviews/admiral-markets",
        # Try broker directory pages
        "https://brokers.forex/broker/admiral-markets",
    ]
    
    print("\n=== Testing URLs likely to mention Admiral Markets ===\n")
    
    # Test with both crawlers
    crawlers = {
        "Crawl4AI": Crawl4AIService(),
    }
    
    # Add Firecrawl if API key is set
    if os.getenv("FIRECRAWL_API_KEY"):
        try:
            crawlers["Firecrawl"] = FirecrawlService()
        except:
            print("Firecrawl not available")
    
    for crawler_name, service in crawlers.items():
        print(f"\n--- Testing with {crawler_name} ---")
        
        for url in test_urls:
            print(f"\nTesting: {url}")
            try:
                result = await service.extract_content(url)
                
                if result.get("success"):
                    content_length = len(result.get("markdown", ""))
                    print(f"✓ Success - Content length: {content_length} chars")
                    
                    if result.get("skip_analysis"):
                        print(f"  ⚠️  Skipped: {result.get('skip_reason')}")
                    else:
                        print(f"  ✅ Found {result.get('admiral_mentions', 0)} Admiral Markets mentions!")
                        contexts = result.get('mention_contexts', [])
                        if contexts:
                            print(f"  📝 First mention context:")
                            context = contexts[0]['context'][:200].replace('\n', ' ')
                            print(f"     {context}...")
                else:
                    print(f"✗ Failed: {result.get('error', 'Unknown error')}")
                    
                # Don't overwhelm servers
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"✗ Exception: {str(e)}")
    
    # Also test with a synthetic example
    print("\n\n--- Testing with synthetic content ---")
    synthetic_content = """
    # Best Forex Brokers 2024
    
    When choosing a forex broker, it's important to consider several factors.
    
    ## Top Brokers
    
    1. **IG** - Great for beginners
    2. **OANDA** - Excellent platform
    3. **Admiral Markets** - Good for European traders, Admiral Markets offers competitive spreads
    4. **Forex.com** - Reliable US broker
    
    Admiral Markets (now known as Admirals) is a well-established broker that has been
    serving traders since 2001. The broker offers access to forex, CFDs, and other instruments.
    
    Many traders choose Admiral Markets for their MT4/MT5 platform support and educational resources.
    """
    
    # Test pattern matching directly
    from app.services.crawlers.firecrawl_service import FirecrawlService
    service = FirecrawlService()
    mentions = service._find_admiral_mentions(synthetic_content)
    
    print(f"Found {len(mentions)} mentions in synthetic content")
    for start, end, text in mentions:
        print(f"  - '{text}' at position {start}")
        context = service._extract_context_around_mention(synthetic_content, start, end, words_before=10, words_after=10)
        print(f"    Context: {context['context'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_with_known_content()) 