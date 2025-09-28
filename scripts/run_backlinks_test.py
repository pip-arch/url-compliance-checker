#!/usr/bin/env python3
"""
Script to process backlinks CSV file using the mock processor
"""
import os
import csv
import asyncio
import argparse
import logging
from datetime import datetime
from app.mock_processor import batch_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/backlinks_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def process_backlinks(file_path, column_name, limit=None, offset=0, batch_size=1000):
    """Process backlinks from CSV file using the mock processor"""
    # Extract URLs from CSV
    urls = load_urls_from_csv(file_path, column_name, limit, offset)
    if not urls:
        logger.error(f"No valid URLs found in {file_path}, column '{column_name}'")
        return
    
    logger.info(f"Processing {len(urls)} URLs from {file_path}")
    
    # Process in batches
    batch_count = (len(urls) + batch_size - 1) // batch_size
    processed = 0
    
    start_time = datetime.now()
    
    for i in range(batch_count):
        batch_start = i * batch_size
        batch_end = min(batch_start + batch_size, len(urls))
        batch_urls = urls[batch_start:batch_end]
        
        logger.info(f"Processing batch {i+1}/{batch_count}: {len(batch_urls)} URLs")
        
        batch_id = f"backlinks_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1}"
        
        # Process batch
        stats = await batch_processor.process_batch(batch_id, batch_urls)
        
        # Update processed count
        processed += len(batch_urls)
        
        # Log results
        logger.info(f"Batch {i+1} results:")
        logger.info(f"  Processed: {stats['processed']} URLs")
        logger.info(f"  Success rate: {stats['successful']}/{len(batch_urls)} ({stats['successful']/len(batch_urls)*100:.2f}%)")
        logger.info(f"  Failed: {stats['failed']}, Skipped: {stats['skipped']}, Filtered: {stats['filtered']}")
        logger.info(f"  Processing speed: {stats['urls_per_second']:.2f} URLs/second")
        
        # Calculate and log progress
        elapsed = (datetime.now() - start_time).total_seconds()
        progress = processed / len(urls) * 100
        remaining = elapsed / processed * (len(urls) - processed) if processed > 0 else 0
        
        logger.info(f"Overall progress: {processed}/{len(urls)} ({progress:.2f}%)")
        logger.info(f"Elapsed time: {elapsed:.2f} seconds, Estimated remaining: {remaining:.2f} seconds")
        
        # Sleep briefly between batches
        await asyncio.sleep(1)
    
    # Log final results
    total_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Completed processing {processed} URLs in {total_time:.2f} seconds")
    logger.info(f"Overall processing speed: {processed/total_time:.2f} URLs/second")

def load_urls_from_csv(file_path, column_name, limit=None, offset=0):
    """Load URLs from CSV file"""
    urls = []
    encodings = ['utf-8-sig', 'latin-1', 'utf-16', 'cp1252']
    
    for encoding in encodings:
        try:
            logger.info(f"Trying to read CSV with encoding: {encoding}")
            with open(file_path, 'r', encoding=encoding) as f:
                # Try to determine the delimiter by examining the first few lines
                sample = f.read(4096)
                f.seek(0)
                
                delimiter = '\t' if '\t' in sample else ','
                logger.info(f"Using delimiter: '{delimiter}' for CSV file")
                
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = reader.fieldnames
                
                if not fieldnames:
                    logger.warning(f"No header row found with encoding {encoding}")
                    continue
                    
                logger.info(f"CSV headers: {fieldnames}")
                
                if column_name not in fieldnames:
                    logger.warning(f"Column '{column_name}' not found in CSV. Available columns: {fieldnames}")
                    # Try to find a similar column
                    url_columns = [col for col in fieldnames if "url" in col.lower()]
                    if url_columns:
                        column_name = url_columns[0]
                        logger.info(f"Using alternative column: '{column_name}'")
                    else:
                        continue
                
                # Skip rows if offset is specified
                for i, row in enumerate(reader):
                    if i < offset:
                        continue
                    
                    url = row.get(column_name, "").strip().strip('"\'')
                    if url and url.startswith("http"):
                        urls.append(url)
                    
                    # Stop if we've reached the limit
                    if limit and len(urls) >= limit:
                        break
                
                if urls:
                    logger.info(f"Successfully read CSV with encoding: {encoding}")
                    logger.info(f"Extracted {len(urls)} valid URLs from {file_path}")
                    return urls
        except Exception as e:
            logger.warning(f"Error loading URLs from CSV with encoding {encoding}: {str(e)}")
    
    logger.error(f"Failed to read CSV file with any encoding")
    return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process backlinks CSV file")
    parser.add_argument("--file", type=str, required=True, help="Path to CSV file")
    parser.add_argument("--column", type=str, default="Referring page URL", help="Column name containing URLs")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of URLs to process")
    parser.add_argument("--offset", type=int, default=0, help="Number of rows to skip")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of URLs per batch")
    
    args = parser.parse_args()
    
    # Create required directories
    os.makedirs("data", exist_ok=True)
    
    # Run the processor
    asyncio.run(process_backlinks(args.file, args.column, args.limit, args.offset, args.batch_size)) 