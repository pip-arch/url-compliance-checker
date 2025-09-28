#!/usr/bin/env python3
"""
Clean restart of Admiral Markets processing with 50 workers.
Includes progress tracking and better error handling.
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

# Problematic domains to skip
SKIP_DOMAINS = {
    'tol.vpo.si',  # DNS resolution errors
    'mindmaps.innovationeye.com',  # SSL issues
    'wp.avtomatiz.ru',  # Lots of 404 errors
}

print("🚀 Admiral Markets Clean Processing - 50 Workers")
print("=" * 60)
print(f"📊 Starting fresh at: {datetime.now()}")
print(f"📈 Current blacklist: 987 entries")
print(f"⚙️  Workers: 50")
print(f"🚫 Skipping domains: {', '.join(SKIP_DOMAINS)}")
print()

# Create a filtered URL file
print("Step 1: Creating filtered URL list...")
filtered_file = "data/tmp/admiral_filtered_clean.csv"

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
os.environ['QA_ENABLED'] = 'false'  # Avoid true_positives error
os.environ['MAX_RETRIES'] = '1'
os.environ['RETRY_DELAY'] = '1'
os.environ['FIRECRAWL_TIMEOUT'] = '10'
os.environ['CRAWL4AI_TIMEOUT'] = '10000'
os.environ['FORCE_RECRAWL'] = 'False'  # Don't recrawl already processed URLs

# Create a unique log file
log_file = f"data/logs/admiral_clean_50workers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

print(f"Step 2: Starting processing with 50 workers...")
print(f"📝 Log file: {log_file}")
print()

cmd = [
    "python", "scripts/run_improved_process_postgres.py",
    "--file", filtered_file,
    "--column", "url",
    "--batch-size", "250",  # Balanced batch size
    "--workers", "50"
]

print(f"Command: {' '.join(cmd)}")
print("-" * 60)
print()

try:
    # Run with real-time output to both console and log
    with open(log_file, 'w') as log:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
            log.write(line)
            log.flush()
        
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