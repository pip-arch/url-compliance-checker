#!/usr/bin/env python3
import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime
from urllib.parse import urlparse
from asyncio import Semaphore
from tqdm.asyncio import tqdm

# Set environment variable for improved settings
os.environ["BLACKLIST_CONFIDENCE_THRESHOLD"] = "0.8"
os.environ["REVIEW_CONFIDENCE_THRESHOLD"] = "0.6"
os.environ["REVIEW_FILE"] = "./data/tmp/review_needed.csv"
os.environ["USE_MOCK_PERCENTAGE"] = "0"
os.environ["FORCE_RECRAWL"] = "True"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/improved_processing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import the blacklist update function
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_blacklist_from_reports import update_blacklist_from_report

# Constants
MAX_CRAWLER_WORKERS = 40
MAX_URLS_PER_DOMAIN = 20
BATCH_PROGRESS_INTERVAL = 50

def patch_services():
    """Patch services with improved settings"""
    logger.info("Applying improved settings to services")
    # No additional patching needed, environment variables are set at the top
    
    # Integrate Crawl4AI as fallback crawler
    try:
        from app.services.init_crawl4ai import integrate_crawl4ai_fallback
        if integrate_crawl4ai_fallback():
            logger.info("Crawl4AI successfully integrated as fallback crawler")
        else:
            logger.warning("Could not integrate Crawl4AI as fallback crawler")
    except Exception as e:
        logger.warning(f"Could not integrate Crawl4AI: {str(e)}")
        logger.warning("Will continue with default fallback crawler only")

def configure_firecrawl_for_speed():
    """Configure Firecrawl for faster processing"""
    logger.info("Configuring Firecrawl for speed")
    # Settings are already configured via environment variables

def import_modules():
    """Import necessary modules"""
    logger.info("Importing modules")
    from app.core.url_processor import URLProcessor
    from app.core.compliance_checker import compliance_checker
    consolidated_blacklist_file = os.path.join("data", "tmp", "blacklist_consolidated.csv")
    review_file = os.environ.get("REVIEW_FILE", "./data/tmp/review_needed.csv")
    
    # Create review file if it doesn't exist
    if not os.path.exists(review_file):
        review_dir = os.path.dirname(review_file)
        if not os.path.exists(review_dir):
            os.makedirs(review_dir)
        with open(review_file, 'w') as f:
            f.write("URL,Main Domain,Reason,Confidence,Compliance Issues,Batch ID,Timestamp\n")
        logger.info(f"Created review file: {review_file}")
    
    return URLProcessor, compliance_checker, consolidated_blacklist_file

def load_urls_from_csv(file_path, column_name, limit=None, offset=0):
    """Load URLs from CSV file"""
    import pandas as pd
    logger.info(f"Loading URLs from {file_path}, column '{column_name}'")
    
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Check if column exists
        if column_name not in df.columns:
            logger.error(f"Column '{column_name}' not found in {file_path}")
            return []
        
        # Extract URLs
        urls = df[column_name].dropna().astype(str).tolist()
        
        # Apply offset and limit
        if offset:
            urls = urls[offset:]
        if limit:
            urls = urls[:limit]
        
        # Filter out URLs that don't start with http
        urls = [url for url in urls if url.startswith('http')]
        
        logger.info(f"Loaded {len(urls)} URLs from {file_path}")
        return urls
    
    except Exception as e:
        logger.error(f"Error loading URLs from {file_path}: {str(e)}")
        return []

def apply_domain_sampling(urls, max_per_domain):
    """Apply domain-based sampling to avoid processing too many URLs from the same domain"""
    if not max_per_domain:
        return urls
    
    logger.info(f"Applying domain sampling with max {max_per_domain} URLs per domain")
    
    # Group URLs by domain
    domain_urls = {}
    for url in urls:
        domain = urlparse(url).netloc
        if domain not in domain_urls:
            domain_urls[domain] = []
        domain_urls[domain].append(url)
    
    # Sample URLs from each domain
    sampled_urls = []
    for domain, domain_url_list in domain_urls.items():
        if len(domain_url_list) > max_per_domain:
            # Take first max_per_domain URLs
            sampled_urls.extend(domain_url_list[:max_per_domain])
            logger.info(f"Sampled {max_per_domain} of {len(domain_url_list)} URLs from domain {domain}")
        else:
            sampled_urls.extend(domain_url_list)
    
    logger.info(f"After domain sampling: {len(sampled_urls)} URLs")
    return sampled_urls

