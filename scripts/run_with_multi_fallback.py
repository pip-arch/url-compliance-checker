#!/usr/bin/env python3
"""
Script to run the real URL analysis process with multi-tier fallback chain:
1. OpenRouter (primary)
2. OpenAI (first fallback)
3. Keyword analysis (final fallback)
"""
import asyncio
import logging
import time
import os
import argparse
import sys
from datetime import datetime
from urllib.parse import urlparse

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/logs/multi_fallback_process.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define a function to patch services, enabling the multi-fallback flow
def patch_services():
    """
    Patch services before starting URL processing:
    1. Configure OpenAI fallback
    2. Initialize Crawl4AI fallback
    3. Update processing settings
    """
    from app.services.init_crawl4ai import integrate_crawl4ai_fallback
    from app.services.openai_service import openai_service
    
    # Verify OpenAI API key is set
    if not openai_service.is_initialized:
        logger.warning("OpenAI service not initialized. Will use only OpenRouter and keyword fallback.")
    else:
        logger.info(f"OpenAI service initialized with model: {os.getenv('OPENAI_MODEL', 'gpt-4-turbo')}")
    
    # Integrate Crawl4AI as a secondary fallback for crawling
    integrate_crawl4ai_fallback()
    
    logger.info("Services patched successfully.")

def configure_firecrawl_for_speed():
    """Configure Firecrawl for high-speed processing."""
    logger.info("Configuring Firecrawl for high-speed processing")
    
    # Set environment variables for Firecrawl performance
    os.environ["MAX_CONCURRENT_BROWSERS"] = "30"  # Increase concurrent browsers
    os.environ["CRAWL_DELAY"] = "0.5"  # Reduce delay between requests

def import_modules():
    """Import necessary modules for URL processing."""
    from app.core.url_processor import URLProcessor
    from app.core.compliance_checker import compliance_checker
    from app.core.blacklist_manager import CONSOLIDATED_BLACKLIST_FILE
    
    return URLProcessor, compliance_checker, CONSOLIDATED_BLACKLIST_FILE

def load_urls_from_csv(file_path, column_name, limit=None, offset=0):
    """Load URLs from a CSV file."""
    import csv
    
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if column_name not in reader.fieldnames:
                raise ValueError(f"Column '{column_name}' not found in CSV file. Available columns: {reader.fieldnames}")
            
            # Skip offset rows
            for _ in range(offset):
                next(reader, None)
            
            # Read up to limit rows
            count = 0
            for row in reader:
                url = row.get(column_name, "").strip()
                if url and url.startswith(("http://", "https://")):
                    urls.append(url)
                    count += 1
                    if limit is not None and count >= limit:
                        break
        
        logger.info(f"Loaded {len(urls)} URLs from {file_path}, column '{column_name}'")
        return urls
    except Exception as e:
        logger.error(f"Error loading URLs from {file_path}: {str(e)}")
        return []

def apply_domain_sampling(urls, max_per_domain):
    """Limit the number of URLs from the same domain."""
    domain_counts = {}
    sampled_urls = []
    
    for url in urls:
        domain = urlparse(url).netloc
        if domain not in domain_counts:
            domain_counts[domain] = 0
        
        if domain_counts[domain] < max_per_domain:
            sampled_urls.append(url)
            domain_counts[domain] += 1
    
    logger.info(f"Applied domain sampling: {len(sampled_urls)}/{len(urls)} URLs kept (max {max_per_domain} per domain)")
    return sampled_urls

