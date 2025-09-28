#!/usr/bin/env python3
"""
Test script to verify connection to Firecrawl API.
This diagnostic tool helps identify authentication or connection issues.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/logs/firecrawl_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_firecrawl(url="https://example.com", api_key=None):
    """
    Test connection to Firecrawl API.
    
    Args:
        url: The URL to scrape (default: https://example.com)
        api_key: Firecrawl API key (if None, will use environment variable)
    
    Returns:
        dict: Response from Firecrawl API
    """
    # Import aiohttp here to ensure it's installed
    try:
        import aiohttp
    except ImportError:
        logger.error("aiohttp not installed. Please install with 'pip install aiohttp'")
        return {"error": "aiohttp not installed"}

    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            logger.error("No Firecrawl API key provided. Set FIRECRAWL_API_KEY environment variable or pass via --api-key")
            return {"error": "No API key provided"}
    
    # API URL from environment or default
    api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
    
    # Set up request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "url": url,
        "formats": ["markdown", "html"],
        "timeout": 30000  # 30 seconds in milliseconds
    }
    
    logger.info(f"Testing Firecrawl API connection to {api_url}")
    logger.info(f"Testing with URL: {url}")
    
    # Make request
    try:
        async with aiohttp.ClientSession() as session:
            start_time = datetime.now()
            
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=35  # 35 seconds timeout (slightly longer than request timeout)
            ) as response:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Read response
                response_text = await response.text()
                status_code = response.status
                
                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse response as JSON. Status: {status_code}, Content: {response_text[:200]}...")
                    return {
                        "success": False,
                        "status_code": status_code,
                        "duration": duration,
                        "error": "Invalid JSON response",
                        "response_text": response_text[:500]  # First 500 chars
                    }
                
                # Check if successful
                if status_code == 200 and response_json.get("success", False):
                    logger.info(f"Firecrawl API connection successful! Status: {status_code}, Duration: {duration:.2f}s")
                    
                    # Log some basic info from the response
                    data = response_json.get("data", {})
                    markdown_length = len(data.get("markdown", "")) if data else 0
                    html_length = len(data.get("html", "")) if data else 0
                    
                    logger.info(f"Received markdown ({markdown_length} chars) and HTML ({html_length} chars)")
                    
                    if "metadata" in data:
                        logger.info(f"Page title: {data['metadata'].get('title', 'Unknown')}")
                    
                    return {
                        "success": True,
                        "status_code": status_code,
                        "duration": duration,
                        "data_summary": {
                            "markdown_length": markdown_length,
                            "html_length": html_length,
                            "metadata": data.get("metadata", {}) if data else {}
                        }
                    }
                else:
                    logger.error(f"Firecrawl API request failed. Status: {status_code}, Response: {response_text[:200]}...")
                    return {
                        "success": False,
                        "status_code": status_code,
                        "duration": duration,
                        "error": response_json.get("error", "Unknown error"),
                        "response": response_json
                    }
                
    except aiohttp.ClientError as e:
        logger.error(f"Firecrawl API connection error: {str(e)}")
        return {"success": False, "error": str(e), "error_type": "connection"}
    
    except asyncio.TimeoutError:
        logger.error("Firecrawl API request timed out after 35 seconds")
        return {"success": False, "error": "Request timed out", "error_type": "timeout"}
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": "unexpected"}

async def main():
    """Run the Firecrawl API test script."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test Firecrawl API connection')
    parser.add_argument('--url', default="https://example.com", help='URL to scrape (default: https://example.com)')
    parser.add_argument('--api-key', help='Firecrawl API key (if not provided, will use FIRECRAWL_API_KEY from .env)')
    args = parser.parse_args()
    
    # Make the directory for logs if it doesn't exist
    os.makedirs("data/logs", exist_ok=True)
    
    # Run the test
    result = await test_firecrawl(url=args.url, api_key=args.api_key)
    
    # Print result in a nicely formatted way
    print("\n" + "="*80)
    print("FIRECRAWL API TEST RESULTS")
    print("="*80)
    
    if result.get("success", False):
        print("\n✅ SUCCESS! Connection to Firecrawl API successful.")
        print(f"Status Code: {result.get('status_code')}")
        print(f"Request Duration: {result.get('duration', 0):.2f} seconds")
        
        # Print data summary
        summary = result.get("data_summary", {})
        print(f"\nReceived Data:")
        print(f"  - Markdown: {summary.get('markdown_length', 0)} characters")
        print(f"  - HTML: {summary.get('html_length', 0)} characters")
        
        # Print metadata
        metadata = summary.get("metadata", {})
        if metadata:
            print(f"\nPage Metadata:")
            print(f"  - Title: {metadata.get('title', 'Not found')}")
            print(f"  - Description: {metadata.get('description', 'Not found')}")
            print(f"  - Language: {metadata.get('language', 'Not found')}")
    else:
        print("\n❌ ERROR! Connection to Firecrawl API failed.")
        print(f"Error Type: {result.get('error_type', 'Unknown')}")
        print(f"Error Message: {result.get('error', 'No error message')}")
        
        if "status_code" in result:
            print(f"Status Code: {result.get('status_code')}")
        
        if "response" in result:
            print("\nResponse Details:")
            print(json.dumps(result.get("response"), indent=2)[:500] + "...")
    
    print("\n" + "="*80)
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)

if __name__ == "__main__":
    asyncio.run(main()) 