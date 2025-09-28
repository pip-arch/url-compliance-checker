#!/usr/bin/env python3
"""
Quick status check for URL processing.
"""

import subprocess
import os
import pandas as pd
from datetime import datetime

def quick_status():
    """Show quick processing status."""
    
    print("\n🚀 URL PROCESSING STATUS")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if process is running
    result = subprocess.run(['pgrep', '-f', 'run_improved_process_postgres.py'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("\n✅ Status: PROCESSING ACTIVE")
    else:
        print("\n⚠️  Status: NOT RUNNING")
    
    # Check blacklist
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    if os.path.exists(blacklist_file):
        try:
            df = pd.read_csv(blacklist_file, on_bad_lines='skip')
            print(f"\n📊 Blacklist Stats:")
            print(f"   Total URLs: {len(df)}")
            print(f"   Unique domains: {df['Main Domain'].nunique()}")
        except:
            with open(blacklist_file, 'r') as f:
                lines = sum(1 for line in f) - 1
            print(f"\n📊 Blacklist URLs: ~{lines}")
    
    # Recent log activity
    log_file = "data/logs/processing_test_100.log"
    if os.path.exists(log_file):
        print("\n📜 Recent Activity:")
        
        # Count successes and failures
        result = subprocess.run(['tail', '-100', log_file], 
                              capture_output=True, text=True)
        if result.stdout:
            lines = result.stdout.split('\n')
            
            firecrawl_success = sum(1 for l in lines if 'Firecrawl request successful' in l)
            crawl4ai_success = sum(1 for l in lines if 'Successfully crawled' in l and 'Crawl4AI' in l)
            errors = sum(1 for l in lines if 'ERROR' in l)
            mentions = sum(1 for l in lines if 'Admiral Markets mentions found' in l)
            
            print(f"   Firecrawl successes: {firecrawl_success}")
            print(f"   Crawl4AI successes: {crawl4ai_success}")
            print(f"   Total errors: {errors}")
            print(f"   Admiral mentions found: {mentions}")
    
    # Last few log lines
    print("\n📋 Last 5 Events:")
    result = subprocess.run(['tail', '-5', log_file], 
                          capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if line:
                print(f"   {line[:80]}...")
    
    print("\n" + "=" * 60)
    print("💡 Run 'python scripts/generate_summary_report.py' for full details")

if __name__ == "__main__":
    quick_status() 