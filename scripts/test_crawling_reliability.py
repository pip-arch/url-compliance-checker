#!/usr/bin/env python3
"""
Test crawling reliability and find URLs that actually work.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
from app.services.crawlers.firecrawl_service import FirecrawlService
import pandas as pd
import logging

logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def test_crawling_reliability():
    """Test various URLs to find ones that work reliably."""
    
    # Mix of different types of URLs to test
    test_urls = [
        # News/Media sites (usually more accessible)
        "https://www.reuters.com/markets/currencies/",
        "https://www.bloomberg.com/markets/currencies",
        "https://finance.yahoo.com/currencies/",
        
        # Forums/Communities (often accessible)
        "https://www.reddit.com/r/Forex/",
        "https://www.forexfactory.com/",
        
        # Educational sites
        "https://www.babypips.com/learn/forex",
        "https://www.investopedia.com/terms/f/forex.asp",
        
        # Broker review sites (may have Admiral Markets mentions)
        "https://www.trustpilot.com/review/www.admiralmarkets.com",
        "https://www.forexpeacearmy.com/forex-reviews/1825/admirals-forex-broker",
        
        # Wikipedia (reliable)
        "https://en.wikipedia.org/wiki/Foreign_exchange_market",
    ]
    
    print("=== Testing Crawling Reliability ===\n")
    
    # Test with Crawl4AI (since Firecrawl is timing out)
    service = Crawl4AIService()
    # Adjust timeout
    service.timeout = 10  # Reduce to 10 seconds
    
    results = []
    working_urls = []
    
    for url in test_urls:
        print(f"Testing: {url}")
        try:
            result = await service.scrape_url(url)
            
            if result.get("success"):
                content_length = len(result.get("data", {}).get("markdown", ""))
                print(f"  ✅ Success - {content_length} chars")
                
                # Check if content is meaningful
                if content_length > 1000:
                    working_urls.append({
                        'url': url,
                        'content_length': content_length,
                        'duration': result.get('duration', 0)
                    })
                else:
                    print(f"  ⚠️  Content too short")
            else:
                error = result.get("error", "Unknown")
                print(f"  ❌ Failed: {error[:50]}...")
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)[:50]}...")
        
        # Small delay to be respectful
        await asyncio.sleep(1)
    
    # Save working URLs
    if working_urls:
        df = pd.DataFrame(working_urls)
        output_file = "data/test_working_urls.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✅ Found {len(working_urls)} working URLs")
        print(f"✅ Saved to {output_file}")
        
        print("\nWorking URLs summary:")
        for item in working_urls:
            print(f"  - {item['url']} ({item['content_length']} chars, {item['duration']:.1f}s)")
    else:
        print("\n❌ No working URLs found!")
    
    # Test with shorter timeout and simpler pages
    print("\n\n=== Testing Simple Pages ===")
    simple_urls = [
        "https://httpbin.org/html",  # Test page
        "https://example.com",  # Simple page
        "https://www.google.com/search?q=admiral+markets+review",  # Google search
    ]
    
    for url in simple_urls:
        print(f"\nTesting: {url}")
        try:
            result = await service.scrape_url(url)
            if result.get("success"):
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed")
        except Exception as e:
            print(f"  ❌ Exception: {str(e)[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_crawling_reliability()) 