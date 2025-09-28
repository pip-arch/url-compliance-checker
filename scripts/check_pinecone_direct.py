#!/usr/bin/env python3
"""
Script to directly check URLs in Pinecone without using the database
"""
import os
import logging
import asyncio
from dotenv import load_dotenv
import argparse
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def check_url_in_pinecone(url):
    """Check if a specific URL exists in Pinecone"""
    # Load environment variables
    load_dotenv()
    
    # Import services after loading environment variables
    from app.services.vector_db import pinecone_service
    
    # Verify Pinecone is initialized
    if not pinecone_service.is_initialized:
        logger.error("❌ Pinecone service failed to initialize")
        return False
    
    logger.info("✅ Pinecone service initialized successfully!")
    
    # Normalize the URL for consistent comparison
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    if parsed_url.query:
        normalized_url += f"?{parsed_url.query}"
    
    logger.info(f"Original URL: {url}")
    logger.info(f"Normalized URL: {normalized_url}")
    
    # Search for the URL in Pinecone
    try:
        search_results = await pinecone_service.search_similar_content(url, top_k=5)
        
        if search_results:
            logger.info(f"Found {len(search_results)} results in Pinecone")
            exact_match = False
            
            for i, result in enumerate(search_results, 1):
                result_url = result.get("url", "N/A")
                score = result.get("score", 0)
                
                # Normalize the result URL for comparison
                parsed_result = urlparse(result_url)
                normalized_result = f"{parsed_result.scheme}://{parsed_result.netloc}{parsed_result.path}"
                if parsed_result.query:
                    normalized_result += f"?{parsed_result.query}"
                
                logger.info(f"{i}. URL: {result_url} (score: {score:.4f})")
                logger.info(f"   Normalized: {normalized_result}")
                
                # Detailed comparison
                exact_match_orig = result_url == url
                exact_match_norm = normalized_result == normalized_url
                
                logger.info(f"   Exact match (original): {exact_match_orig}")
                logger.info(f"   Exact match (normalized): {exact_match_norm}")
                
                # Check if this is an exact match for our URL
                if exact_match_orig or exact_match_norm:
                    logger.info(f"✅ MATCH FOUND for {url} with score {score:.4f}")
                    exact_match = True
                    
                    # Display a snippet of the content
                    text = result.get("text", "")
                    context_before = result.get("context_before", "")
                    context_after = result.get("context_after", "")
                    
                    if text:
                        logger.info(f"Text: {text}")
                    if context_before:
                        logger.info(f"Context before: {context_before[:50]}...")
                    if context_after:
                        logger.info(f"Context after: {context_after[:50]}...")
            
            return exact_match
        else:
            logger.info(f"No results found in Pinecone for URL: {url}")
            return False
    except Exception as e:
        logger.error(f"Error searching Pinecone: {str(e)}")
        return False

async def test_url_processor_with_pinecone(url):
    """Test if the URLProcessor would skip this URL based on Pinecone check"""
    # Load environment variables
    load_dotenv()
    
    # Import URLProcessor
    from app.core.url_processor import URLProcessor
    
    # Create a processor instance
    processor = URLProcessor()
    
    logger.info(f"Testing URL reprocessing logic for: {url}")
    
    # Check if URL exists in Pinecone using our fixed method
    try:
        # Get the raw search results
        from app.services.vector_db import pinecone_service
        search_results = await pinecone_service.search_similar_content(url, top_k=1)
        
        # Log detailed search results
        logger.info("Direct search results:")
        if search_results:
            result = search_results[0]
            result_url = result.get("url", "")
            score = result.get("score", 0)
            logger.info(f"Found: {result_url} (score: {score:.4f})")
            logger.info(f"URL equality: {result_url == url}")
        else:
            logger.info("No direct search results found")
        
        # Now test with the processor method
        in_pinecone = await processor.url_exists_in_pinecone(url)
        logger.info(f"URL exists in Pinecone according to processor.url_exists_in_pinecone: {in_pinecone}")
        
        if in_pinecone:
            logger.info(f"✅ URL {url} would be SKIPPED by the processor")
        else:
            logger.info(f"❌ URL {url} would be REPROCESSED by the processor")
        
        return in_pinecone
    except Exception as e:
        logger.error(f"Error testing URL processor: {str(e)}")
        return False

async def inspect_url_exists_in_pinecone_method():
    """Inspect the URLProcessor.url_exists_in_pinecone method"""
    from app.core.url_processor import URLProcessor
    import inspect
    
    # Get the source code
    source = inspect.getsource(URLProcessor.url_exists_in_pinecone)
    logger.info("URLProcessor.url_exists_in_pinecone method implementation:")
    logger.info(source)

async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Check URLs directly in Pinecone")
    parser.add_argument("--url", type=str, required=True, help="URL to check in Pinecone")
    parser.add_argument("--test-processor", action="store_true", help="Test if the URL processor would skip this URL")
    parser.add_argument("--inspect-method", action="store_true", help="Inspect the url_exists_in_pinecone method")
    args = parser.parse_args()
    
    url = args.url
    
    # Inspect the method if requested
    if args.inspect_method:
        await inspect_url_exists_in_pinecone_method()
    
    # Check URL in Pinecone
    exists = await check_url_in_pinecone(url)
    
    # Test URL processor logic if requested
    if args.test_processor:
        logger.info("\n=== Testing URL Processor Logic ===")
        would_skip = await test_url_processor_with_pinecone(url)
        
        # Compare results
        if exists and would_skip:
            logger.info("✅ CORRECT: URL exists in Pinecone and would be skipped")
        elif not exists and not would_skip:
            logger.info("✅ CORRECT: URL doesn't exist in Pinecone and would be reprocessed")
        elif exists and not would_skip:
            logger.info("❌ INCORRECT: URL exists in Pinecone but would be reprocessed")
        else:
            logger.info("❌ INCORRECT: URL doesn't exist in Pinecone but would be skipped")

if __name__ == "__main__":
    asyncio.run(main()) 