#!/usr/bin/env python3
"""
Optimized fast processing script with reduced timeouts and better parallelism.
"""

import asyncio
import sys
import os
import pandas as pd
import aiohttp
from urllib.parse import urlparse
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_domain_health(session, url, timeout=3):
    """Quick health check for a domain."""
    try:
        domain = urlparse(url).netloc
        check_url = f"http://{domain}"
        
        async with session.head(check_url, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True) as response:
            return response.status < 500
    except:
        # Try HTTPS
        try:
            check_url = f"https://{domain}"
            async with session.head(check_url, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True) as response:
                return response.status < 500
        except:
            return False

async def prefilter_urls(urls, max_workers=50):
    """Pre-filter URLs by checking domain health."""
    logger.info(f"🚀 Pre-filtering {len(urls)} URLs for domain health...")
    
    healthy_urls = []
    dead_urls = []
    
    async with aiohttp.ClientSession() as session:
        # Process in batches
        batch_size = max_workers
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            tasks = [check_domain_health(session, url) for url in batch]
            results = await asyncio.gather(*tasks)
            
            for url, is_healthy in zip(batch, results):
                if is_healthy:
                    healthy_urls.append(url)
                else:
                    dead_urls.append(url)
            
            logger.info(f"  Checked {min(i+batch_size, len(urls))}/{len(urls)} - Healthy: {len(healthy_urls)}, Dead: {len(dead_urls)}")
    
    return healthy_urls, dead_urls

def optimize_crawl_settings():
    """Optimize crawler settings for speed."""
    # Reduce timeouts
    os.environ['FIRECRAWL_TIMEOUT'] = '10'  # 10 seconds instead of 30
    os.environ['CRAWL4AI_TIMEOUT'] = '10'
    os.environ['CRAWLER_TIMEOUT'] = '10'
    
    # Reduce retries
    os.environ['MAX_RETRIES'] = '1'  # Only 1 retry instead of 3
    os.environ['RETRY_DELAY'] = '1'  # 1 second delay instead of exponential
    
    # Skip certain checks
    os.environ['SKIP_SSL_VERIFY'] = 'true'
    os.environ['FAST_MODE'] = 'true'

async def run_fast_processing():
    """Run optimized processing."""
    
    # Optimize settings
    optimize_crawl_settings()
    
    # Read URLs
    csv_file = "data/inputs/admiral_markets/referring_urls.csv"
    df = pd.read_csv(csv_file)
    all_urls = df['url'].tolist()[:500]  # Process 500 for speed test
    
    logger.info(f"\n{'='*60}")
    logger.info(f"⚡ FAST PROCESSING MODE - {len(all_urls)} URLs")
    logger.info(f"{'='*60}\n")
    
    # Pre-filter URLs
    start_time = datetime.now()
    healthy_urls, dead_urls = await prefilter_urls(all_urls, max_workers=100)
    filter_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"\n✅ Pre-filtering complete in {filter_time:.1f}s")
    logger.info(f"   Healthy domains: {len(healthy_urls)} ({len(healthy_urls)/len(all_urls)*100:.1f}%)")
    logger.info(f"   Dead domains: {len(dead_urls)} ({len(dead_urls)/len(all_urls)*100:.1f}%)")
    
    # Save dead URLs to skip file
    if dead_urls:
        dead_df = pd.DataFrame({'url': dead_urls, 'reason': 'DOMAIN_DEAD'})
        dead_df.to_csv('data/tmp/dead_domains.csv', index=False)
        logger.info(f"   Saved {len(dead_urls)} dead URLs to data/tmp/dead_domains.csv")
    
    # Save healthy URLs for processing
    if healthy_urls:
        healthy_df = pd.DataFrame({'url': healthy_urls})
        healthy_df.to_csv('data/tmp/healthy_urls.csv', index=False)
        logger.info(f"   Saved {len(healthy_urls)} healthy URLs for processing")
        
        # Now run the main processor on healthy URLs only
        logger.info(f"\n🚀 Starting main processing on {len(healthy_urls)} healthy URLs...")
        
        cmd = f"""python scripts/run_improved_process_postgres.py \\
            --file data/tmp/healthy_urls.csv \\
            --column url \\
            --batch-size 50 \\
            --workers 20"""
        
        logger.info(f"\nRun this command to process healthy URLs:")
        logger.info(cmd)
        
        # Also create a focused list of forex/finance URLs
        forex_urls = [url for url in healthy_urls if any(
            keyword in url.lower() 
            for keyword in ['forex', 'trading', 'finance', 'invest', 'broker', 'market']
        )]
        
        if forex_urls:
            forex_df = pd.DataFrame({'url': forex_urls})
            forex_df.to_csv('data/tmp/forex_focused_urls.csv', index=False)
            logger.info(f"\n🎯 Found {len(forex_urls)} forex/finance URLs (most likely to mention Admiral Markets)")
            logger.info(f"   Saved to data/tmp/forex_focused_urls.csv")

if __name__ == "__main__":
    asyncio.run(run_fast_processing()) 