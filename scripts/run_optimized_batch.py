#!/usr/bin/env python3
"""
Optimized batch processing with smart pre-filtering.
Removes dead domains but keeps already processed URLs (they're fast).
ONLY filters technical issues - NO content decisions.
"""

import asyncio
import sys
import os
import pandas as pd
import aiohttp
from urllib.parse import urlparse
import logging
from datetime import datetime
import json
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Known problematic domains from previous runs
KNOWN_DEAD_DOMAINS = {
    'taniabertaldi.com',
    'guitarsxs.com',
    's.sfhpurple.com',
    # Add more as discovered
}

async def check_domain_health(session, url, timeout=2):
    """Ultra-fast domain health check - TECHNICAL ONLY."""
    try:
        domain = urlparse(url).netloc
        
        # Skip known dead domains immediately
        if domain in KNOWN_DEAD_DOMAINS:
            return False, "known_dead"
            
        # Quick DNS/connectivity check only
        check_url = f"http://{domain}"
        
        async with session.head(
            check_url, 
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=False,
            ssl=False
        ) as response:
            return True, "healthy"
            
    except aiohttp.ClientConnectorError:
        return False, "dns_error"
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception:
        return False, "other_error"

async def pre_filter_urls(urls, max_concurrent=50):
    """Pre-filter URLs to remove ONLY dead domains - no content filtering."""
    print(f"\n⚡ PRE-FILTERING {len(urls)} URLs (dead domains only)...")
    print("=" * 60)
    
    healthy_urls = []
    dead_domains = set()
    domain_status = {}
    
    async with aiohttp.ClientSession() as session:
        # Process in batches
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            tasks = []
            
            for url in batch:
                domain = urlparse(url).netloc
                
                # Cache domain status
                if domain in domain_status:
                    if domain_status[domain]:
                        healthy_urls.append(url)
                    continue
                
                tasks.append(check_domain_health(session, url))
            
            # Check batch health
            results = await asyncio.gather(*tasks)
            
            for url, (is_healthy, reason) in zip(batch, results):
                domain = urlparse(url).netloc
                domain_status[domain] = is_healthy
                
                if is_healthy:
                    healthy_urls.append(url)
                else:
                    dead_domains.add((domain, reason))
            
            # Progress update
            if (i + len(batch)) % 500 == 0:
                print(f"  Checked {i + len(batch):,} URLs...")
    
    # Save dead domains for future reference
    if dead_domains:
        with open("data/tmp/dead_domains.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "domains": [{"domain": d, "reason": r} for d, r in dead_domains]
            }, f, indent=2)
    
    print(f"\n✅ Pre-filtering complete:")
    print(f"  - Healthy URLs: {len(healthy_urls):,} ({len(healthy_urls)/len(urls)*100:.1f}%)")
    print(f"  - Dead domains removed: {len(dead_domains):,}")
    print(f"  - Time saved: ~{len(dead_domains) * 74:,} seconds")
    print(f"\n📌 Note: Keeping ALL healthy URLs regardless of content")
    
    return healthy_urls

def apply_crawler_optimizations():
    """Apply speed optimizations to crawler settings."""
    print("\n⚙️  Applying crawler optimizations...")
    
    # Update environment variables
    os.environ['FIRECRAWL_TIMEOUT'] = '10'
    os.environ['CRAWL4AI_TIMEOUT'] = '10000'
    os.environ['MAX_RETRIES'] = '1'
    os.environ['RETRY_DELAY'] = '1'
    
    print("  ✅ Timeouts: 30s → 10s")
    print("  ✅ Retries: 3 → 1")
    print("  ✅ Retry delays minimized")

async def main():
    """Run optimized batch processing."""
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_optimized_batch.py <csv_file> [limit]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found")
        sys.exit(1)
    
    print(f"\n🚀 OPTIMIZED BATCH PROCESSING")
    print(f"=" * 60)
    print(f"Input file: {input_file}")
    
    # Load URLs
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
        urls = df['url'].tolist()
    else:
        with open(input_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    
    if limit:
        urls = urls[:limit]
        print(f"Limited to: {limit} URLs")
    
    print(f"Total URLs: {len(urls):,}")
    
    # Apply optimizations
    apply_crawler_optimizations()
    
    # Pre-filter ONLY dead domains
    start_time = datetime.now()
    healthy_urls = await pre_filter_urls(urls)
    filter_time = (datetime.now() - start_time).total_seconds()
    
    print(f"\n⏱️  Pre-filtering took: {filter_time:.1f} seconds")
    print(f"📊 URLs to process: {len(healthy_urls):,}")
    
    # Save filtered URLs
    output_file = "data/tmp/filtered_urls.csv"
    pd.DataFrame({'url': healthy_urls}).to_csv(output_file, index=False)
    print(f"💾 Saved to: {output_file}")
    
    # Run the main processing with optimized settings
    print(f"\n🏃 Starting main processing...")
    print(f"   Processing ALL {len(healthy_urls):,} healthy URLs")
    print(f"   Expected time: ~{len(healthy_urls) * 2:.0f} seconds")
    print(f"   (vs ~{len(urls) * 10:.0f} seconds without optimization)")
    
    cmd = [
        "python", "scripts/run_improved_process_postgres.py",
        "--file", output_file,
        "--column", "url",
        "--batch-size", "100",
        "--workers", "20"
    ]
    
    # Add log file
    log_file = f"data/logs/optimized_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    print(f"\n📝 Logging to: {log_file}")
    print(f"\n{'='*60}")
    print("Starting processing...\n")
    
    # Run with real-time output
    with open(log_file, 'w') as log:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in process.stdout:
            print(line, end='')
            log.write(line)
            log.flush()
        
        process.wait()
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Check results: python scripts/generate_summary_report.py")

if __name__ == "__main__":
    asyncio.run(main()) 