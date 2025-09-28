#!/usr/bin/env python3
"""
Monitor LLM analysis activity in real-time.
"""

import subprocess
import time
import os
from datetime import datetime

def monitor_llm():
    """Monitor for LLM analysis activity."""
    
    print("\n🤖 LLM ANALYSIS MONITOR")
    print("=" * 60)
    print("Watching for LLM compliance analysis...\n")
    
    log_file = "data/logs/production_test_200.log"
    last_position = 0
    
    while True:
        try:
            if os.path.exists(log_file):
                # Read new log entries
                with open(log_file, 'r') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                
                # Look for LLM analysis activity
                for line in new_lines:
                    if "Admiral Markets mentions found on" in line and "skipping analysis" not in line:
                        print(f"\n🎯 {datetime.now().strftime('%H:%M:%S')} - Found URL with Admiral mentions!")
                        print(f"   {line.strip()}")
                    
                    elif "LLM ANALYSIS RESULT" in line:
                        print(f"\n✨ {datetime.now().strftime('%H:%M:%S')} - LLM ANALYSIS TRIGGERED!")
                        print(f"   {line.strip()}")
                    
                    elif "Model:" in line and "llama" in line:
                        print(f"   🤖 {line.strip()}")
                    
                    elif "Category:" in line and ("blacklist" in line or "whitelist" in line or "review" in line):
                        print(f"   📊 {line.strip()}")
                    
                    elif "Confidence:" in line and "." in line:
                        print(f"   💯 {line.strip()}")
                    
                    elif "Explanation:" in line and len(line) > 50:
                        print(f"   💬 {line.strip()[:100]}...")
                    
                    elif "FINAL CATEGORIZATION" in line:
                        print(f"\n🏁 {datetime.now().strftime('%H:%M:%S')} - Decision made!")
                    
                    elif "blacklisted" in line.lower() and "http" in line:
                        print(f"   🚫 BLACKLISTED: {line.strip()[:80]}...")
                    
                    elif "whitelisted" in line.lower() and "http" in line:
                        print(f"   ✅ WHITELISTED: {line.strip()[:80]}...")
            
            time.sleep(1)  # Check every second
            
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    monitor_llm() 