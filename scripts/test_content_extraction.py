#!/usr/bin/env python3
"""
Test content extraction and check for Admiral Markets mentions.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawlers.firecrawl_service import FirecrawlService
import re

async def test_content_extraction():
    """Test content extraction and manually check for mentions."""
    
    # Test URL that should mention various forex brokers
    test_url = "https://www.investopedia.com/best-forex-brokers-5084736"
    
    print(f"\n=== Testing content extraction for: {test_url} ===\n")
    
    try:
        service = FirecrawlService()
        result = await service.extract_content(test_url)
        
        if result.get("success"):
            content = result.get("markdown", "")
            
            # Print content length
            print(f"✓ Content extracted successfully")
            print(f"  Content length: {len(content)} characters")
            
            # Check for various broker mentions
            brokers_to_check = [
                "admiral", "admiralmarkets", "admiral markets",
                "oanda", "forex.com", "ig", "cmc markets", 
                "etoro", "plus500", "xm", "pepperstone"
            ]
            
            print(f"\n  Broker mentions found:")
            for broker in brokers_to_check:
                matches = list(re.finditer(broker, content, re.IGNORECASE))
                if matches:
                    print(f"    - {broker}: {len(matches)} mentions")
                    # Show first match context
                    first_match = matches[0]
                    start = max(0, first_match.start() - 50)
                    end = min(len(content), first_match.end() + 50)
                    context = content[start:end].replace('\n', ' ')
                    print(f"      Context: ...{context}...")
            
            # Save content for manual inspection
            output_file = "data/test_content_sample.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {test_url}\n")
                f.write(f"Content length: {len(content)}\n")
                f.write(f"Skip analysis: {result.get('skip_analysis', False)}\n")
                f.write(f"Skip reason: {result.get('skip_reason', 'N/A')}\n")
                f.write("\n--- CONTENT ---\n")
                f.write(content[:5000])  # First 5000 chars
                if len(content) > 5000:
                    f.write("\n\n... (truncated) ...")
            
            print(f"\n✓ Saved content sample to {output_file}")
            
            # Show Admiral patterns being used
            print(f"\n  Admiral patterns checked:")
            for pattern in service.admiral_patterns:
                print(f"    - {pattern}")
                
        else:
            print(f"✗ Error: {result.get('error')}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_content_extraction()) 