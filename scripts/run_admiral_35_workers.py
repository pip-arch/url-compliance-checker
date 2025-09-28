#!/usr/bin/env python3
"""
Run Admiral Markets full batch with 35 workers
"""
import subprocess
import sys
import os
from datetime import datetime

print("🚀 Admiral Markets Full Batch Processing")
print("=" * 50)
print(f"📊 Dataset: 67,693 URLs")
print(f"⚙️  Workers: 35")
print(f"📦 Batch size: 250")
print(f"🕐 Started: {datetime.now()}")
print()

# First run the pre-filtering
print("Step 1: Pre-filtering dead domains...")
pre_filter_cmd = [
    "python", "scripts/run_optimized_batch.py",
    "data/inputs/admiral_markets/referring_urls.txt",
    "67693"
]

# This will create data/tmp/filtered_urls.csv
result = subprocess.run(pre_filter_cmd)

if result.returncode != 0:
    print("❌ Pre-filtering failed!")
    sys.exit(1)

print("\n✅ Pre-filtering complete!")
print("\nStep 2: Processing with 35 workers...")

# Now run the main processing with custom settings
main_cmd = [
    "python", "scripts/run_improved_process_postgres.py",
    "--file", "data/tmp/filtered_urls.csv",
    "--column", "url",
    "--batch-size", "250",
    "--workers", "35"
]

print(f"\nRunning: {' '.join(main_cmd)}")
print("\n" + "=" * 50)

# Run with real-time output
subprocess.run(main_cmd) 