"""
Test script for incremental batch scaling tests.
This script tests the batch processing system with increasingly larger batches
and documents performance metrics at each level.
"""
import os
import csv
import sys
import uuid
import time
import json
import logging
import asyncio
import random
import argparse
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
from app.core.batch_processor import batch_processor
from app.services.crawler import crawler_service
from app.services.error_handler import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/batch_scaling_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get environment variables or use defaults
DEFAULT_TEST_SIZES = [100, 1000, 10000, 50000, 100000]
RESULTS_DIR = os.getenv("RESULTS_DIR", "data/test_results")
SAMPLE_DOMAINS = [
    "example.com",
    "blog.example.com",
    "forex-review.com",
    "tradingplatforms.com",
    "investing.com",
    "forexbrokerreviews.org",
    "finance-news.com",
    "trading-insights.net",
    "brokersrating.com",
    "forexbrokerguide.com",
    "marketanalysis.org",
    "investmentadvice.net",
    "financialtimes.com",
    "wallstreetjournal.com",
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "forbes.com",
    "tradingview.com",
    "seekingalpha.com"
]

class BatchScalingTest:
    """
    Test the batch processing system with increasingly larger batches:
    1. Generate test URLs with realistic domain distribution
    2. Process batches of different sizes
    3. Collect and report performance metrics
    4. Generate recommendations for production configuration
    """
    
    def __init__(self):
        """Initialize the batch scaling test."""
        # Ensure results directory exists
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Initialize test metrics
        self.test_results = {}
        self.start_time = datetime.now()
        
        # Track Firecrawl API usage
        self.initial_credits_used = crawler_service.credits_used
        
        logger.info(f"BatchScalingTest initialized")
        logger.info(f"Starting with {self.initial_credits_used} Firecrawl credits used")
        
    async def run_test(self, batch_sizes: List[int] = DEFAULT_TEST_SIZES, run_id: str = None, 
                      input_file: str = None, column: str = None, limit: int = None, offset: int = 0):
        """
        Run the batch scaling test with the specified batch sizes.
        
        Args:
            batch_sizes: List of batch sizes to test
            run_id: Optional run ID for tracking test results
            input_file: Path to CSV file containing URLs
            column: Column name in CSV containing URLs
            limit: Maximum number of URLs to process
            offset: Starting index in the URL list
        """
        if run_id is None:
            run_id = f"batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        logger.info(f"Starting batch scaling test {run_id}")
        
        # If input file is provided, extract URLs from it
        all_urls = []
        if input_file and column:
            logger.info(f"Loading URLs from file: {input_file}, column: {column}")
            all_urls = self.load_urls_from_csv(input_file, column)
            logger.info(f"Loaded {len(all_urls)} URLs from file")
            
            # Apply limit and offset if specified
            if offset > 0:
                all_urls = all_urls[offset:]
                logger.info(f"Applied offset {offset}, {len(all_urls)} URLs remaining")
            
            if limit:
                all_urls = all_urls[:limit]
                logger.info(f"Applied limit {limit}, using {len(all_urls)} URLs")
            
            # If batch_sizes is default and we have a limit, use just one batch
            if batch_sizes == DEFAULT_TEST_SIZES and limit:
                batch_sizes = [limit]
                logger.info(f"Using single batch size of {limit} for file input")

        test_summary = {
            "run_id": run_id,
            "start_time": datetime.now().isoformat(),
            "batch_sizes": batch_sizes,
            "results": {},
            "firecrawl_usage": {
                "initial_credits": self.initial_credits_used,
                "final_credits": self.initial_credits_used,
                "credits_used": 0
            },
            "recommendations": {}
        }
        
        try:
            # Run tests for each batch size
            for size in batch_sizes:
                logger.info(f"Testing batch size: {size}")
                
                # Generate or select test URLs
                test_urls = []
                if all_urls:
                    # Use URLs from input file
                    test_urls = all_urls[:size] if len(all_urls) > size else all_urls
                    logger.info(f"Using {len(test_urls)} URLs from input file")
                else:
                    # Generate test URLs
                    test_urls = self.generate_test_urls(size)
                    logger.info(f"Generated {len(test_urls)} test URLs")
                
                # Save test URLs to file
                urls_file = os.path.join(RESULTS_DIR, f"test_urls_{run_id}_{size}.csv")
                self.save_urls_to_file(test_urls, urls_file)
                
                # Process batch
                batch_id = f"test_{run_id}_{size}"
                batch_stats = await self.process_batch(batch_id, test_urls)
                
                # Store results
                test_summary["results"][size] = batch_stats
                
                # Log results
                self.log_batch_results(size, batch_stats)
                
                # Save results after each batch size
                self.save_test_results(test_summary, run_id)
                
                # Wait briefly between tests
                await asyncio.sleep(5)
                
                # If we're processing from a file and have used all URLs, stop
                if all_urls and len(test_urls) < size:
                    logger.info(f"Processed all {len(all_urls)} URLs from input file, stopping")
                    break
            
            # Calculate Firecrawl usage
            test_summary["firecrawl_usage"]["final_credits"] = crawler_service.credits_used
            test_summary["firecrawl_usage"]["credits_used"] = crawler_service.credits_used - self.initial_credits_used
            
            # Generate configuration recommendations
            test_summary["recommendations"] = self.generate_recommendations(test_summary)
            
            # Save final results
            self.save_test_results(test_summary, run_id)
            
            logger.info(f"Batch scaling test completed. Results saved to {RESULTS_DIR}")
            
            return test_summary
        except Exception as e:
            logger.error(f"Error during batch scaling test: {str(e)}", exc_info=True)
            
            # Save results even if test fails
            test_summary["error"] = str(e)
            self.save_test_results(test_summary, run_id)
            
            return test_summary
    
    def load_urls_from_csv(self, file_path: str, column_name: str) -> List[str]:
        """
        Load URLs from a CSV file.
        
        Args:
            file_path: Path to CSV file
            column_name: Name of column containing URLs
            
        Returns:
            List of URLs
        """
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                # Try different delimiters
                sample = f.read(4096)
                f.seek(0)
                
                # Check if the file has tabs
                if '\t' in sample:
                    delimiter = '\t'
                else:
                    delimiter = ','
                
                logger.info(f"Using delimiter: '{delimiter}' for CSV file")
                
                reader = csv.DictReader(f, delimiter=delimiter)
                if column_name not in reader.fieldnames:
                    logger.error(f"Column '{column_name}' not found in CSV. Available columns: {reader.fieldnames}")
                    return []
                
                for row in reader:
                    url = row.get(column_name, "").strip()
                    if url and url.startswith("http"):
                        urls.append(url)
                
                logger.info(f"Extracted {len(urls)} valid URLs from column '{column_name}'")
                return urls
        except Exception as e:
            logger.error(f"Error loading URLs from CSV file: {str(e)}")
            return []
    
    def generate_test_urls(self, count: int) -> List[str]:
        """
        Generate test URLs with realistic domain distribution.
        
        Args:
            count: Number of URLs to generate
            
        Returns:
            List of generated URLs
        """
        urls = []
        
        # Determine domain distribution
        # 60% from sample domains, 40% randomly generated
        sample_domain_count = int(count * 0.6)
        random_domain_count = count - sample_domain_count
        
        # Generate URLs from sample domains
        domains_per_sample = max(1, sample_domain_count // len(SAMPLE_DOMAINS))
        for domain in SAMPLE_DOMAINS:
            for _ in range(domains_per_sample):
                if len(urls) >= sample_domain_count:
                    break
                
                path = self._generate_random_path()
                urls.append(f"https://{domain}/{path}")
            
            if len(urls) >= sample_domain_count:
                break
        
        # Fill remaining sample URLs if needed
        while len(urls) < sample_domain_count:
            domain = random.choice(SAMPLE_DOMAINS)
            path = self._generate_random_path()
            urls.append(f"https://{domain}/{path}")
        
        # Generate random domain URLs
        for _ in range(random_domain_count):
            domain = self._generate_random_domain()
            path = self._generate_random_path()
            urls.append(f"https://{domain}/{path}")
        
        # Shuffle URLs
        random.shuffle(urls)
        
        return urls
    
    def _generate_random_domain(self) -> str:
        """Generate a random domain name."""
        # Generate common TLDs
        tlds = ["com", "org", "net", "io", "co", "info"]
        
        # Generate domain parts
        domain_parts = ["trading", "forex", "finance", "invest", "market", "money", 
                        "stock", "broker", "review", "blog", "news", "analysis", 
                        "capital", "asset", "wealth", "portfolio", "trader", "currency"]
        
        # Randomly decide if it should be a subdomain
        if random.random() < 0.3:
            subdomain = random.choice(domain_parts)
            domain = random.choice(domain_parts)
            tld = random.choice(tlds)
            return f"{subdomain}.{domain}.{tld}"
        else:
            domain = random.choice(domain_parts)
            tld = random.choice(tlds)
            return f"{domain}.{tld}"
    
    def _generate_random_path(self) -> str:
        """Generate a random URL path."""
        # Common path components
        path_parts = ["blog", "article", "review", "news", "post", "guide", "analysis", 
                      "comparison", "admiralmarkets", "trading", "forex", "platform", 
                      "broker", "investment", "strategy", "market", "report"]
        
        # Randomly generate path depth (1-3 levels)
        depth = random.randint(1, 3)
        
        path = []
        for _ in range(depth):
            part = random.choice(path_parts)
            
            # Sometimes add a number to the path
            if random.random() < 0.3:
                part += f"-{random.randint(1, 100)}"
                
            path.append(part)
        
        # Sometimes add .html extension
        if random.random() < 0.2:
            path[-1] += ".html"
            
        return "/".join(path)
    
    def save_urls_to_file(self, urls: List[str], filename: str):
        """Save test URLs to a CSV file."""
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["url"])
                for url in urls:
                    writer.writerow([url])
            
            logger.info(f"Saved {len(urls)} test URLs to {filename}")
        except Exception as e:
            logger.error(f"Error saving URLs to file: {str(e)}")
    
    async def process_batch(self, batch_id: str, urls: List[str]) -> Dict[str, Any]:
        """
        Process a batch of URLs and collect performance metrics.
        
        Args:
            batch_id: ID for the batch
            urls: List of URLs to process
            
        Returns:
            Dict with batch processing results and metrics
        """
        logger.info(f"Processing batch {batch_id} with {len(urls)} URLs")
        
        # Record start time and resources
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        # Process the batch
        stats = await batch_processor.process_batch(batch_id, urls)
        
        # Record end time and resources
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        # Calculate metrics
        duration = end_time - start_time
        urls_per_second = len(urls) / duration if duration > 0 else 0
        memory_increase = end_memory - start_memory
        
        # Add metrics to stats
        stats["metrics"] = {
            "duration_seconds": duration,
            "urls_per_second": urls_per_second,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_increase_mb": memory_increase,
            "memory_per_url_kb": (memory_increase * 1024 / len(urls)) if len(urls) > 0 else 0,
            "firecrawl_credits_used": crawler_service.credits_used - self.initial_credits_used,
            "real_api_calls": crawler_service.real_requests,
            "mock_api_calls": crawler_service.mock_requests,
            "real_percentage": (crawler_service.real_requests / (crawler_service.real_requests + crawler_service.mock_requests)) * 100 if (crawler_service.real_requests + crawler_service.mock_requests) > 0 else 0
        }
        
        return stats
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert to MB
    
    def log_batch_results(self, batch_size: int, stats: Dict[str, Any]):
        """Log batch processing results."""
        metrics = stats.get("metrics", {})
        
        logger.info(f"Results for batch size {batch_size}:")
        logger.info(f"  Duration: {metrics.get('duration_seconds', 0):.2f} seconds")
        logger.info(f"  URLs per second: {metrics.get('urls_per_second', 0):.2f}")
        logger.info(f"  Success rate: {stats.get('successful', 0)}/{batch_size} ({stats.get('successful', 0)/batch_size*100:.2f}%)")
        logger.info(f"  Memory usage: {metrics.get('start_memory_mb', 0):.2f}MB → {metrics.get('end_memory_mb', 0):.2f}MB (+{metrics.get('memory_increase_mb', 0):.2f}MB)")
        logger.info(f"  Memory per URL: {metrics.get('memory_per_url_kb', 0):.2f}KB")
        logger.info(f"  Firecrawl: {metrics.get('real_api_calls', 0)} real calls ({metrics.get('real_percentage', 0):.2f}%), {metrics.get('firecrawl_credits_used', 0)} credits used")
    
    def save_test_results(self, results: Dict[str, Any], run_id: str):
        """Save test results to a JSON file."""
        try:
            filename = os.path.join(RESULTS_DIR, f"batch_test_results_{run_id}.json")
            with open(filename, 'w') as file:
                json.dump(results, file, indent=2)
            
            logger.info(f"Saved test results to {filename}")
        except Exception as e:
            logger.error(f"Error saving test results: {str(e)}")
    
    def generate_recommendations(self, test_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate configuration recommendations based on test results.
        
        Args:
            test_summary: Summary of test results
            
        Returns:
            Dict with configuration recommendations
        """
        recommendations = {
            "batch_size": None,
            "concurrent_requests": None,
            "memory_setting": None,
            "cpu_setting": None,
            "explanation": ""
        }
        
        try:
            # Find optimal batch size
            optimal_batch_size = None
            max_throughput = 0
            
            for size_str, results in test_summary["results"].items():
                size = int(size_str) if isinstance(size_str, str) else size_str
                metrics = results.get("metrics", {})
                throughput = metrics.get("urls_per_second", 0)
                success_rate = results.get("successful", 0) / size if size > 0 else 0
                
                # Only consider if success rate is at least 80%
                if success_rate >= 0.8 and throughput > max_throughput:
                    max_throughput = throughput
                    optimal_batch_size = size
            
            # If we found an optimal batch size
            if optimal_batch_size:
                recommendations["batch_size"] = optimal_batch_size
                
                # Get metrics for the optimal batch size
                size_key = str(optimal_batch_size) if str(optimal_batch_size) in test_summary["results"] else optimal_batch_size
                optimal_results = test_summary["results"][size_key]
                metrics = optimal_results.get("metrics", {})
                
                # Calculate recommended concurrent requests
                memory_per_url_kb = metrics.get("memory_per_url_kb", 0)
                available_memory_mb = 1000  # Assume 1GB available memory
                
                # Calculate max concurrent URLs based on memory
                if memory_per_url_kb > 0:
                    max_concurrent = int((available_memory_mb * 1024) / memory_per_url_kb * 0.7)  # Use 70% of available memory
                    recommendations["concurrent_requests"] = min(max_concurrent, 100)  # Cap at 100
                else:
                    recommendations["concurrent_requests"] = 20  # Default fallback
                
                # Memory and CPU settings
                recommendations["memory_setting"] = "80.0"  # 80% threshold
                recommendations["cpu_setting"] = "80.0"     # 80% threshold
                
                # Generate explanation
                recommendations["explanation"] = (
                    f"Based on test results, the optimal batch size is {optimal_batch_size} URLs "
                    f"with a throughput of {max_throughput:.2f} URLs/second. "
                    f"Each URL uses approximately {memory_per_url_kb:.2f}KB of memory. "
                    f"We recommend using {recommendations['concurrent_requests']} concurrent requests "
                    f"to efficiently process URLs while staying within memory constraints. "
                    f"Set memory and CPU thresholds to 80% to ensure stable operation."
                )
            else:
                # No optimal batch size found
                recommendations["explanation"] = (
                    "No optimal batch size found with at least 80% success rate. "
                    "Consider adjusting test parameters or investigating error causes."
                )
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            recommendations["explanation"] = f"Error generating recommendations: {str(e)}"
        
        return recommendations

# Command-line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch scaling tests")
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_TEST_SIZES, 
                        help="Batch sizes to test (default: 100, 1000, 10000, 50000, 100000)")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Custom run ID for this test")
    parser.add_argument("--input", type=str, default=None,
                        help="Path to CSV file containing URLs")
    parser.add_argument("--column", type=str, default=None,
                        help="Column name in CSV containing URLs")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of URLs to process")
    parser.add_argument("--offset", type=int, default=0,
                        help="Starting index in the URL list")
    
    args = parser.parse_args()
    
    # Run the test
    test = BatchScalingTest()
    asyncio.run(test.run_test(
        batch_sizes=args.sizes, 
        run_id=args.run_id,
        input_file=args.input,
        column=args.column,
        limit=args.limit,
        offset=args.offset
    )) 