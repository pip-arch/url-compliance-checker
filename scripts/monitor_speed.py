#!/usr/bin/env python3
"""
Monitor processing speed and show improvements.
"""

import time
import os
from datetime import datetime

def monitor_speed():
    """Monitor processing speed."""
    
    log_file = "data/logs/fast_forex_processing.log"
    
    print("\n⚡ SPEED MONITOR - Fast Processing Mode")
    print("=" * 60)
    print("Optimizations applied:")
    print("- ✅ Pre-filtered dead domains (saved ~10 min)")
    print("- ✅ Timeouts: 30s → 10s")
    print("- ✅ Retries: 3 → 1")
    print("- ✅ Workers: 10 → 20")
    print("- ✅ Focus on forex/finance URLs")
    print("=" * 60)
    
    start_time = datetime.now()
    last_position = 0
    urls_processed = 0
    urls_with_mentions = 0
    llm_analyses = 0
    
    print("\nMonitoring...")
    
    while True:
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                
                for line in new_lines:
                    if "Processing batch" in line:
                        urls_processed = int(line.split('(')[1].split(' ')[0].split('-')[1])
                    
                    if "Admiral Markets mentions found" in line and "skipping" not in line:
                        urls_with_mentions += 1
                    
                    if "LLM ANALYSIS RESULT" in line:
                        llm_analyses += 1
                
                # Calculate speed
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0 and urls_processed > 0:
                    speed = urls_processed / elapsed * 60  # URLs per minute
                    
                    # Clear and update display
                    print(f"\r⏱️  Time: {int(elapsed)}s | "
                          f"📊 Processed: {urls_processed} | "
                          f"🎯 With mentions: {urls_with_mentions} | "
                          f"🤖 LLM analyses: {llm_analyses} | "
                          f"⚡ Speed: {speed:.1f} URLs/min", end='', flush=True)
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n\n✅ Final stats:")
            print(f"   - Total time: {int(elapsed)}s")
            print(f"   - URLs processed: {urls_processed}")
            print(f"   - Speed: {speed:.1f} URLs/minute")
            print(f"   - Old speed estimate: ~4 URLs/minute")
            print(f"   - Speed improvement: {speed/4:.1f}x faster!")
            break

if __name__ == "__main__":
    monitor_speed() 