async def process_urls_improved(file_path, column_name, limit=None, offset=0, batch_size=20, workers=10):
    """Process URLs from CSV file using the improved processor with confidence thresholds"""
    # Patch services first
    patch_services()
    
    # Configure Firecrawl for faster processing
    configure_firecrawl_for_speed()
    
    # Import modules
    URLProcessor, compliance_checker, consolidated_blacklist_file = import_modules()
    
    # Extract URLs from CSV
    urls = load_urls_from_csv(file_path, column_name, limit, offset)
    if not urls:
        logger.error(f"No valid URLs found in {file_path}, column '{column_name}'")
        return {"total_processed": 0}
    
    # Apply domain-based sampling to avoid processing too many URLs from the same domain
    urls = apply_domain_sampling(urls, MAX_URLS_PER_DOMAIN)
    
    logger.info(f"Processing {len(urls)} URLs from {file_path} (after domain sampling)")
    
    # Initialize the URL processor
    processor = URLProcessor()
    
    # Stats tracking
    stats = {
        "urls_queued": len(urls),
        "urls_crawled": 0,
        "urls_analyzed": 0,
        "batches_processed": 0,
        "domains_processed": set(),
        "start_time": datetime.now(),
        "blacklisted": 0,
        "whitelisted": 0,
        "review": 0
    }
    
    # Calculate total batches for progress bar
    total_batches = (len(urls) + batch_size - 1) // batch_size
    
    # Create progress bar
    progress_bar = tqdm(
        total=len(urls),
        desc="Processing URLs",
        unit="url",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )
    
    # Process URLs in batches
    batch_index = 0
    while batch_index * batch_size < len(urls):
        start_idx = batch_index * batch_size
        end_idx = min((batch_index + 1) * batch_size, len(urls))
        urls_to_process = urls[start_idx:end_idx]
        
        # Create batch ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"improved_batch_{timestamp}_{batch_index + 1}"
        
        logger.info(f"Processing batch {batch_index + 1}/{total_batches}: {len(urls_to_process)} URLs with batch ID {batch_id}")
        
        try:
            # Process URLs in this batch
            result = await processor.process_urls(urls_to_process, batch_id)
            
            # Track domains processed
            for url in urls_to_process:
                domain = urlparse(url).netloc
                stats["domains_processed"].add(domain)
            
            # Update stats
            stats["urls_crawled"] += len(urls_to_process)
            stats["batches_processed"] += 1
            
            # Process URL reports with compliance checker
            if 'processed_urls' in result and result['processed_urls'] > 0:
                # Get processed URLs from the database
                processed_urls = await processor.db.get_processed_urls_by_batch(batch_id)
                if processed_urls:
                    # Generate compliance report
                    report = await compliance_checker.generate_report(processed_urls, batch_id)
                    
                    # ✅ PERMANENT FIX: Automatically save blacklisted URLs to CSV
                    new_blacklist_count = await update_blacklist_from_report(report)
                    if new_blacklist_count > 0:
                        logger.info(f"✅ Permanently saved {new_blacklist_count} blacklisted URLs to CSV")
                    
                    # Update statistics
                    stats["urls_analyzed"] += len(processed_urls)
                    stats["blacklisted"] += report.blacklist_count
                    stats["whitelisted"] += report.whitelist_count
                    stats["review"] += report.review_count
                    
                    logger.info(f"Batch {batch_id} analysis: "
                              f"{report.blacklist_count} blacklisted, "
                              f"{report.whitelist_count} whitelisted, "
                              f"{report.review_count} for review")
            
            # Update progress bar
            progress_bar.update(len(urls_to_process))
            
            # Calculate and display ETA
            elapsed = (datetime.now() - stats["start_time"]).total_seconds()
            if stats["urls_crawled"] > 0:
                rate = stats["urls_crawled"] / elapsed
                remaining_urls = stats["urls_queued"] - stats["urls_crawled"]
                eta_seconds = remaining_urls / rate if rate > 0 else 0
                eta_minutes = int(eta_seconds / 60)
                eta_hours = int(eta_minutes / 60)
                eta_minutes = eta_minutes % 60
                
                # Update progress bar description with stats
                progress_bar.set_description(
                    f"Processing URLs | B:{stats['blacklisted']} W:{stats['whitelisted']} R:{stats['review']} | "
                    f"ETA: {eta_hours}h {eta_minutes}m"
                )
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {str(e)}")
        
        # Increment batch index
        batch_index += 1
    
    # Close progress bar
    progress_bar.close()
    
    # Calculate final stats
    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
    logger.info(f"Processing completed in {elapsed:.1f}s")
    logger.info(f"Processed {stats['urls_crawled']} URLs across {len(stats['domains_processed'])} domains")
    logger.info(f"Analysis results: {stats['blacklisted']} blacklisted, {stats['whitelisted']} whitelisted, {stats['review']} for review")
    
    return {
        "total_processed": stats["urls_crawled"],
        "domains_processed": len(stats["domains_processed"]),
        "batches_processed": stats["batches_processed"],
        "elapsed_seconds": elapsed,
        "blacklisted": stats["blacklisted"],
        "whitelisted": stats["whitelisted"],
        "review": stats["review"]
    }

