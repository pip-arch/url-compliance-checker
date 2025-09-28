#!/usr/bin/env python3
"""
Test URL checker with actual Admiral Markets referring pages.
These URLs are much more likely to mention Admiral Markets.
"""

import asyncio
import sys
import os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.crawl4ai_service import Crawl4AIService
import random

async def test_admiral_referrers():
    """Test with URLs that actually link to Admiral Markets."""
    
    print("\n=== Testing Admiral Markets Referrers ===\n")
    
    # Read referring URLs
    with open("data/inputs/admiral_markets/referring_urls.txt", "r") as f:
        all_urls = [line.strip() for line in f if line.strip()]
    
    print(f"📊 Total referring URLs: {len(all_urls)}")
    
    # Sample a diverse set of URLs
    test_urls = random.sample(all_urls, min(20, len(all_urls)))
    
    print(f"\n🔍 Testing {len(test_urls)} sample URLs...\n")
    
    service = Crawl4AIService()
    service.timeout = 15  # Reduce timeout for faster testing
    
    results = []
    urls_with_mentions = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing: {url}")
        
        try:
            result = await service.extract_content(url)
            
            if result.get("success"):
                content_length = len(result.get("markdown", ""))
                admiral_mentions = result.get("admiral_mentions", 0)
                skip_analysis = result.get("skip_analysis", False)
                
                results.append({
                    'url': url,
                    'success': True,
                    'content_length': content_length,
                    'admiral_mentions': admiral_mentions,
                    'skip_analysis': skip_analysis,
                    'skip_reason': result.get('skip_reason', '')
                })
                
                if admiral_mentions > 0:
                    print(f"   ✅ SUCCESS! Found {admiral_mentions} Admiral mentions")
                    urls_with_mentions.append(url)
                    
                    # Show first context
                    contexts = result.get('mention_contexts', [])
                    if contexts:
                        print(f"   📝 First mention: '{contexts[0]['mention_text']}'")
                elif skip_analysis:
                    print(f"   ⏭️  Skipped: {result.get('skip_reason')}")
                else:
                    print(f"   ✅ Crawled successfully ({content_length} chars)")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown')[:50]}...")
                results.append({
                    'url': url,
                    'success': False,
                    'error': result.get('error', 'Unknown')[:100]
                })
        
        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:50]}...")
            results.append({
                'url': url,
                'success': False,
                'error': str(e)[:100]
            })
        
        # Small delay to be respectful
        await asyncio.sleep(0.5)
    
    # Summary
    successful_crawls = [r for r in results if r.get('success')]
    failed_crawls = [r for r in results if not r.get('success')]
    
    print(f"\n\n📊 SUMMARY:")
    print(f"   Total tested: {len(test_urls)}")
    print(f"   Successful crawls: {len(successful_crawls)}")
    print(f"   Failed crawls: {len(failed_crawls)}")
    print(f"   URLs with Admiral mentions: {len(urls_with_mentions)} 🎯")
    
    if urls_with_mentions:
        print(f"\n✅ URLs that mention Admiral Markets:")
        for url in urls_with_mentions[:10]:  # Show first 10
            print(f"   - {url}")
        
        # Save for further testing
        pd.DataFrame({'url': urls_with_mentions}).to_csv(
            "data/test_urls_with_admiral_mentions.csv", 
            index=False
        )
        print(f"\n💾 Saved {len(urls_with_mentions)} URLs with mentions to data/test_urls_with_admiral_mentions.csv")
        print("\n🚀 READY FOR FULL PIPELINE TESTING!")
    else:
        print("\n⚠️  No URLs with Admiral mentions found in this sample")
        print("   Try running again or increasing sample size")
    
    # Save all results
    df_results = pd.DataFrame(results)
    df_results.to_csv("data/admiral_referrer_test_results.csv", index=False)
    print(f"\n📊 Full results saved to data/admiral_referrer_test_results.csv")

if __name__ == "__main__":
    asyncio.run(test_admiral_referrers()) 