async def process_urls_with_multi_fallback(file_path, column_name, limit=None, offset=0, batch_size=1000):
    """
    Process URLs from CSV file using the real processor with multi-tier fallback.
    
    Args:
        file_path: Path to CSV file with URLs
        column_name: Column name containing URLs
        limit: Maximum number of URLs to process
        offset: Number of URLs to skip from the beginning
        batch_size: Size of processing batches
    """
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
        return
    
    # Apply domain-based sampling to avoid processing too many URLs from the same domain
    MAX_URLS_PER_DOMAIN = int(os.getenv("MAX_URLS_PER_DOMAIN", "10"))
    urls = apply_domain_sampling(urls, MAX_URLS_PER_DOMAIN)
    
    logger.info(f"Processing {len(urls)} URLs from {file_path} (after domain sampling)")
    
    # Initialize the URL processor
    processor = URLProcessor()
    
    # Track statistics
    start_time = datetime.now()
    stats = {
        "urls_queued": len(urls),
        "urls_processed": 0,
        "domains_blacklisted": 0,
        "analysis_methods": {
            "real_llm": 0,
            "openai": 0,
            "fallback": 0
        }
    }
    
    # Process URLs in batches
    batch_id = f"multi_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"Starting batch {batch_id}")
    
    # Process in sequential batches for better control
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i + batch_size]
        batch_size_actual = len(batch_urls)
        
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} with {batch_size_actual} URLs")
        
        # Process batch
        try:
            result = await processor.process_urls(batch_urls, batch_id)
            processed_count = result.get("processed_urls", 0)
            
            if processed_count > 0:
                # Get processed URLs from the database
                processed_urls = await processor.db.get_processed_urls_by_batch(batch_id)
                
                if processed_urls:
                    # Generate compliance report for processed URLs
                    report = await compliance_checker.generate_report(processed_urls, batch_id)
                    
                    # Update statistics
                    stats["urls_processed"] += len(processed_urls)
                    stats["domains_blacklisted"] += report.blacklist_count
                    stats["analysis_methods"]["real_llm"] += report.real_llm_count
                    stats["analysis_methods"]["openai"] += report.openai_count
                    stats["analysis_methods"]["fallback"] += report.fallback_count
                    
                    # Log progress
                    elapsed = (datetime.now() - start_time).total_seconds()
                    progress = stats["urls_processed"] / stats["urls_queued"] * 100
                    urls_per_second = stats["urls_processed"] / elapsed if elapsed > 0 else 0
                    remaining = (stats["urls_queued"] - stats["urls_processed"]) / urls_per_second if urls_per_second > 0 else 0
                    
                    logger.info(f"Progress: {stats['urls_processed']}/{stats['urls_queued']} URLs ({progress:.1f}%), "
                               f"Speed: {urls_per_second:.2f} URLs/sec, "
                               f"Est. remaining: {remaining/60:.1f} min")
                    
                    # Log analysis methods
                    total_analyzed = report.real_llm_count + report.openai_count + report.fallback_count
                    if total_analyzed > 0:
                        real_pct = report.real_llm_count / total_analyzed * 100
                        openai_pct = report.openai_count / total_analyzed * 100
                        fallback_pct = report.fallback_count / total_analyzed * 100
                        logger.info(f"Analysis methods: {report.real_llm_count} real LLM ({real_pct:.1f}%), "
                                  f"{report.openai_count} OpenAI ({openai_pct:.1f}%), "
                                  f"{report.fallback_count} fallback ({fallback_pct:.1f}%)")
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
    
    # Log final statistics
    total_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Processing completed in {total_time:.1f} seconds")
    logger.info(f"URLs processed: {stats['urls_processed']}/{stats['urls_queued']} ({stats['urls_processed']/stats['urls_queued']*100:.1f}%)")
    logger.info(f"Domains blacklisted: {stats['domains_blacklisted']}")
    
    # Log analysis methods
    total_analyzed = sum(stats["analysis_methods"].values())
    if total_analyzed > 0:
        real_pct = stats["analysis_methods"]["real_llm"] / total_analyzed * 100
        openai_pct = stats["analysis_methods"]["openai"] / total_analyzed * 100
        fallback_pct = stats["analysis_methods"]["fallback"] / total_analyzed * 100
        logger.info(f"Analysis methods: {stats['analysis_methods']['real_llm']} real LLM ({real_pct:.1f}%), "
                  f"{stats['analysis_methods']['openai']} OpenAI ({openai_pct:.1f}%), "
                  f"{stats['analysis_methods']['fallback']} fallback ({fallback_pct:.1f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process URLs with multi-tier fallback (OpenRouter -> OpenAI -> Keywords)")
    parser.add_argument("file_path", help="Path to CSV file containing URLs")
    parser.add_argument("column_name", help="Column name containing URLs")
    parser.add_argument("--limit", type=int, help="Maximum number of URLs to process")
    parser.add_argument("--offset", type=int, default=0, help="Number of URLs to skip from the beginning")
    parser.add_argument("--batch-size", type=int, default=10, help="Size of processing batches")
    
    args = parser.parse_args()
    
    # Ensure the logs directory exists
    os.makedirs("data/logs", exist_ok=True)
    
    asyncio.run(process_urls_with_multi_fallback(
        args.file_path,
        args.column_name,
        args.limit,
        args.offset,
        args.batch_size
    )) 