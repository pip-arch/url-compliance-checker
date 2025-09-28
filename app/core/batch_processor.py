"""
Batch processor for efficiently handling large volumes of URLs.
"""
import os
import asyncio
import logging
import time
import psutil
import gc
import json
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
from datetime import datetime
from app.models.url import URL, URLBatch, URLStatus, URLFilterReason, URLContent
from app.core.url_processor import URLProcessor
from app.services.db import db_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
MAX_URLS_PER_BATCH = int(os.getenv("MAX_URLS_PER_BATCH", "100"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
MAX_REQUESTS_PER_DOMAIN = int(os.getenv("MAX_REQUESTS_PER_DOMAIN", "2"))
DOMAIN_COOLDOWN_PERIOD = float(os.getenv("DOMAIN_COOLDOWN_PERIOD", "3.0"))  # seconds
MAX_CPU_PERCENT = float(os.getenv("MAX_CPU_PERCENT", "80.0"))
MAX_MEMORY_PERCENT = float(os.getenv("MAX_MEMORY_PERCENT", "80.0"))
MEMORY_CHECKPOINT_INTERVAL = int(os.getenv("MEMORY_CHECKPOINT_INTERVAL", "1000"))  # URLs
GC_THRESHOLD = float(os.getenv("GC_THRESHOLD", "75.0"))  # Memory percentage to trigger GC
BATCH_STATE_DIR = os.getenv("BATCH_STATE_DIR", "data/batch_state")

class BatchProcessor:
    """
    Processor for handling large batches of URLs with resource management:
    1. Process URLs in configurable batch sizes
    2. Implement domain-based rate limiting
    3. Monitor system resources and adjust concurrency
    4. Track failed URLs separately
    """

    def __init__(self):
        """Initialize the batch processor."""
        self.url_processor = URLProcessor()
        self.domain_last_request = {}  # Track when each domain was last requested
        self.active_domains = set()    # Track currently active domains
        self.domain_semaphores = {}    # Limit concurrent requests per domain
        
        # Global concurrency control
        self.concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        # Initialize resource monitoring
        self.initial_memory_usage = psutil.virtual_memory().used
        self.peak_memory_usage = self.initial_memory_usage
        self.peak_cpu_usage = 0.0
        self.last_memory_check = time.time()
        
        # Resource utilization history for adaptive tuning
        self.memory_history = []
        self.cpu_history = []
        
        # Ensure batch state directory exists
        os.makedirs(BATCH_STATE_DIR, exist_ok=True)
        
        logger.info(f"BatchProcessor initialized with max {MAX_CONCURRENT_REQUESTS} concurrent requests")
        logger.info(f"Max {MAX_REQUESTS_PER_DOMAIN} concurrent requests per domain")
        logger.info(f"Domain cooldown period: {DOMAIN_COOLDOWN_PERIOD} seconds")
        logger.info(f"Resource limits: CPU {MAX_CPU_PERCENT}%, Memory {MAX_MEMORY_PERCENT}%")
        logger.info(f"Memory checkpoint interval: {MEMORY_CHECKPOINT_INTERVAL} URLs")

    async def process_batch(self, batch_id: str, urls: List[str]) -> Dict[str, Any]:
        """
        Process a batch of URLs with intelligent resource management.
        
        Args:
            batch_id: The ID of the batch
            urls: List of URLs to process
            
        Returns:
            Dict with processing statistics
        """
        logger.info(f"Processing batch {batch_id} with {len(urls)} URLs")
        
        # Check for existing state file - for recovery
        if self._batch_state_exists(batch_id):
            logger.info(f"Found existing state for batch {batch_id}, attempting to resume")
            stats, processed_urls = self._load_batch_state(batch_id)
            # Filter out already processed URLs
            urls = [url for url in urls if url not in processed_urls]
            logger.info(f"Resuming batch {batch_id} with {len(urls)} remaining URLs")
            if not urls:
                logger.info(f"All URLs in batch {batch_id} have already been processed")
                return stats
        else:
            # Initialize statistics
            stats = {
                "total": len(urls),
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "filtered": 0,
                "filter_reasons": {},
                "start_time": datetime.now(),
                "end_time": None,
                "duration_seconds": 0,
                "failed_urls": [],
                "processed_urls": set(),
                "memory_usage": {
                    "initial": self.initial_memory_usage,
                    "peak": self.initial_memory_usage,
                    "checkpoints": []
                },
                "cpu_usage": {
                    "peak": 0.0,
                    "average": 0.0
                }
            }
        
        # Update batch status to PROCESSING
        await self._update_batch_status(batch_id, URLStatus.PROCESSING)
        
        # Process URLs in smaller chunks to avoid memory issues
        chunk_size = min(MAX_URLS_PER_BATCH, len(urls))
        chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]
        
        logger.info(f"Split {len(urls)} URLs into {len(chunks)} chunks of max {chunk_size} URLs")
        
        # Reset monitor values for this session
        self._reset_resource_monitors()
        
        try:
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} with {len(chunk)} URLs")
                
                # Check resource utilization before processing chunk
                self._check_and_optimize_resources()
                
                # Process chunk with resource-aware concurrency
                chunk_stats = await self._process_chunk(batch_id, chunk)
                
                # Update overall statistics
                stats["processed"] += chunk_stats["processed"]
                stats["successful"] += chunk_stats["successful"]
                stats["failed"] += chunk_stats["failed"]
                stats["skipped"] += chunk_stats["skipped"]
                stats["filtered"] += chunk_stats["filtered"]
                stats["failed_urls"].extend(chunk_stats["failed_urls"])
                
                # Track processed URLs for checkpointing
                if "processed_url_list" in chunk_stats:
                    for url in chunk_stats["processed_url_list"]:
                        stats["processed_urls"].add(url)
                
                # Update filter reasons
                for reason, count in chunk_stats["filter_reasons"].items():
                    if reason in stats["filter_reasons"]:
                        stats["filter_reasons"][reason] += count
                    else:
                        stats["filter_reasons"][reason] = count
                
                # Update memory usage statistics
                stats["memory_usage"]["peak"] = self.peak_memory_usage
                current_memory = psutil.virtual_memory().used
                stats["memory_usage"]["current"] = current_memory
                stats["memory_usage"]["checkpoints"].append({
                    "chunk": i+1,
                    "urls_processed": stats["processed"],
                    "memory_used": current_memory,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update CPU usage statistics
                stats["cpu_usage"]["peak"] = self.peak_cpu_usage
                stats["cpu_usage"]["average"] = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
                
                # Save checkpoint state
                self._save_batch_state(batch_id, stats)
                
                # Memory checkpoint - force garbage collection after each chunk
                if i % (MEMORY_CHECKPOINT_INTERVAL // chunk_size) == 0:
                    self._perform_memory_checkpoint()
                
                # Check if we should continue
                if self._should_abort_processing():
                    logger.warning(f"Aborting batch processing due to resource constraints")
                    stats["aborted"] = True
                    break
                
                # Adaptive chunk size based on resource utilization
                chunk_size = self._adjust_chunk_size(chunk_size, stats)
        except Exception as e:
            logger.error(f"Error during batch processing: {str(e)}", exc_info=True)
            stats["error"] = str(e)
        finally:
            # Calculate final statistics
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
            stats["urls_per_second"] = stats["processed"] / stats["duration_seconds"] if stats["duration_seconds"] > 0 else 0
            
            # Final resource usage
            stats["memory_usage"]["final"] = psutil.virtual_memory().used
            stats["memory_usage"]["peak"] = self.peak_memory_usage
            stats["cpu_usage"]["final"] = psutil.cpu_percent(interval=0.1)
            
            # Convert processed_urls set to list for JSON serialization
            stats["processed_urls"] = list(stats["processed_urls"])
            
            # Update batch status to PROCESSED
            await self._update_batch_status(batch_id, URLStatus.PROCESSED)
            
            # Save final state
            self._save_batch_state(batch_id, stats)
            
            logger.info(f"Batch {batch_id} processing completed:")
            logger.info(f"Processed: {stats['processed']}/{stats['total']} URLs")
            logger.info(f"Successful: {stats['successful']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}, Filtered: {stats['filtered']}")
            logger.info(f"Duration: {stats['duration_seconds']:.2f} seconds ({stats['urls_per_second']:.2f} URLs/sec)")
            logger.info(f"Peak memory usage: {self._format_bytes(stats['memory_usage']['peak'])}")
            logger.info(f"Peak CPU usage: {stats['cpu_usage']['peak']:.2f}%")
        
        return stats

    def _reset_resource_monitors(self):
        """Reset resource monitoring values for a new processing session."""
        self.initial_memory_usage = psutil.virtual_memory().used
        self.peak_memory_usage = self.initial_memory_usage
        self.peak_cpu_usage = 0.0
        self.last_memory_check = time.time()
        self.memory_history = []
        self.cpu_history = []

    def _check_and_optimize_resources(self):
        """Check current resource utilization and optimize if needed."""
        # Get current resource usage
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Update tracking
        if memory.used > self.peak_memory_usage:
            self.peak_memory_usage = memory.used
            
        if cpu_percent > self.peak_cpu_usage:
            self.peak_cpu_usage = cpu_percent
            
        # Add to history (keep last 10 readings)
        self.memory_history.append(memory.percent)
        if len(self.memory_history) > 10:
            self.memory_history.pop(0)
            
        self.cpu_history.append(cpu_percent)
        if len(self.cpu_history) > 10:
            self.cpu_history.pop(0)
        
        # Log current resource usage every minute
        current_time = time.time()
        if current_time - self.last_memory_check > 60:
            logger.info(f"Resource usage - Memory: {memory.percent:.1f}% ({self._format_bytes(memory.used)}), CPU: {cpu_percent:.1f}%")
            self.last_memory_check = current_time
        
        # Trigger garbage collection if memory usage is high
        if memory.percent > GC_THRESHOLD:
            logger.warning(f"Memory usage above threshold ({memory.percent:.1f}% > {GC_THRESHOLD:.1f}%), performing garbage collection")
            self._perform_memory_checkpoint()

    def _perform_memory_checkpoint(self):
        """Perform memory optimization with garbage collection."""
        before_gc = psutil.virtual_memory().used
        
        # Run garbage collection
        gc.collect()
        
        # Get memory usage after GC
        after_gc = psutil.virtual_memory().used
        memory_freed = before_gc - after_gc if before_gc > after_gc else 0
        
        logger.info(f"Memory checkpoint: {self._format_bytes(memory_freed)} freed by garbage collection")

    def _adjust_chunk_size(self, current_size: int, stats: Dict[str, Any]) -> int:
        """Adaptively adjust chunk size based on resource utilization."""
        # Get average memory and CPU usage from history
        avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0
        avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
        
        # Calculate error rate from stats
        total_processed = stats["successful"] + stats["failed"]
        error_rate = stats["failed"] / total_processed if total_processed > 0 else 0
        
        # Adjust chunk size based on resource usage and error rate
        if avg_memory > 85 or avg_cpu > 85:
            # High resource usage - decrease chunk size
            new_size = max(10, int(current_size * 0.8))
            logger.info(f"High resource usage detected, reducing chunk size from {current_size} to {new_size}")
            return new_size
        elif (avg_memory < 50 and avg_cpu < 50) and error_rate < 0.1:
            # Low resource usage and error rate - increase chunk size
            new_size = min(MAX_URLS_PER_BATCH, int(current_size * 1.2))
            logger.info(f"Low resource usage detected, increasing chunk size from {current_size} to {new_size}")
            return new_size
        
        # No change needed
        return current_size

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes as human-readable string (KB, MB, GB)."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024 or unit == 'GB':
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024

    def _batch_state_exists(self, batch_id: str) -> bool:
        """Check if a state file exists for this batch ID."""
        state_file = os.path.join(BATCH_STATE_DIR, f"{batch_id}.json")
        return os.path.exists(state_file)

    def _save_batch_state(self, batch_id: str, stats: Dict[str, Any]) -> None:
        """Save batch processing state for potential recovery."""
        state_file = os.path.join(BATCH_STATE_DIR, f"{batch_id}.json")
        try:
            # Convert processed_urls to list if it's a set
            serializable_stats = stats.copy()
            if isinstance(serializable_stats.get("processed_urls"), set):
                serializable_stats["processed_urls"] = list(serializable_stats["processed_urls"])
            
            with open(state_file, 'w') as f:
                json.dump(serializable_stats, f)
            
            logger.debug(f"Saved batch state to {state_file}")
        except Exception as e:
            logger.error(f"Error saving batch state: {str(e)}")

    def _load_batch_state(self, batch_id: str) -> tuple:
        """Load batch processing state for recovery."""
        state_file = os.path.join(BATCH_STATE_DIR, f"{batch_id}.json")
        try:
            with open(state_file, 'r') as f:
                stats = json.load(f)
            
            # Convert processed_urls back to a set
            processed_urls = set(stats.get("processed_urls", []))
            stats["processed_urls"] = processed_urls
            
            logger.info(f"Loaded batch state from {state_file}")
            logger.info(f"Resuming with {stats['processed']}/{stats['total']} URLs already processed")
            
            return stats, processed_urls
        except Exception as e:
            logger.error(f"Error loading batch state: {str(e)}")
            return {
                "total": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "filtered": 0,
                "filter_reasons": {},
                "start_time": datetime.now(),
                "failed_urls": [],
                "processed_urls": set()
            }, set()

    async def _process_chunk(self, batch_id: str, urls: List[str]) -> Dict[str, Any]:
        """Process a chunk of URLs with resource-aware concurrency."""
        stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "filtered": 0,
            "filter_reasons": {},
            "failed_urls": [],
            "processed_url_list": []
        }
        
        # Create a task for each URL
        tasks = []
        for url in urls:
            # Add URL to processed list for checkpointing
            stats["processed_url_list"].append(url)
            
            # Create a URL object
            url_obj = URL(
                id=f"{batch_id}_{stats['processed']}",
                url=url,
                batch_id=batch_id,
                status=URLStatus.PENDING
            )
            
            # Add task to process the URL
            task = asyncio.create_task(self._process_url_with_resource_management(url_obj))
            tasks.append(task)
            
            stats["processed"] += 1
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing URL: {str(result)}")
                stats["failed"] += 1
                stats["failed_urls"].append(urls[i])
                continue
                
            if result["status"] == URLStatus.PROCESSED:
                stats["successful"] += 1
            elif result["status"] == URLStatus.FAILED:
                stats["failed"] += 1
                stats["failed_urls"].append(result["url"])
            elif result["status"] == URLStatus.SKIPPED:
                stats["skipped"] += 1
            elif result["status"] == URLStatus.FILTERED:
                stats["filtered"] += 1
                reason = result.get("filter_reason", "unknown")
                if reason in stats["filter_reasons"]:
                    stats["filter_reasons"][reason] += 1
                else:
                    stats["filter_reasons"][reason] = 1
        
        return stats

    async def _process_url_with_resource_management(self, url_obj: URL) -> Dict[str, Any]:
        """Process a single URL with resource management."""
        try:
            # Extract domain for rate limiting
            domain = urlparse(url_obj.url).netloc
            
            # Ensure domain has a semaphore
            if domain not in self.domain_semaphores:
                self.domain_semaphores[domain] = asyncio.Semaphore(MAX_REQUESTS_PER_DOMAIN)
            
            # Check if we should abort due to resource constraints before acquiring semaphores
            if self._should_abort_processing():
                logger.warning(f"Skipping URL {url_obj.url} due to resource constraints")
                url_obj.status = URLStatus.SKIPPED
                url_obj.filter_reason = URLFilterReason.RESOURCE_LIMIT
                return {
                    "url": url_obj.url,
                    "status": URLStatus.SKIPPED,
                    "filter_reason": URLFilterReason.RESOURCE_LIMIT.value
                }
            
            # Acquire semaphores for concurrency control
            async with self.concurrency_semaphore:
                # Domain-specific rate limiting
                await self._respect_domain_rate_limit(domain)
                
                # Process the URL using a separate semaphore per domain
                async with self.domain_semaphores[domain]:
                    self.active_domains.add(domain)
                    try:
                        logger.debug(f"Processing URL: {url_obj.url}")
                        result = await self.url_processor.process_url(url_obj)
                        self.domain_last_request[domain] = time.time()
                        return result
                    finally:
                        self.active_domains.remove(domain)
        except Exception as e:
            logger.error(f"Error processing URL {url_obj.url}: {str(e)}")
            url_obj.status = URLStatus.FAILED
            url_obj.error = str(e)
            return {
                "url": url_obj.url,
                "status": URLStatus.FAILED,
                "error": str(e)
            }

    async def _respect_domain_rate_limit(self, domain: str) -> None:
        """
        Respect rate limiting for a specific domain.
        Wait if the domain has been requested recently.
        """
        if domain in self.domain_last_request:
            last_request_time = self.domain_last_request[domain]
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            
            if time_since_last_request < DOMAIN_COOLDOWN_PERIOD and domain not in self.active_domains:
                wait_time = DOMAIN_COOLDOWN_PERIOD - time_since_last_request
                logger.debug(f"Rate limiting for domain {domain}, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)

    def _should_abort_processing(self) -> bool:
        """
        Check if processing should be aborted due to resource constraints.
        Returns True if processing should be aborted.
        """
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > MAX_CPU_PERCENT:
            logger.warning(f"CPU usage too high: {cpu_percent}% > {MAX_CPU_PERCENT}%")
            return True
        
        # Track CPU usage history
        self.cpu_history.append(cpu_percent)
        if len(self.cpu_history) > 10:
            self.cpu_history.pop(0)
        
        # Update peak CPU usage
        if cpu_percent > self.peak_cpu_usage:
            self.peak_cpu_usage = cpu_percent
        
        # Check memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        if memory_percent > MAX_MEMORY_PERCENT:
            logger.warning(f"Memory usage too high: {memory_percent}% > {MAX_MEMORY_PERCENT}%")
            return True
        
        # Track memory usage history
        self.memory_history.append(memory_percent)
        if len(self.memory_history) > 10:
            self.memory_history.pop(0)
        
        # Update peak memory usage
        if memory.used > self.peak_memory_usage:
            self.peak_memory_usage = memory.used
        
        return False

    async def _update_batch_status(self, batch_id: str, status: URLStatus) -> None:
        """Update batch status in the database."""
        try:
            # In a real implementation, this would update the batch in the database
            logger.info(f"Updating batch {batch_id} status to {status}")
            # await db_service.update_batch_status(batch_id, status)
        except Exception as e:
            logger.error(f"Error updating batch status: {str(e)}")

# Create a singleton instance
batch_processor = BatchProcessor() 