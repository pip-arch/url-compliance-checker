#!/usr/bin/env python3
"""
Extract URLs from a tab-separated CSV file and process them using the improved processor.
This script handles the UTF-16 to UTF-8 conversion automatically and properly extracts
URLs from the "Referring page URL" column.
"""

import os
import sys
import argparse
import asyncio
import logging
import pandas as pd
from datetime import datetime

# Add project root to path to ensure app module can be found
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set environment variable for improved settings - ENSURE REAL DATA ONLY
os.environ["BLACKLIST_CONFIDENCE_THRESHOLD"] = "0.8"
os.environ["REVIEW_CONFIDENCE_THRESHOLD"] = "0.6"
os.environ["REVIEW_FILE"] = "./data/tmp/review_needed.csv"
os.environ["USE_MOCK_PERCENTAGE"] = "0"  # NO MOCK DATA - REAL CRAWLING ONLY
os.environ["FORCE_RECRAWL"] = "True"
os.environ["FIRECRAWL_TIMEOUT"] = "30"  # 30 second timeout for Firecrawl
os.environ["MAX_RETRY_COUNT"] = "3"  # Maximum retries for failed crawls
os.environ["SKIP_ALREADY_PROCESSED"] = "False"  # Force reprocessing of URLs even if in Pinecone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/extract_and_process.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def extract_and_process_urls(file_path, limit=20, batch_size=5, workers=5, skip_existing=False):
    """
    Extract URLs from a file and process them.
    This handles both UTF-16 and UTF-8 encoded files.
    
    Args:
        file_path: Path to the CSV file
        limit: Maximum number of URLs to process
        batch_size: Number of URLs to process in each batch
        workers: Number of concurrent workers
        skip_existing: If True, skip URLs that are already in Pinecone
    """
    logger.info(f"Starting URL extraction and processing from {file_path}")
    logger.info(f"Settings: USE_MOCK_PERCENTAGE=0 (REAL DATA ONLY)")
    
    # Check if the file is UTF-16 encoded
    with open(file_path, 'rb') as f:
        raw_data = f.read(4)
        if raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
            logger.info(f"Detected UTF-16 encoding for {file_path}")
            is_utf16 = True
        else:
            logger.info(f"File appears to be UTF-8 or ASCII encoded: {file_path}")
            is_utf16 = False
    
    try:
        # Read the file directly with pandas, handling encoding
        encoding = 'utf-16' if is_utf16 else 'utf-8'
        logger.info(f"Reading file with {encoding} encoding")
        
        # Try to read with tab separator first
        try:
            df = pd.read_csv(file_path, encoding=encoding, sep='\t', quotechar='"', on_bad_lines='skip')
        except Exception as e:
            logger.warning(f"Failed to read with tab separator: {str(e)}")
            # Try with comma separator
            try:
                df = pd.read_csv(file_path, encoding=encoding, quotechar='"', on_bad_lines='skip')
            except Exception as e:
                logger.error(f"Failed to read CSV: {str(e)}")
                raise
        
        # Check for the URL column
        url_column = None
        for col in df.columns:
            if 'url' in col.lower() and 'referring' in col.lower():
                url_column = col
                break
        
        if not url_column:
            logger.warning("URL column not found, using first column")
            url_column = df.columns[0]
        
        logger.info(f"Using column: {url_column}")
        
        # Extract URLs
        urls = df[url_column].dropna().astype(str).tolist()
        
        # Filter out non-http URLs
        urls = [url for url in urls if url.startswith('http')]
        
        # Apply limit
        if limit and limit < len(urls):
            urls = urls[:limit]
        
        logger.info(f"Extracted {len(urls)} URLs")
        
        # Import URL processor and other modules
        from app.core.url_processor import URLProcessor
        from app.core.compliance_checker import compliance_checker
        
        # Initialize processor
        processor = URLProcessor()
        
        # Patch the url_exists_in_pinecone method to respect skip_existing
        if not skip_existing:
            logger.info("Patching URL processor to force reprocessing of already crawled URLs")
            original_method = processor.url_exists_in_pinecone
            
            async def patched_method(url):
                if skip_existing:
                    return await original_method(url)
                return False  # Always return False to force reprocessing
                
            processor.url_exists_in_pinecone = patched_method
        
        # Process URLs in batches
        total_urls = len(urls)
        batch_count = (total_urls + batch_size - 1) // batch_size
        
        logger.info(f"Processing {total_urls} URLs in {batch_count} batches")
        
        stats = {
            "processed": 0,
            "blacklisted": 0,
            "whitelisted": 0,
            "review": 0,
            "batches_processed": 0,
            "start_time": datetime.now()
        }
        
        for i in range(0, total_urls, batch_size):
            batch_urls = urls[i:i+batch_size]
            batch_number = i // batch_size + 1
            
            # Create batch ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_id = f"extract_batch_{timestamp}_{batch_number}"
            
            logger.info(f"Processing batch {batch_number}/{batch_count}: {len(batch_urls)} URLs")
            
            try:
                # Process batch
                result = await processor.process_urls(batch_urls, batch_id)
                
                # Update stats
                stats["processed"] += len(batch_urls)
                stats["batches_processed"] += 1
                
                # Generate compliance report
                if 'processed_count' in result and result['processed_count'] > 0:
                    logger.info(f"Batch has {result['processed_count']} processed URLs, fetching them...")
                    processed_urls = await processor.db.get_processed_urls_by_batch(batch_id)
                    logger.info(f"Retrieved {len(processed_urls)} processed URLs from database")
                    
                    # Log details about each processed URL
                    for idx, url in enumerate(processed_urls):
                        logger.info(f"  URL {idx+1}: {url.url}, status: {url.status}")
                        # Check if URL has content
                        has_content = hasattr(url, 'content') and url.content is not None
                        logger.info(f"    Has content: {has_content}")
                        if has_content:
                            # Check if content has mentions
                            mention_count = len(url.content.mentions) if url.content.mentions else 0
                            logger.info(f"    Mention count: {mention_count}")
                    
                    if processed_urls:
                        logger.info(f"Generating compliance report for {len(processed_urls)} URLs")
                        report = await compliance_checker.generate_report(processed_urls, batch_id)
                        
                        # Update statistics
                        stats["blacklisted"] += report.blacklist_count
                        stats["whitelisted"] += report.whitelist_count
                        stats["review"] += report.review_count
                        
                        logger.info(f"Batch {batch_id} analysis: "
                                  f"{report.blacklist_count} blacklisted, "
                                  f"{report.whitelist_count} whitelisted, "
                                  f"{report.review_count} for review")
                    else:
                        logger.warning(f"No processed URLs found for batch {batch_id}")
                else:
                    logger.warning(f"Batch {batch_id} has no processed URLs (count: {result.get('processed_count', 0)})")
                
                # Log progress
                elapsed = (datetime.now() - stats["start_time"]).total_seconds()
                progress = stats["processed"] / total_urls * 100
                urls_per_minute = stats["processed"] / (elapsed / 60) if elapsed > 0 else 0
                logger.info(f"Progress: {stats['processed']}/{total_urls} URLs ({progress:.1f}%) | "
                          f"Time elapsed: {elapsed:.1f}s | "
                          f"Speed: {urls_per_minute:.2f} URLs/minute")
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_id}: {str(e)}", exc_info=True)
        
        # Log final stats
        elapsed = (datetime.now() - stats["start_time"]).total_seconds()
        urls_per_minute = stats["processed"] / (elapsed / 60) if elapsed > 0 else 0
        logger.info(f"Processing completed in {elapsed:.1f}s")
        logger.info(f"Processed {stats['processed']} URLs at {urls_per_minute:.2f} URLs/minute")
        logger.info(f"Analysis results: {stats['blacklisted']} blacklisted, {stats['whitelisted']} whitelisted, {stats['review']} for review")
        
        # Check blacklist and review files
        blacklist_file = os.path.join("data", "tmp", "blacklist_consolidated.csv")
        if os.path.exists(blacklist_file):
            with open(blacklist_file, 'r') as f:
                blacklist_count = sum(1 for _ in f) - 1  # Subtract header
                logger.info(f"Total blacklisted URLs: {blacklist_count}")
        
        review_file = os.environ.get("REVIEW_FILE")
        if os.path.exists(review_file):
            with open(review_file, 'r') as f:
                review_count = sum(1 for _ in f) - 1  # Subtract header
                logger.info(f"Total URLs for review: {review_count}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error extracting and processing URLs: {str(e)}", exc_info=True)
        return {"error": str(e)}

async def main():
    """Run the URL extraction and processing script."""
    parser = argparse.ArgumentParser(description='Extract and process URLs from CSV files')
    parser.add_argument('--file', required=True, help='Path to the CSV file')
    parser.add_argument('--limit', type=int, default=20, help='Maximum number of URLs to process')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of URLs per batch')
    parser.add_argument('--workers', type=int, default=5, help='Number of crawler workers')
    parser.add_argument('--skip-existing', action='store_true', help='Skip URLs already in Pinecone')
    args = parser.parse_args()
    
    start_time = datetime.now()
    logger.info(f"Starting URL extraction and processing at {start_time}")
    
    # Process URLs
    try:
        results = await extract_and_process_urls(
            file_path=args.file,
            limit=args.limit,
            batch_size=args.batch_size,
            workers=args.workers,
            skip_existing=args.skip_existing
        )
        
        # Log completion
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Process completed at {end_time}")
        logger.info(f"Total duration: {duration}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 