#!/usr/bin/env python3
"""
Fallback crawler utility using Firecrawl with Crawl4AI as a backup.
This script demonstrates how to use Crawl4AI as a fallback when Firecrawl fails.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Add parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from app
from app.services.crawlers.firecrawl_service import FirecrawlService
from app.services.crawlers.crawl4ai_service import Crawl4AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FallbackCrawler:
    """Crawler that tries Firecrawl first, then falls back to Crawl4AI if it fails."""
    
    def __init__(self):
        """Initialize both services."""
        self.firecrawl = FirecrawlService()
        self.crawl4ai = Crawl4AIService()
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL using Firecrawl with Crawl4AI as fallback.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dict with content and metadata, including which crawler was used
        """
        logger.info(f"Attempting to crawl {url} with Firecrawl")
        
        # Try Firecrawl first
        result = await self.firecrawl.extract_content(url)
        
        # If Firecrawl succeeds, return the result with source info
        if result.get("success", False):
            logger.info(f"Successfully crawled {url} with Firecrawl")
            result["crawler_used"] = "firecrawl"
            return result
        
        # If Firecrawl fails, log the error and try Crawl4AI
        logger.warning(f"Firecrawl failed for {url}: {result.get('error', 'Unknown error')}")
        logger.info(f"Attempting fallback to Crawl4AI for {url}")
        
        # Try Crawl4AI as fallback
        result = await self.crawl4ai.extract_content(url)
        
        # Add which crawler was used
        if result.get("success", False):
            logger.info(f"Successfully crawled {url} with Crawl4AI (fallback)")
            result["crawler_used"] = "crawl4ai"
        else:
            logger.error(f"Both crawlers failed for {url}")
            result["crawler_used"] = "none_succeeded"
        
        return result

async def test_fallback_crawler(urls: List[str]):
    """
    Test the fallback crawler with a list of URLs.
    
    Args:
        urls: List of URLs to test
    """
    crawler = FallbackCrawler()
    
    for url in urls:
        logger.info(f"Testing URL: {url}")
        try:
            result = await crawler.extract_content(url)
            
            if result["success"]:
                logger.info(f"Successfully crawled {url} using {result['crawler_used']}")
                logger.info(f"Content length: {len(result.get('html', ''))} bytes")
                logger.info(f"Markdown length: {len(result.get('markdown', ''))} bytes")
                logger.info(f"Duration: {result.get('duration', 0):.2f} seconds")
            else:
                logger.error(f"Failed to crawl {url} with all available crawlers")
            
            logger.info("-" * 50)
        
        except Exception as e:
            logger.exception(f"Error crawling {url}: {e}")

if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    
    # Example usage
    URLS_TO_TEST = [
        "https://example.com",
        "https://news.ycombinator.com",
        "https://github.com",
        "https://www.python.org",
    ]
    
    # Run the test
    asyncio.run(test_fallback_crawler(URLS_TO_TEST)) 