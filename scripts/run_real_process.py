#!/usr/bin/env python3
"""
Script to process URLs using the real processor (not the mock)
This will execute the full end-to-end pipeline including:
1. URL validation and filtering
2. Web crawling with Firecrawl
3. Content extraction and processing
4. Vector DB storage with Pinecone
5. Compliance checking with OpenRouter
6. Domain blacklisting
"""
import os
import csv
import asyncio
import argparse
import logging
import uuid
import sys
import numpy as np
import math
import collections
from datetime import datetime
from urllib.parse import urlparse
from asyncio import Semaphore
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/real_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# High-performance settings
MAX_CRAWLER_WORKERS = 20       # Maximum number of concurrent crawler workers
MAX_ANALYZER_WORKERS = 10      # Maximum number of concurrent AI analyzers
MAX_URLS_PER_DOMAIN = 5        # Maximum URLs to process per domain
FIRECRAWL_TIMEOUT_SECONDS = 30 # Reduce timeout for Firecrawl
MAX_POLL_ATTEMPTS = 6          # Reduce polling attempts
POLL_INTERVAL_SECONDS = 2      # Reduce polling interval
BATCH_PROGRESS_INTERVAL = 10   # Log progress every 10 URLs
PROBLEMATIC_DOMAINS = set()    # Track domains that repeatedly fail

# Create mock services for testing
class MockVectorDB:
    def __init__(self):
        self.is_initialized = True
        logger.info("Initialized MOCK vector database service")
    
    async def store_content(self, content):
        logger.info(f"MOCK storing content for URL: {content.url}")
        return {i: f"mock-embedding-{i}" for i in range(len(content.mentions))}

class MockAIService:
    def __init__(self):
        self.is_initialized = True
        logger.info("Initialized MOCK AI analysis service")
    
    async def analyze_content(self, content):
        from app.models.report import URLCategory
        from app.services.ai import AIAnalysisResult
        
        # Simulate blacklisting ~10% of domains
        import random
        from urllib.parse import urlparse
        
        domain = urlparse(content.url).netloc
        if "forex" in domain or "trading" in domain or "scam" in domain or random.random() < 0.1:
            category = URLCategory.BLACKLIST
            explanation = f"MOCK analysis: Domain {domain} contains suspicious keywords"
            issues = ["Potentially misleading marketing", "Unauthorized offering of services"]
        else:
            category = URLCategory.WHITELIST
            explanation = f"MOCK analysis: Domain {domain} appears compliant"
            issues = []
        
        return AIAnalysisResult(
            model="mock-model",
            category=category,
            confidence=0.9,
            explanation=explanation,
            compliance_issues=issues
        )

# Patch services - DISABLED to always use real services
def patch_services():
    import app.services.vector_db as vector_db
    import app.services.ai as ai
    
    # Only check AI service - don't worry about Pinecone for now
    logger.info("USING REAL SERVICES ONLY - But allowing Pinecone to be skipped")
    
    # Set mock crawling to 0%
    from app.services.crawler import crawler_service
    if hasattr(crawler_service, 'mock_percentage'):
        logger.info("Setting mock crawl percentage to 0%")
        crawler_service.mock_percentage = 0
        
    # Check only AI service
    if not hasattr(ai.ai_service, 'is_initialized') or not ai.ai_service.is_initialized:
        logger.error("ERROR: Real AI service failed to initialize - please check OpenRouter API key")
        raise RuntimeError("AI service not initialized. Cannot continue without real AI service.")
        
    # For Pinecone, just log a warning but continue
    if not hasattr(vector_db.pinecone_service, 'is_initialized') or not vector_db.pinecone_service.is_initialized:
        logger.warning("WARNING: Pinecone service not initialized - vector storage will be skipped")
        # Create a simple mock vector service that doesn't do anything
        class SimplePassthroughVectorDB:
            def __init__(self):
                self.is_initialized = True
                logger.info("Using passthrough vector DB - no vectors will be stored")
            
            async def store_content(self, content):
                logger.info(f"Skipping vector storage for URL: {content.url}")
                return {i: f"skipped-embedding-{i}" for i in range(len(content.mentions))}
                
        # Replace with our simple passthrough service
        vector_db.pinecone_service = SimplePassthroughVectorDB()
        
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

# Import modules after patching
def import_modules():
    from app.core.url_processor import URLProcessor, CONSOLIDATED_BLACKLIST_FILE
    from app.core.compliance_checker import compliance_checker
    return URLProcessor, compliance_checker, CONSOLIDATED_BLACKLIST_FILE