async def main():
    """Run the improved URL processing pipeline."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process URLs with improved confidence settings")
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument("--column", default="Source", help="Column name containing URLs")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of URLs to process")
    parser.add_argument("--offset", type=int, default=0, help="Number of rows to skip")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of URLs per batch")
    parser.add_argument("--workers", type=int, default=10, help="Number of crawler workers")
    parser.add_argument("--max-domain", type=int, default=None, help="Maximum URLs per domain")
    args = parser.parse_args()

    # Log current settings
    logger.info(f"Starting improved URL processing with the following settings:")
    logger.info(f"BLACKLIST_CONFIDENCE_THRESHOLD: {os.environ.get('BLACKLIST_CONFIDENCE_THRESHOLD')}")
    logger.info(f"REVIEW_CONFIDENCE_THRESHOLD: {os.environ.get('REVIEW_CONFIDENCE_THRESHOLD')}")
    logger.info(f"REVIEW_FILE: {os.environ.get('REVIEW_FILE')}")
    logger.info(f"USE_MOCK_PERCENTAGE: {os.environ.get('USE_MOCK_PERCENTAGE')}")
    logger.info(f"FORCE_RECRAWL: {os.environ.get('FORCE_RECRAWL')}")
    logger.info(f"Input file: {args.file}")
    logger.info(f"URL column: {args.column}")
    logger.info(f"Limit: {args.limit}")
    logger.info(f"Offset: {args.offset}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Max URLs per domain: {args.max_domain}")

    start_time = datetime.now()
    logger.info(f"Process started at {start_time}")
    
    # Process URLs
    try:
        global MAX_CRAWLER_WORKERS, MAX_URLS_PER_DOMAIN
        MAX_CRAWLER_WORKERS = args.workers
        MAX_URLS_PER_DOMAIN = args.max_domain or MAX_URLS_PER_DOMAIN
        
        results = await process_urls_improved(
            file_path=args.file,
            column_name=args.column,
            limit=args.limit,
            offset=args.offset,
            batch_size=args.batch_size,
            workers=args.workers
        )
        
        # Calculate statistics
        total_urls = results["total_processed"]
        logger.info(f"Successfully processed {total_urls} URLs")
        logger.info(f"Analysis results: {results.get('blacklisted', 0)} blacklisted, "
                  f"{results.get('whitelisted', 0)} whitelisted, "
                  f"{results.get('review', 0)} for review")
        
        # Calculate blacklist stats
        blacklist_file = os.path.join("data", "tmp", "blacklist_consolidated.csv")
        if os.path.exists(blacklist_file):
            with open(blacklist_file, 'r') as f:
                blacklist_count = sum(1 for _ in f) - 1  # Subtract header
                logger.info(f"Total blacklisted URLs: {blacklist_count}")
        
        # Calculate review stats
        review_file = os.environ.get("REVIEW_FILE")
        if os.path.exists(review_file):
            with open(review_file, 'r') as f:
                review_count = sum(1 for _ in f) - 1  # Subtract header
                logger.info(f"Total URLs for review: {review_count}")
        
        # Log completion
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Process completed at {end_time}")
        logger.info(f"Total duration: {duration}")
        
    except Exception as e:
        logger.error(f"Error processing URLs: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
