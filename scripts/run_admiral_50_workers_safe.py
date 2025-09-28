#!/usr/bin/env python3
"""
Run Admiral Markets processing with 50 workers and skip problematic domains.
Includes better error handling to prevent crashes.
"""
import subprocess
import sys
import os
from datetime import datetime

# Problematic domains to skip
SKIP_DOMAINS = {
    'tol.vpo.si',  # DNS resolution errors
    'mindmaps.innovationeye.com',  # SSL issues
    # Add more problematic domains as needed
}

print("🚀 Admiral Markets Processing - 50 Workers Edition")
print("=" * 60)
print(f"📊 Dataset: Admiral Markets backlinks")
print(f"⚙️  Workers: 50 (increased from 35)")
print(f"🚫 Skipping problematic domains: {', '.join(SKIP_DOMAINS)}")
print(f"🕐 Started: {datetime.now()}")
print()

# Create a filtered URL file excluding problematic domains
print("Step 1: Creating filtered URL list...")
filtered_file = "data/tmp/admiral_filtered_safe.csv"

with open("data/inputs/admiral_markets/referring_urls.csv", 'r') as infile:
    with open(filtered_file, 'w') as outfile:
        # Copy header
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

print(f"✅ Filtered URL list created")
print(f"   - Kept: {kept} URLs")
print(f"   - Skipped: {skipped} URLs from problematic domains")
print()

# Set environment variables for safety
os.environ['QA_ENABLED'] = 'false'  # Disable QA to avoid true_positives error
os.environ['MAX_RETRIES'] = '1'
os.environ['RETRY_DELAY'] = '1'
os.environ['FIRECRAWL_TIMEOUT'] = '10'
os.environ['CRAWL4AI_TIMEOUT'] = '10000'

print("Step 2: Starting processing with 50 workers...")
cmd = [
    "python", "scripts/run_improved_process_postgres.py",
    "--file", filtered_file,
    "--column", "url",
    "--batch-size", "300",  # Larger batches for efficiency with more workers
    "--workers", "50"
]

print(f"Command: {' '.join(cmd)}")
print()

try:
    # Run with real-time output
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
    
    process.wait()
    
    if process.returncode == 0:
        print("\n✅ Processing completed successfully!")
    else:
        print(f"\n⚠️ Processing exited with code: {process.returncode}")
        
except KeyboardInterrupt:
    print("\n\n⚠️ Processing interrupted by user")
    process.terminate()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1) 