# Configure Firecrawl for faster processing
def configure_firecrawl_for_speed():
    try:
        from app.services.crawler import crawler_service
        
        # Override Firecrawl settings for faster processing
        if hasattr(crawler_service, '_crawl_with_firecrawl'):
            original_method = crawler_service._crawl_with_firecrawl
            
            async def faster_firecrawl(url):
                # Skip problematic domains
                domain = urlparse(url).netloc
                if domain in PROBLEMATIC_DOMAINS:
                    logger.info(f"Skipping known problematic domain: {domain}")
                    raise Exception(f"Domain {domain} is in the problematic domains list")
                
                # Apply the optimized settings when calling the original method
                try:
                    return await original_method(url)
                except Exception as e:
                    # Track problematic domains
                    if "timeout" in str(e).lower() or "did not complete within the timeout" in str(e).lower():
                        PROBLEMATIC_DOMAINS.add(domain)
                        logger.warning(f"Added {domain} to problematic domains list")
                    raise
            
            # Replace with optimized version
            crawler_service._crawl_with_firecrawl = faster_firecrawl
            logger.info("Configured Firecrawl for faster processing")
            
            # Also update the polling settings in the crawler module
            if hasattr(crawler_service, 'MAX_POLL_ATTEMPTS'):
                setattr(crawler_service, 'MAX_POLL_ATTEMPTS', MAX_POLL_ATTEMPTS)
                logger.info(f"Set MAX_POLL_ATTEMPTS to {MAX_POLL_ATTEMPTS}")
            
            if hasattr(crawler_service, 'POLL_INTERVAL'):
                setattr(crawler_service, 'POLL_INTERVAL', POLL_INTERVAL_SECONDS)
                logger.info(f"Set POLL_INTERVAL to {POLL_INTERVAL_SECONDS}")
            
            if hasattr(crawler_service, 'REQUEST_TIMEOUT'):
                setattr(crawler_service, 'REQUEST_TIMEOUT', FIRECRAWL_TIMEOUT_SECONDS)
                logger.info(f"Set REQUEST_TIMEOUT to {FIRECRAWL_TIMEOUT_SECONDS}")
                
    except Exception as e:
        logger.warning(f"Failed to configure Firecrawl for speed: {str(e)}")

