"""
Test script to verify that the batch processing system works correctly.
"""
import asyncio
import logging
import uuid
import random
from typing import List
from app.core.batch_processor import batch_processor
from app.services.failed_url_service import failed_url_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample URLs to process
SAMPLE_URLS = [
    # Valid URLs
    "https://www.admiralmarkets.com",
    "https://www.admiralmarkets.com/about-us",
    "https://www.example.com",
    "https://en.wikipedia.org/wiki/Foreign_exchange_market",
    "https://www.investopedia.com/terms/f/forex.asp",
    # Invalid URLs (will fail)
    "https://nonexistent-domain-that-should-not-resolve-123456.com",
    "https://example.com/nonexistent-page-that-should-404",
    "https://invalid-url"
]

# Generate a large list of test URLs for batch processing
def generate_test_urls(count: int = 100) -> List[str]:
    """Generate a list of test URLs for batch processing."""
    # Start with the sample URLs
    urls = SAMPLE_URLS.copy()
    
    # Add randomly generated URLs to reach the desired count
    while len(urls) < count:
        # Generate a random URL
        domain = random.choice([
            "example.com",
            "admiralmarkets.com",
            "test-domain.com",
            "webtrader.com",
            "investing.com",
            "finance-blog.com"
        ])
        
        path = random.choice([
            "",
            "about",
            "products",
            "services",
            "forex",
            "cfd",
            "trading",
            "education",
            "blog"
        ])
        
        subpath = random.choice([
            "",
            "item1",
            "page2",
            "article3",
            "post4",
            f"admiralmarkets-review-{uuid.uuid4().hex[:8]}"
        ])
        
        url = f"https://www.{domain}/{path}"
        if subpath:
            url += f"/{subpath}"
        
        urls.append(url)
    
    # Shuffle the URLs to randomize their order
    random.shuffle(urls)
    
    return urls

async def test_batch_processing():
    """Test batch processing with a small batch of URLs."""
    # Generate a batch ID
    batch_id = str(uuid.uuid4())
    
    # Generate a small set of test URLs (using a small number for testing)
    test_urls = generate_test_urls(20)
    logger.info(f"Generated {len(test_urls)} test URLs")
    
    # Process the batch
    logger.info(f"Processing batch {batch_id} with {len(test_urls)} URLs")
    stats = await batch_processor.process_batch(batch_id, test_urls)
    
    # Print the results
    logger.info("=" * 80)
    logger.info("BATCH PROCESSING RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total URLs: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info(f"Filtered: {stats['filtered']}")
    if stats["filter_reasons"]:
        logger.info("Filter reasons:")
        for reason, count in stats["filter_reasons"].items():
            logger.info(f"  - {reason}: {count}")
    logger.info(f"Duration: {stats['duration_seconds']:.2f} seconds")
    logger.info(f"URLs per second: {stats['urls_per_second']:.2f}")
    logger.info("=" * 80)
    
    # Check for failed URLs
    if stats["failed"] > 0:
        logger.info(f"Found {stats['failed']} failed URLs")
        failed_urls = await failed_url_service.get_failed_urls(batch_id)
        
        if failed_urls:
            logger.info("Sample of failed URLs:")
            for i, url in enumerate(failed_urls[:5]):
                logger.info(f"  {i+1}. {url.get('url', 'Unknown')} - Error: {url.get('error', 'Unknown')}")
            
            # Export failed URLs
            export_path = await failed_url_service.export_failed_urls(batch_id)
            if export_path:
                logger.info(f"Failed URLs exported to {export_path}")
    
    return stats

async def main():
    """Run the test and report results."""
    try:
        stats = await test_batch_processing()
        logger.info("✅ Batch processing test completed successfully!")
    except Exception as e:
        logger.error(f"❌ Batch processing test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 