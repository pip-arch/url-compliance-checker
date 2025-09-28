"""
Initialize Crawl4AI integration with the crawler service.
This module provides a function to integrate Crawl4AI as a secondary fallback crawler.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Flag to track whether Crawl4AI has been integrated
crawl4ai_integrated = False

def integrate_crawl4ai_fallback():
    """
    Integrate Crawl4AI service as a secondary fallback crawler.
    This function is meant to be called from patch_services functions.
    """
    global crawl4ai_integrated
    
    # Only integrate once
    if crawl4ai_integrated:
        logger.info("Crawl4AI already integrated as fallback crawler")
        return True
    
    # Import required modules
    from app.services.crawler import crawler_service
    from app.services.crawlers.crawl4ai_service import Crawl4AIService
    
    logger.info("Integrating Crawl4AI as a secondary fallback crawler")
    
    try:
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
        
        # Update the service to reflect the new fallback chain
        crawler_service.fallback_chain = "Firecrawl → Crawl4AI → Custom BeautifulSoup"
        
        # Set the flag to True
        crawl4ai_integrated = True
        
        logger.info("Successfully integrated Crawl4AI as a secondary fallback crawler")
        logger.info("Crawler fallback chain: Firecrawl → Crawl4AI → Custom BeautifulSoup crawler")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to integrate Crawl4AI: {str(e)}")
        return False 