#!/usr/bin/env python3
"""
Test LLM analysis by forcing it to run regardless of Admiral mentions.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.compliance_checker import ComplianceChecker
from app.models.url import URLContent, URLContentMatch
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

async def test_llm_analysis():
    """Test LLM analysis with sample content."""
    
    print("\n🧪 TESTING LLM COMPLIANCE ANALYSIS\n")
    
    # Initialize compliance checker
    checker = ComplianceChecker()
    
    # Create test cases
    test_cases = [
        {
            'url': 'https://example-forex-site.com/admiral-markets-review',
            'content': """
            Admiral Markets Review - Is it a Scam?
            
            Many traders ask if Admiral Markets is legitimate. This broker offers forex trading
            services and claims to be regulated. However, our investigation found several red flags:
            
            1. They promise guaranteed returns of 50% per month
            2. No proper regulation verification available
            3. Multiple customer complaints about withdrawal issues
            4. Using Admiral Markets brand without authorization
            
            We recommend avoiding this broker. Admiral Markets official site is admiralmarkets.com,
            not this suspicious clone site.
            """
        },
        {
            'url': 'https://legitimate-news.com/admiral-markets-earnings',
            'content': """
            Admiral Markets Reports Q3 Earnings
            
            Admiral Markets, the well-known forex broker, today announced their Q3 results.
            The company showed strong growth in trading volumes and new client acquisitions.
            
            CEO stated: "We continue to focus on providing excellent trading conditions
            and educational resources for our clients."
            
            Admiral Markets is regulated by FCA and offers trading in forex, indices, and commodities.
            Visit their official website at admiralmarkets.com for more information.
            """
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing URL: {test['url']}")
        print(f"{'='*60}")
        
        # Create URLContent object
        url_content = URLContent(
            url=test['url'],
            html_content=test['content'],
            full_text=test['content'],
            crawled_at=datetime.utcnow()
        )
        
        # Add a mention manually to ensure analysis runs
        mention = URLContentMatch(
            text="Admiral Markets",
            context_before=test['content'][:50],
            context_after=test['content'][-50:],
            position=test['content'].find("Admiral Markets")
        )
        url_content.mentions = [mention]
        
        # Force the analysis
        print("\n🤖 Running LLM Compliance Analysis...")
        result = await checker.check_url_compliance(url_content)
        
        print(f"\n📊 ANALYSIS RESULT:")
        print(f"   Category: {result.category.value}")
        print(f"   Analysis Method: {result.analysis_method}")
        
        if result.ai_analysis:
            print(f"   AI Confidence: {result.ai_analysis.confidence}")
            print(f"   AI Explanation: {result.ai_analysis.explanation}")
            print(f"   Compliance Issues: {result.ai_analysis.compliance_issues}")
        
        if result.rule_matches:
            print(f"\n📋 Matched Rules:")
            for rule in result.rule_matches:
                print(f"   - {rule.rule_name}: {rule.match_text}")

if __name__ == "__main__":
    asyncio.run(test_llm_analysis()) 