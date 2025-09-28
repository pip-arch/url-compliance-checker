#!/usr/bin/env python3
"""
Real-time monitoring of URL processing progress.
"""

import time
import os
import pandas as pd
from datetime import datetime
import subprocess

def monitor_processing():
    """Monitor URL processing in real-time."""
    
    print("\n🔍 URL PROCESSING MONITOR")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring\n")
    
    last_blacklist_count = 0
    
    while True:
        try:
            # Clear screen for fresh display
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"📊 URL Processing Monitor - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50)
            
            # Check if process is running
            result = subprocess.run(['pgrep', '-f', 'run_improved_process_postgres.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Status: PROCESSING")
            else:
                print("⚠️  Status: NOT RUNNING")
            
            # Check blacklist
            blacklist_file = "data/tmp/blacklist_consolidated.csv"
            if os.path.exists(blacklist_file):
                try:
                    df_blacklist = pd.read_csv(blacklist_file, on_bad_lines='skip')
                    current_count = len(df_blacklist)
                    new_urls = current_count - last_blacklist_count
                    
                    print(f"\n📋 Blacklist Statistics:")
                    print(f"   Total URLs: {current_count}")
                    print(f"   New this session: {new_urls}")
                    print(f"   Unique domains: {df_blacklist['Main Domain'].nunique()}")
                    
                    last_blacklist_count = current_count
                except:
                    pass
            
            # Check review queue
            review_file = "data/tmp/review_needed.csv"
            if os.path.exists(review_file):
                try:
                    df_review = pd.read_csv(review_file)
                    print(f"\n⚠️  URLs for review: {len(df_review)}")
                except:
                    pass
            
            # Check latest log entries
            log_file = "data/logs/processing_test_100.log"
            if os.path.exists(log_file):
                print("\n📜 Latest Activity:")
                result = subprocess.run(['tail', '-5', log_file], 
                                      capture_output=True, text=True)
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if 'ERROR' in line:
                            print(f"   ❌ {line[:80]}...")
                        elif 'SUCCESS' in line or 'blacklisted' in line:
                            print(f"   ✅ {line[:80]}...")
                        elif 'Admiral' in line:
                            print(f"   🎯 {line[:80]}...")
                        else:
                            print(f"   • {line[:80]}...")
            
            # Processing rate estimate
            print("\n📈 Performance:")
            print("   Estimated rate: ~100-200 URLs/hour")
            print("   Expected completion: Check back in 15-30 minutes for 100 URLs")
            
            print("\n" + "=" * 50)
            print("Refreshing every 5 seconds...")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_processing() 