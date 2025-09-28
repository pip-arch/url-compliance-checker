#!/usr/bin/env python3
"""
Resume Admiral Markets processing with extended skip list v3.
Adds more problematic domains found during processing.
"""
import subprocess
import sys
import os
from datetime import datetime
import signal

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print('\n\n⚠️ Processing interrupted by user')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Extended problematic domains to skip (v3)
SKIP_DOMAINS = {
    'tol.vpo.si',  # DNS resolution errors
    'mindmaps.innovationeye.com',  # SSL issues
    'wp.avtomatiz.ru',  # Lots of 404 errors
    'test-omeldonia.host-ware.com',  # Connection timeouts
    'merchantshares.com',  # 522 errors, redirects to lietaer.com
    'guitarsxs.com',  # Connection timeouts
    'taniabertaldi.com',  # DNS resolution errors (NEW)
    'floribertoinsurance.com',  # DNS resolution errors (NEW)
}

print("🔄 RESUMING Admiral Markets Processing - 50 Workers (v3)")
print("=" * 60)
print(f"📊 Resuming at: {datetime.now()}")
print(f"📈 Current blacklist: 1,322+ entries")
print(f"🔍 Already found: 391+ URLs with Admiral mentions")
print(f"⚙️  Workers: 50")
print(f"🚫 Skipping domains: {', '.join(sorted(SKIP_DOMAINS))}")
print()
print("✨ NEW: Added taniabertaldi.com and floribertoinsurance.com to skip list")
print("🐛 FIX: Fixed Crawl4AI browser_args parameter issue")
print()

# Create a filtered URL file
print("Step 1: Creating filtered URL list...")
filtered_file = "data/tmp/admiral_filtered_resume_v3.csv"

with open("data/inputs/admiral_markets/referring_urls.csv", 'r') as infile:
    with open(filtered_file, 'w') as outfile:
        header = infile.readline()
        outfile.write(header)
        
        skipped = 0
        kept = 0
        
        for line in infile:
            skip = False
            for domain in SKIP_DOMAINS:
                if domain in line:
                    skip = True
                    skipped += 1
                    break
            
            if not skip:
                outfile.write(line)
                kept += 1

print(f"✅ Filtered URL list created: {filtered_file}")
print(f"   - Kept: {kept:,} URLs")
print(f"   - Skipped: {skipped} problematic URLs")
print()

# Set optimized environment variables
os.environ['QA_ENABLED'] = 'false'
os.environ['MAX_RETRIES'] = '1'
os.environ['RETRY_DELAY'] = '1'
os.environ['FIRECRAWL_TIMEOUT'] = '10'
os.environ['CRAWL4AI_TIMEOUT'] = '10000'
os.environ['FORCE_RECRAWL'] = 'False'

# Create a unique log file
log_file = f"data/logs/admiral_resume_50workers_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

print(f"Step 2: Resuming processing with 50 workers...")
print(f"📝 Log file: {log_file}")
print()
print("ℹ️  Already-processed URLs will be quickly skipped via Pinecone")
print("ℹ️  Progress will be shown every 25 URLs processed")
print()

cmd = [
    "python", "scripts/run_improved_process_postgres.py",
    "--file", filtered_file,
    "--column", "url",
    "--batch-size", "250",
    "--workers", "50"
]

print(f"Command: {' '.join(cmd)}")
print("-" * 60)
print()

try:
    with open(log_file, 'w') as log:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        urls_processed = 0
        admiral_found = 0
        blacklisted = 0
        errors = 0
        
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
            log.write(line)
            log.flush()
            
            # Track progress
            if "already processed" in line:
                urls_processed += 1
            elif "Admiral Markets mentions found" in line:
                admiral_found += 1
            elif "blacklist_report" in line:
                blacklisted += 1
            elif "ERROR" in line or "All.*attempts failed" in line:
                errors += 1
            
            # Show progress every 25 URLs
            if urls_processed > 0 and urls_processed % 25 == 0:
                print(f"\n📊 Progress: {urls_processed} URLs checked, {admiral_found} with Admiral mentions, {blacklisted} blacklisted, {errors} errors\n")
        
        process.wait()
        
        if process.returncode == 0:
            print("\n✅ Processing completed successfully!")
        else:
            print(f"\n⚠️ Processing exited with code: {process.returncode}")
            
except KeyboardInterrupt:
    print("\n\n⚠️ Processing interrupted by user")
    if 'process' in locals():
        process.terminate()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)

print(f"\n📊 Check the log file for details: {log_file}")
print(f"📈 Check blacklist growth: wc -l data/tmp/blacklist_consolidated.csv")
print(f"🔍 Final stats: {urls_processed} URLs checked, {admiral_found} with Admiral mentions, {blacklisted} blacklisted, {errors} errors") 