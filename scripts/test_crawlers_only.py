#!/usr/bin/env python3
"""Test crawler functionality without Firecrawl to find the best fallback options."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.crawler import crawler_service
from app.models.url import URLContent
import time

async def test_crawlers():
    """Test different crawler configurations."""
    
    # Test URLs with different characteristics
    test_urls = [
        "https://www.example.com",  # Simple site
        "https://www.wikipedia.org",  # Well-known site
        "https://httpbin.org/html",  # Test site
        "https://www.google.com",  # JavaScript-heavy
        "https://www.bbc.com/news",  # News site
    ]
    
    print("🧪 Testing Crawler Performance Without Firecrawl\n")
    print("=" * 60)
    
    # Temporarily disable Firecrawl
    original_api_key = crawler_service.firecrawl_api_key
    crawler_service.firecrawl_api_key = None
    
    results = {
        'crawl4ai': {'success': 0, 'failed': 0, 'times': []},
        'custom': {'success': 0, 'failed': 0, 'times': []},
    }
    
    for url in test_urls:
        print(f"\n📍 Testing: {url}")
        
        # Test Crawl4AI
        print("  → Testing Crawl4AI...")
        start_time = time.time()
        try:
            # Force Crawl4AI
            crawler_service.use_crawl4ai = True
            content = await crawler_service.crawl_url(url)
            elapsed = time.time() - start_time
            
            if content and content.full_text:
                results['crawl4ai']['success'] += 1
                results['crawl4ai']['times'].append(elapsed)
                print(f"    ✅ Success ({elapsed:.2f}s) - {len(content.full_text)} chars")
            else:
                results['crawl4ai']['failed'] += 1
                print(f"    ❌ Failed - No content")
        except Exception as e:
            results['crawl4ai']['failed'] += 1
            print(f"    ❌ Failed - {str(e)[:50]}...")
        
        # Test Custom Crawler
        print("  → Testing Custom Crawler...")
        start_time = time.time()
        try:
            # Force custom crawler
            crawler_service.use_crawl4ai = False
            content = await crawler_service._crawl_with_custom(url)
            elapsed = time.time() - start_time
            
            if content and content.full_text:
                results['custom']['success'] += 1
                results['custom']['times'].append(elapsed)
                print(f"    ✅ Success ({elapsed:.2f}s) - {len(content.full_text)} chars")
            else:
                results['custom']['failed'] += 1
                print(f"    ❌ Failed - No content")
        except Exception as e:
            results['custom']['failed'] += 1
            print(f"    ❌ Failed - {str(e)[:50]}...")
    
    # Restore original settings
    crawler_service.firecrawl_api_key = original_api_key
    crawler_service.use_crawl4ai = True
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 CRAWLER PERFORMANCE SUMMARY\n")
    
    for crawler, stats in results.items():
        total = stats['success'] + stats['failed']
        success_rate = (stats['success'] / total * 100) if total > 0 else 0
        avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
        
        print(f"{crawler.upper()}:")
        print(f"  Success Rate: {success_rate:.1f}% ({stats['success']}/{total})")
        print(f"  Average Time: {avg_time:.2f}s")
        print()
    
    # Recommendation
    if results['crawl4ai']['success'] > results['custom']['success']:
        print("💡 Recommendation: Use Crawl4AI as primary fallback")
    else:
        print("💡 Recommendation: Use Custom Crawler as primary fallback")

if __name__ == "__main__":
    asyncio.run(test_crawlers()) 