#!/usr/bin/env python3
"""
Test script for Crawl4AI crawler integration.
This script demonstrates the use of Crawl4AI as a backup crawler.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from app
from app.services.crawlers.crawl4ai_service import Crawl4AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample URLs to test
TEST_URLS = [
    "https://example.com",
    "https://news.ycombinator.com",
    "https://github.com",
    "https://www.python.org",
]

async def test_crawl4ai():
    """Test Crawl4AI crawler with a few test URLs."""
    logger.info("Starting Crawl4AI crawler test")
    
    # Initialize Crawl4AI service
    service = Crawl4AIService()
    
    for url in TEST_URLS:
        logger.info(f"Testing URL: {url}")
        try:
            result = await service.extract_content(url)
            
            if result["success"]:
                logger.info(f"Successfully crawled {url}")
                logger.info(f"Content length: {len(result['html'])} bytes")
                logger.info(f"Markdown length: {len(result['markdown'])} bytes")
                logger.info(f"Duration: {result['duration']:.2f} seconds")
                logger.info("-" * 50)
            else:
                logger.error(f"Failed to crawl {url}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.exception(f"Error testing {url}: {e}")
    
    logger.info("Crawl4AI crawler test completed")

if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    asyncio.run(test_crawl4ai()) 