async def process_urls_real(file_path, column_name, limit=None, offset=0, batch_size=1000):
    """Process URLs from CSV file using the real processor with high-performance parallel processing"""
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
    urls = apply_domain_sampling(urls, MAX_URLS_PER_DOMAIN)
    
    logger.info(f"Processing {len(urls)} URLs from {file_path} (after domain sampling)")
    
    # Initialize the URL processor
    processor = URLProcessor()
    
    # Create queues for coordination between workers
    url_queue = asyncio.Queue()  # URLs to be crawled
    analysis_queue = asyncio.Queue()  # Crawled URLs waiting for analysis
    
    # Create semaphores to limit concurrency
    crawler_semaphore = Semaphore(MAX_CRAWLER_WORKERS)
    analyzer_semaphore = Semaphore(MAX_ANALYZER_WORKERS)
    
    # Create message queue for status updates
    status_updates = asyncio.Queue()
    
    # Track statistics
    start_time = datetime.now()
    stats = {
        "urls_queued": len(urls),
        "urls_crawled": 0,
        "urls_analyzed": 0,
        "urls_failed": 0,
        "domains_blacklisted": 0,
        "domains_processed": set(),
        "batch_count": (len(urls) + batch_size - 1) // batch_size,
        "current_batch": 0,
        "results": []
    }
    
    # Fill the queue with URLs
    for url in urls:
        await url_queue.put(url)
    
    # Create batch IDs
    batch_count = (len(urls) + batch_size - 1) // batch_size
    batch_ids = [f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1}" for i in range(batch_count)]
    
    # Status monitor task
    async def status_monitor():
        """Monitor and log the processing status."""
        last_time = time.time()
        last_urls_analyzed = 0
        try:
            while not stop_event.is_set():
                current_time = time.time()
                elapsed = current_time - last_time
                current_urls_analyzed = analyzer_worker.urls_analyzed
                
                # Calculate processing speed
                if elapsed > 0:
                    urls_per_sec = (current_urls_analyzed - last_urls_analyzed) / elapsed
                else:
                    urls_per_sec = 0
                
                # Prepare report stats string
                report_stats = ""
                if compliance_report:
                    report_stats = (
                        f"Report status: {compliance_report.status}, "
                        f"Blacklisted: {compliance_report.blacklist_count}, "
                        f"Whitelisted: {compliance_report.whitelist_count}, "
                        f"Review: {compliance_report.review_count}, "
                        f"Total: {compliance_report.total_urls}, "
                        f"Processed: {compliance_report.processed_urls}"
                    )
                
                # Update stats based on message type
                if update["type"] == "crawl_complete":
                    stats["urls_crawled"] += 1
                    if stats["urls_crawled"] % BATCH_PROGRESS_INTERVAL == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        progress = stats["urls_crawled"] / stats["urls_queued"] * 100
                        urls_per_second = stats["urls_crawled"] / elapsed if elapsed > 0 else 0
                        remaining = (stats["urls_queued"] - stats["urls_crawled"]) / urls_per_second if urls_per_second > 0 else 0
                        
                        logger.info(f"Progress: {stats['urls_crawled']}/{stats['urls_queued']} URLs ({progress:.1f}%), "
                                   f"Speed: {urls_per_second:.2f} URLs/sec, "
                                   f"Est. remaining: {remaining/60:.1f} min")
                
                elif update["type"] == "crawl_error":
                    stats["urls_failed"] += 1
                
                elif update["type"] == "analysis_complete":
                    stats["urls_analyzed"] += 1
                    
                    # Track blacklisted domains
                    blacklisted = update.get("blacklisted", False)
                    if blacklisted:
                        stats["domains_blacklisted"] += 1
                        logger.info(f"Domain blacklisted: {update.get('domain', '')}")
                
                elif update["type"] == "batch_complete":
                    batch_num = update.get("batch_num", 0)
                    batch_report = update.get("report", {})
                    stats["results"].append({
                        "batch_id": batch_ids[batch_num-1] if batch_num <= len(batch_ids) else "unknown",
                        "batch_num": batch_num,
                        "report": batch_report
                    })
                    logger.info(f"Batch {batch_num} completed: "
                               f"{batch_report.get('blacklist_count', 0)} blacklisted, "
                               f"{batch_report.get('whitelist_count', 0)} whitelisted, "
                               f"{batch_report.get('review_count', 0)} for review")
                
                # Mark as done
                status_updates.task_done()
                
        except Exception as e:
            logger.error(f"Error in status monitor: {str(e)}")
    
    # Crawler workers
    async def crawler_worker():
        # Track a batch of URLs to process together
        batch_urls = []
        batch_size_internal = 10  # Process 10 URLs at a time
        
        # Helper function to process a batch of URLs
        async def process_url_batch(urls_to_process):
            if not urls_to_process:
                return
            
            # Get batch number and ID for this batch
            batch_index = min(stats["urls_crawled"] // batch_size, len(batch_ids) - 1)
            batch_id = batch_ids[batch_index]
            
            # Acquire semaphore for the whole batch
            async with crawler_semaphore:
                try:
                    # Process URLs as a batch
                    logger.debug(f"Processing batch of {len(urls_to_process)} URLs")
                    result = await processor.process_urls(urls_to_process, batch_id)
                    
                    # Track domains processed
                    for url in urls_to_process:
                        domain = urlparse(url).netloc
                        stats["domains_processed"].add(domain)
                    
                    # Put URL info into the analysis queue
                    processed_count = result.get("processed_urls", 0)
                    
                    if processed_count > 0:
                        # Get processed URLs from the result
                        processed_urls = await processor.db.get_processed_urls_by_batch(batch_id)
                        
                        if processed_urls:
                            # Add each URL to the analysis queue
                            for url_obj in processed_urls:
                                await analysis_queue.put({
                                    "url": url_obj.url,
                                    "url_obj": url_obj,
                                    "batch_id": batch_id,
                                    "batch_num": batch_index + 1
                                })
                    
                    # Update stats
                    stats["urls_crawled"] += len(urls_to_process)
                    
                    # Log progress periodically
                    if stats["urls_crawled"] % BATCH_PROGRESS_INTERVAL == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        progress = stats["urls_crawled"] / stats["urls_queued"] * 100
                        urls_per_second = stats["urls_crawled"] / elapsed if elapsed > 0 else 0
                        remaining = (stats["urls_queued"] - stats["urls_crawled"]) / urls_per_second if urls_per_second > 0 else 0
                        
                        logger.info(f"Progress: {stats['urls_crawled']}/{stats['urls_queued']} URLs ({progress:.1f}%), "
                                   f"Speed: {urls_per_second:.2f} URLs/sec, "
                                   f"Est. remaining: {remaining/60:.1f} min")
                    
                    # Log batch results
                    logger.info(f"Batch results for {len(urls_to_process)} URLs: "
                               f"Processed: {result.get('processed_urls', 0)}, "
                               f"Already Processed: {result.get('already_processed', 0)}, "
                               f"Blacklisted Skipped: {result.get('blacklisted_skipped', 0)}, "
                               f"Skipped: {result.get('skipped_urls', 0)}, "
                               f"Blacklisted domains: {result.get('blacklisted_domains', 0)}")
                    
                except Exception as e:
                    logger.error(f"Error processing URL batch: {str(e)}")
                    
                    # Update failed count
                    stats["urls_failed"] += len(urls_to_process)
                    
                    # Log each failed URL
                    for url in urls_to_process:
                        domain = urlparse(url).netloc
                        await status_updates.put({
                            "type": "crawl_error",
                            "url": url,
                            "domain": domain
                        })
        
        while True:
            try:
                # Get URL from queue
                url = await url_queue.get()
                if url is None:  # Sentinel value
                    url_queue.task_done()
                    
                    # Process any remaining URLs in the batch
                    if batch_urls:
                        await process_url_batch(batch_urls)
                        batch_urls = []
                        
                    break
                
                # Add URL to batch
                batch_urls.append(url)
                
                # Process in small batches
                if len(batch_urls) >= batch_size_internal:
                    await process_url_batch(batch_urls)
                    batch_urls = []
                
                # Mark task as done
                url_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in crawler worker: {str(e)}")
                
    # Analyzer workers
    async def analyzer_worker():
        # Track URLs by batch
        batch_urls = collections.defaultdict(list)
        
        # Helper function to analyze a batch of URLs
        async def analyze_url_batch(batch_id, batch_num, urls_to_analyze):
            if not urls_to_analyze:
                return
            
            # Acquire semaphore
            async with analyzer_semaphore:
                try:
                    # Run compliance check on all URLs in the batch
                    logger.info(f"Running compliance check on {len(urls_to_analyze)} URLs from batch {batch_id}")
                    report = await compliance_checker.generate_report(urls_to_analyze, batch_id)
                    
                    # Update status
                    await status_updates.put({
                        "type": "batch_complete",
                        "batch_id": batch_id,
                        "batch_num": batch_num,
                        "report": report
                    })
                    
                    # Update analyzed count
                    stats["urls_analyzed"] += len(urls_to_analyze)
                    
                    # Track blacklisted domains
                    for url_obj in urls_to_analyze:
                        domain = urlparse(url_obj.url).netloc
                        
                        # Get URL report from compliance report instead of accessing category directly
                        is_blacklisted = False
                        if hasattr(report, "url_reports") and report.url_reports:
                            for url_report in report.url_reports:
                                if url_report.url == url_obj.url:
                                    # Compare with the URLCategory enum value, not the string
                                    from app.models.report import URLCategory
                                    is_blacklisted = url_report.category == URLCategory.BLACKLIST
                                    break
                        
                        if is_blacklisted:
                            stats["domains_blacklisted"] += 1
                            logger.info(f"Domain blacklisted: {domain}")
                        
                        await status_updates.put({
                            "type": "analysis_complete",
                            "url": url_obj.url,
                            "domain": domain,
                            "blacklisted": is_blacklisted
                        })
                    
                except Exception as e:
                    logger.error(f"Error analyzing URL batch: {str(e)}")
        
        while True:
            try:
                # Get URL info from queue
                url_info = await analysis_queue.get()
                if url_info is None:  # Sentinel value
                    analysis_queue.task_done()
                    
                    # Process any remaining batches
                    for batch_id, urls in batch_urls.items():
                        if urls:
                            batch_num = int(batch_id.split('_')[-1])
                            await analyze_url_batch(batch_id, batch_num, urls)
                            
                    break
                
                url = url_info["url"]
                url_obj = url_info.get("url_obj")
                batch_id = url_info["batch_id"]
                batch_num = url_info["batch_num"]
                
                # Group URLs by batch for batch analysis
                if url_obj:
                    batch_urls[batch_id].append(url_obj)
                
                # If we have accumulated enough URLs for this batch, analyze them all
                if len(batch_urls[batch_id]) >= batch_size or url_queue.empty():
                    if batch_urls[batch_id]:
                        await analyze_url_batch(batch_id, batch_num, batch_urls[batch_id])
                        batch_urls[batch_id] = []
                
                # Mark task as done
                analysis_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in analyzer worker: {str(e)}")
    
    # Start the monitor task
    monitor_task = asyncio.create_task(status_monitor())
    
    # Start crawler workers
    crawler_tasks = []
    for i in range(MAX_CRAWLER_WORKERS):
        task = asyncio.create_task(crawler_worker())
        crawler_tasks.append(task)
    
    # Start analyzer workers
    analyzer_tasks = []
    for i in range(MAX_ANALYZER_WORKERS):
        task = asyncio.create_task(analyzer_worker())
        analyzer_tasks.append(task)
    
    # Wait for all tasks to be processed
    await url_queue.join()
    logger.info("All URLs have been processed")
    
    # Add sentinel values to signal workers to exit
    for _ in range(MAX_CRAWLER_WORKERS):
        await url_queue.put(None)
    for _ in range(MAX_ANALYZER_WORKERS):
        await analysis_queue.put(None)
    
    # Wait for analyzer queues to be processed (remaining batches)
    await analysis_queue.join()
    
    # Signal status monitor to exit
    await status_updates.put(None)
    await status_updates.join()
    
    # Wait for all tasks to complete
    await asyncio.gather(*crawler_tasks, *analyzer_tasks, monitor_task)
    
    # Log final results
    total_time = (datetime.now() - start_time).total_seconds()
    processing_speed = stats["urls_crawled"]/total_time if total_time > 0 and stats["urls_crawled"] > 0 else 0
    logger.info(f"Completed processing {stats['urls_crawled']} URLs in {total_time:.2f} seconds")
    logger.info(f"Overall processing speed: {processing_speed:.2f} URLs/second")
    logger.info(f"Domains processed: {len(stats['domains_processed'])}")
    logger.info(f"Domains blacklisted: {stats['domains_blacklisted']}")
    logger.info(f"Consolidated blacklist file: {consolidated_blacklist_file}")
    
    # Summarize all batch results
    total_blacklisted = sum(r["report"].blacklist_count for r in stats["results"] if hasattr(r["report"], "blacklist_count"))
    total_whitelisted = sum(r["report"].whitelist_count for r in stats["results"] if hasattr(r["report"], "whitelist_count"))
    total_review = sum(r["report"].review_count for r in stats["results"] if hasattr(r["report"], "review_count"))
    
    logger.info("==================== FINAL RESULTS ====================")
    logger.info(f"Total batches processed: {len(stats['results'])}/{stats['batch_count']}")
    logger.info(f"Total URLs processed: {stats['urls_crawled']}")
    logger.info(f"Total URLs failed: {stats['urls_failed']}")
    logger.info(f"Total blacklisted: {total_blacklisted}")
    logger.info(f"Total whitelisted: {total_whitelisted}")
    logger.info(f"Total needing review: {total_review}")
    logger.info(f"Total processing time: {total_time:.2f} seconds")
    logger.info(f"Processing speed: {processing_speed:.2f} URLs/second")
    logger.info("=======================================================")

def apply_domain_sampling(urls, max_per_domain=5):
    """Apply domain-based sampling to avoid processing too many URLs from the same domain"""
    if not max_per_domain or max_per_domain <= 0:
        return urls
    
    domains = {}
    result = []
    
    for url in urls:
        domain = urlparse(url).netloc
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(url)
    
    # For each domain, take up to max_per_domain URLs
    for domain, domain_urls in domains.items():
        sampled = domain_urls[:max_per_domain]
        result.extend(sampled)
        
        if len(domain_urls) > max_per_domain:
            logger.info(f"Sampled {max_per_domain} URLs from domain {domain} (out of {len(domain_urls)} total)")
    
    logger.info(f"Domain sampling reduced URL count from {len(urls)} to {len(result)}")
    return result

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
                    
                    # Handle potentially empty or NaN values
                    url_value = row.get(column_name, "")
                    if isinstance(url_value, float) and math.isnan(url_value):  # Handle NaN
                        continue
                        
                    url = str(url_value).strip().strip('"\'')
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
    parser = argparse.ArgumentParser(description="Process real URLs with the full pipeline")
    parser.add_argument("--file", type=str, required=True, help="Path to CSV file")
    parser.add_argument("--column", type=str, default="Referring page URL", help="Column name containing URLs")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of URLs to process")
    parser.add_argument("--offset", type=int, default=0, help="Number of rows to skip")
    parser.add_argument("--batch-size", type=int, default=200, help="Number of URLs per batch")
    parser.add_argument("--workers", type=int, default=20, help="Number of crawler workers")
    parser.add_argument("--max-domain", type=int, default=5, help="Maximum URLs per domain")
    
    args = parser.parse_args()
    
    # Override global settings if provided via arguments
    if args.workers:
        MAX_CRAWLER_WORKERS = args.workers
    
    if args.max_domain:
        MAX_URLS_PER_DOMAIN = args.max_domain
    
    # Create required directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/tmp", exist_ok=True)
    
    # Run the real processor
    asyncio.run(process_urls_real(args.file, args.column, args.limit, args.offset, args.batch_size)) 