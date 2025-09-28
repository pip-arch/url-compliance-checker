#!/usr/bin/env python3
"""
Integrate Crawl4AI service as a secondary fallback crawler in the URL-checker system.
This script modifies the crawler service to use Crawl4AI when Firecrawl fails.
"""

import os
import sys
import logging
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(project_root, "data/logs/integrate_crawl4ai.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import required services and modules
from app.services.crawler import crawler_service
from app.services.crawlers.crawl4ai_service import Crawl4AIService


async def integrate_crawl4ai():
    """Integrate Crawl4AI service as a fallback crawler."""
    logger.info("Integrating Crawl4AI as a secondary fallback crawler")
    
    # Initialize Crawl4AI service
    crawl4ai_service = Crawl4AIService()
    
    # Store original method for later use
    original_crawl_with_custom = crawler_service._crawl_with_custom
    
    # Define new custom crawler method that tries Crawl4AI first
    async def enhanced_custom_crawler(url: str) -> Dict[str, Any]:
        """Enhanced custom crawler that tries Crawl4AI first, then falls back to original custom crawler."""
        logger.info(f"Enhanced crawler for {url}: trying Crawl4AI first")
        
        try:
            # Try with Crawl4AI
            result = await crawl4ai_service.extract_content(url)
            
            if result.get("success", False):
                logger.info(f"Successfully crawled {url} with Crawl4AI")
                
                # Format to match the expected output format
                return {
                    "url": url,
                    "title": result.get("metadata", {}).get("title", ""),
                    "full_text": result.get("markdown", ""),
                    "metadata": {
                        "crawled_with": "crawl4ai",
                        "duration": result.get("duration", 0),
                        "html_length": len(result.get("html", ""))
                    }
                }
            else:
                logger.warning(f"Crawl4AI failed for {url}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.warning(f"Error using Crawl4AI for {url}: {str(e)}")
        
        # Fall back to original custom crawler if Crawl4AI fails
        logger.info(f"Falling back to original custom crawler for {url}")
        return await original_crawl_with_custom(url)
    
    # Patch the custom crawler method in the crawler service
    crawler_service._crawl_with_custom = enhanced_custom_crawler
    
    # Also patch the crawl method to mention Crawl4AI in the logs
    original_crawl = crawler_service.crawl
    
    async def enhanced_crawl(url: str) -> Dict[str, Any]:
        """Enhanced crawl method that mentions Crawl4AI in the logs."""
        logger.info(f"Crawling URL: {url} (with Firecrawl → Crawl4AI → Custom fallback chain)")
        return await original_crawl(url)
    
    crawler_service.crawl = enhanced_crawl
    
    logger.info("Successfully integrated Crawl4AI as a secondary fallback crawler")
    logger.info("Crawler fallback chain: Firecrawl → Crawl4AI → Custom BeautifulSoup crawler")
    
    return True


async def test_integration(test_url: str = "https://example.com"):
    """Test the integration by crawling a URL and checking which crawler was used."""
    logger.info(f"Testing Crawl4AI integration with URL: {test_url}")
    
    # First integrate Crawl4AI
    success = await integrate_crawl4ai()
    if not success:
        logger.error("Failed to integrate Crawl4AI")
        return False
    
    # Try crawling a URL
    try:
        result = await crawler_service.crawl(test_url)
        
        if result:
            crawler_used = result.get("metadata", {}).get("crawled_with", "unknown")
            logger.info(f"Successfully crawled {test_url} using {crawler_used}")
            logger.info(f"Title: {result.get('title', 'None')}")
            logger.info(f"Full text length: {len(result.get('full_text', ''))}")
            return True
        else:
            logger.error(f"Failed to crawl {test_url}")
            return False
    except Exception as e:
        logger.error(f"Error testing integration: {str(e)}")
        return False


async def main():
    """Main function to integrate Crawl4AI and test the integration."""
    load_dotenv()  # Load environment variables
    
    # Check if a URL was provided as a command-line argument
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    
    # Integrate Crawl4AI and test the integration
    await test_integration(test_url)


if __name__ == "__main__":
    asyncio.run(main()) 