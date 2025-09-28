#!/usr/bin/env python3
"""Test Firecrawl API with the new key."""

import os
import requests
from dotenv import load_dotenv

def test_firecrawl():
    """Test Firecrawl API connectivity and functionality."""
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('FIRECRAWL_API_KEY')
    api_url = os.getenv('FIRECRAWL_API_URL', 'https://api.firecrawl.dev/v1/scrape')
    
    print(f"🔥 Testing Firecrawl API")
    print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"   API URL: {api_url}\n")
    
    # Test URL
    test_url = "https://www.example.com"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'url': test_url,
        'formats': ['markdown', 'html'],
        'onlyMainContent': True
    }
    
    try:
        print(f"📡 Testing with URL: {test_url}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                content_length = len(data['data'].get('markdown', ''))
                print(f"   ✅ Success! Retrieved {content_length} characters")
                print(f"   Title: {data['data'].get('metadata', {}).get('title', 'N/A')}")
                
                # Check credit usage
                if 'creditsUsed' in data:
                    print(f"   Credits Used: {data['creditsUsed']}")
            else:
                print(f"   ⚠️  Unexpected response format")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    print("\n💡 Next Steps:")
    if response.status_code == 200:
        print("   ✅ Firecrawl is working! You can now run URL processing.")
    else:
        print("   ❌ Firecrawl is not working. Check the API key or use fallback crawlers.")

if __name__ == "__main__":
    test_firecrawl() 