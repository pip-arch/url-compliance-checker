#!/usr/bin/env python3
"""
Test script for verifying the Firecrawl integration works end-to-end.
This script uses the actual URLProcessor to process a test URL and validates the results.
"""

import os
import sys
import asyncio
import logging
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import URL processor
from app.core.url_processor import URLProcessor
from app.services.crawlers.firecrawl_service import FirecrawlService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/logs/firecrawl_integration_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_firecrawl_service_direct(url):
    """Test the FirecrawlService directly"""
    logger.info(f"Testing FirecrawlService directly with URL: {url}")
    
    # Create the service
    firecrawl = FirecrawlService()
    
    # Test scrape_url method
    logger.info("Testing scrape_url method...")
    start_time = datetime.now()
    scrape_result = await firecrawl.scrape_url(url)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"scrape_url completed in {duration:.2f} seconds")
    success = scrape_result.get("success", False)
    logger.info(f"Success: {success}")
    
    if success:
        data = scrape_result.get("data", {})
        markdown_length = len(data.get("markdown", "")) if data else 0
        html_length = len(data.get("html", "")) if data else 0
        logger.info(f"Received markdown ({markdown_length} chars) and HTML ({html_length} chars)")
    else:
        logger.error(f"Error: {scrape_result.get('error', 'Unknown error')}")
    
    # Test extract_content method
    logger.info("Testing extract_content method...")
    start_time = datetime.now()
    extract_result = await firecrawl.extract_content(url)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"extract_content completed in {duration:.2f} seconds")
    success = extract_result.get("success", False)
    logger.info(f"Success: {success}")
    
    if success:
        markdown_length = len(extract_result.get("markdown", ""))
        html_length = len(extract_result.get("html", ""))
        logger.info(f"Received markdown ({markdown_length} chars) and HTML ({html_length} chars)")
    else:
        logger.error(f"Error: {extract_result.get('error', 'Unknown error')}")
    
    return {
        "scrape_result": scrape_result,
        "extract_result": extract_result
    }

async def test_url_processor(url):
    """Test the URL processor's crawl method"""
    logger.info(f"Testing URLProcessor with URL: {url}")
    
    # Create processor
    processor = URLProcessor()
    
    # Create a test batch ID
    batch_id = f"test_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Process the single URL
    logger.info(f"Processing URL with batch ID: {batch_id}")
    result = await processor.process_urls([url], batch_id)
    
    logger.info(f"Batch processing result: {json.dumps(result, indent=2)}")
    
    return result

async def main():
    """Run the tests"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Test Firecrawl integration')
    parser.add_argument('--url', default='https://example.com', help='URL to test with')
    parser.add_argument('--direct-only', action='store_true', help='Only test the FirecrawlService directly')
    parser.add_argument('--processor-only', action='store_true', help='Only test the URLProcessor')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Make log directory
    os.makedirs("data/logs", exist_ok=True)
    
    # Check for API key
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY not set in .env file.")
        print("\n⚠️ ERROR: FIRECRAWL_API_KEY not set in .env file! ⚠️")
        print("Please set this environment variable to your Firecrawl API key.")
        return 1
    
    # Print header
    print("\n" + "="*80)
    print("FIRECRAWL INTEGRATION TEST")
    print("="*80 + "\n")
    
    print(f"Testing with URL: {args.url}")
    
    # Run direct test unless processor-only specified
    direct_results = None
    if not args.processor_only:
        print("\nTesting FirecrawlService directly...")
        try:
            direct_results = await test_firecrawl_service_direct(args.url)
            
            if direct_results["scrape_result"].get("success", False):
                print("✅ FirecrawlService.scrape_url: SUCCESS")
            else:
                print("❌ FirecrawlService.scrape_url: FAILED")
                print(f"Error: {direct_results['scrape_result'].get('error', 'Unknown error')}")
            
            if direct_results["extract_result"].get("success", False):
                print("✅ FirecrawlService.extract_content: SUCCESS")
            else:
                print("❌ FirecrawlService.extract_content: FAILED")
                print(f"Error: {direct_results['extract_result'].get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ FirecrawlService test error: {str(e)}")
            logger.error(f"FirecrawlService test error: {str(e)}", exc_info=True)
    
    # Run processor test unless direct-only specified
    processor_results = None
    if not args.direct_only:
        print("\nTesting URLProcessor with Firecrawl integration...")
        try:
            processor_results = await test_url_processor(args.url)
            
            if processor_results.get("status") == "processed":
                print("✅ URLProcessor test: SUCCESS")
                print(f"Processed: {processor_results.get('processed_urls', 0)} URLs")
            else:
                print("❌ URLProcessor test: FAILED")
                print(f"Status: {processor_results.get('status', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ URLProcessor test error: {str(e)}")
            logger.error(f"URLProcessor test error: {str(e)}", exc_info=True)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if direct_results:
        scrape_success = direct_results["scrape_result"].get("success", False)
        extract_success = direct_results["extract_result"].get("success", False)
        print(f"FirecrawlService.scrape_url: {'✅ SUCCESS' if scrape_success else '❌ FAILED'}")
        print(f"FirecrawlService.extract_content: {'✅ SUCCESS' if extract_success else '❌ FAILED'}")
    
    if processor_results:
        status = processor_results.get("status")
        success = status == "processed"
        print(f"URLProcessor integration: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    print("\n" + "="*80 + "\n")
    
    # Return success if all tests passed
    if direct_results and processor_results:
        if (direct_results["scrape_result"].get("success", False) and 
            direct_results["extract_result"].get("success", False) and
            processor_results.get("status") == "processed"):
            return 0
    elif direct_results:
        if (direct_results["scrape_result"].get("success", False) and 
            direct_results["extract_result"].get("success", False)):
            return 0
    elif processor_results:
        if processor_results.get("status") == "processed":
            return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 