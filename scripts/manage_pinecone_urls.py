#!/usr/bin/env python3
"""
Comprehensive script to manage and analyze URLs in Pinecone
"""
import os
import logging
import asyncio
from dotenv import load_dotenv
import argparse
from urllib.parse import urlparse
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def initialize_services():
    """Initialize services required for managing Pinecone URLs"""
    # Load environment variables
    load_dotenv()
    
    # Import services
    from app.services.vector_db import pinecone_service
    from app.core.url_processor import URLProcessor
    
    # Verify Pinecone is initialized
    if not pinecone_service.is_initialized:
        logger.error("❌ Pinecone service failed to initialize")
        return None, None
    
    logger.info("✅ Pinecone service initialized successfully!")
    
    # Create URL processor
    processor = URLProcessor()
    
    return pinecone_service, processor

async def get_pinecone_stats(pinecone_service):
    """Get statistics about URLs stored in Pinecone"""
    try:
        # Run a generic search to get a sample of stored data
        search_results = await pinecone_service.search_similar_content("admiralmarkets", top_k=100)
        
        if not search_results:
            logger.info("No results found in Pinecone")
            return
        
        logger.info(f"Found {len(search_results)} results in Pinecone")
        
        # Analyze domains
        domains = defaultdict(int)
        url_count = 0
        
        for result in search_results:
            url = result.get("url", "")
            if url:
                url_count += 1
                parsed = urlparse(url)
                domain = parsed.netloc
                domains[domain] += 1
        
        # Display domain statistics
        logger.info(f"Total URLs found: {url_count}")
        logger.info(f"Unique domains: {len(domains)}")
        
        logger.info("Top domains:")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {domain}: {count} URLs")
            
        return search_results
    except Exception as e:
        logger.error(f"Error getting Pinecone stats: {str(e)}")
        return None

async def search_url(pinecone_service, processor, url):
    """Search for a specific URL in Pinecone"""
    try:
        logger.info(f"Searching for URL: {url}")
        
        # Check if URL exists in Pinecone using the processor's method
        in_pinecone = await processor.url_exists_in_pinecone(url)
        
        if in_pinecone:
            logger.info(f"✅ URL {url} exists in Pinecone and would be skipped by the processor")
            
            # Get more details about the URL
            search_results = await pinecone_service.search_similar_content(url, top_k=5)
            
            # Find the exact match
            for result in search_results:
                result_url = result.get("url", "")
                if result_url == url:
                    score = result.get("score", 0)
                    text = result.get("text", "")
                    context_before = result.get("context_before", "")
                    context_after = result.get("context_after", "")
                    
                    logger.info(f"Match details:")
                    logger.info(f"  Score: {score:.4f}")
                    if text:
                        logger.info(f"  Text: {text}")
                    if context_before:
                        logger.info(f"  Context before: {context_before[:50]}...")
                    if context_after:
                        logger.info(f"  Context after: {context_after[:50]}...")
        else:
            logger.info(f"❌ URL {url} does not exist in Pinecone and would be reprocessed by the processor")
    except Exception as e:
        logger.error(f"Error searching for URL: {str(e)}")

async def batch_test_urls(pinecone_service, processor, urls):
    """Test a batch of URLs to determine which would be reprocessed vs skipped"""
    logger.info(f"Testing batch of {len(urls)} URLs")
    
    results = {
        "skipped": [],
        "reprocessed": []
    }
    
    for i, url in enumerate(urls, 1):
        try:
            # Check if URL exists in Pinecone
            in_pinecone = await processor.url_exists_in_pinecone(url)
            
            if in_pinecone:
                results["skipped"].append(url)
                logger.info(f"{i}. SKIP: {url}")
            else:
                results["reprocessed"].append(url)
                logger.info(f"{i}. REPROCESS: {url}")
                
            # Add a small delay to avoid rate limiting
            if i % 10 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error testing URL {url}: {str(e)}")
    
    # Summarize results
    logger.info(f"\nResults summary:")
    logger.info(f"  URLs that would be skipped: {len(results['skipped'])}")
    logger.info(f"  URLs that would be reprocessed: {len(results['reprocessed'])}")
    
    return results

async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Manage and analyze URLs in Pinecone")
    parser.add_argument("--stats", action="store_true", help="Get statistics about URLs in Pinecone")
    parser.add_argument("--url", type=str, help="Search for a specific URL in Pinecone")
    parser.add_argument("--batch-file", type=str, help="Test a batch of URLs from a file (one URL per line)")
    args = parser.parse_args()
    
    # Initialize services
    pinecone_service, processor = await initialize_services()
    if not pinecone_service or not processor:
        return False
    
    # Get statistics about URLs in Pinecone
    if args.stats:
        logger.info("=== Pinecone URL Statistics ===")
        await get_pinecone_stats(pinecone_service)
    
    # Search for a specific URL
    if args.url:
        logger.info("=== URL Search ===")
        await search_url(pinecone_service, processor, args.url)
    
    # Test a batch of URLs
    if args.batch_file:
        logger.info(f"=== Batch Testing URLs from {args.batch_file} ===")
        try:
            with open(args.batch_file, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
            
            logger.info(f"Loaded {len(urls)} URLs from {args.batch_file}")
            await batch_test_urls(pinecone_service, processor, urls)
        except Exception as e:
            logger.error(f"Error processing batch file: {str(e)}")
    
    # If no specific operation requested, show stats
    if not (args.stats or args.url or args.batch_file):
        logger.info("=== Pinecone URL Statistics ===")
        await get_pinecone_stats(pinecone_service)
    
    return True

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    execution_time = time.time() - start_time
    logger.info(f"Execution completed in {execution_time:.2f} seconds") 