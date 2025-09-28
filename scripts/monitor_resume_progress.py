#!/usr/bin/env python3
"""
Monitor the progress of resumed Admiral Markets processing.
"""
import time
import subprocess
import os
from datetime import datetime

def get_latest_log():
    """Find the most recent admiral resume log file."""
    log_dir = "data/logs"
    log_files = [f for f in os.listdir(log_dir) if f.startswith("admiral_resume_50workers_v3_")]
    if not log_files:
        return None
    latest = max(log_files, key=lambda x: os.path.getctime(os.path.join(log_dir, x)))
    return os.path.join(log_dir, latest)

def count_blacklist_entries():
    """Count current blacklist entries."""
    try:
        with open("data/tmp/blacklist_consolidated.csv", 'r') as f:
            return sum(1 for line in f) - 1  # Subtract header
    except:
        return 0

def get_process_stats(log_file):
    """Extract processing statistics from log file."""
    if not log_file or not os.path.exists(log_file):
        return {}
    
    try:
        # Get last 100 lines for recent activity
        result = subprocess.run(['tail', '-100', log_file], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        stats = {
            'urls_processed': 0,
            'already_processed': 0,
            'admiral_found': 0,
            'blacklisted': 0,
            'errors': 0,
            'last_activity': None
        }
        
        for line in lines:
            if "already processed" in line:
                stats['already_processed'] += 1
            elif "Admiral Markets mentions found" in line:
                stats['admiral_found'] += 1
            elif "blacklist_report" in line:
                stats['blacklisted'] += 1
            elif "ERROR" in line or "failed" in line.lower():
                stats['errors'] += 1
            
            # Extract timestamp from recent lines
            if line.strip() and any(x in line for x in ['INFO:', 'ERROR:', 'WARNING:']):
                stats['last_activity'] = line[:19] if len(line) > 19 else None
        
        stats['urls_processed'] = stats['already_processed'] + stats['admiral_found']
        return stats
        
    except Exception as e:
        print(f"Error reading log: {e}")
        return {}

def main():
    print("🔄 ADMIRAL MARKETS PROCESSING MONITOR")
    print("=" * 50)
    
    log_file = get_latest_log()
    if not log_file:
        print("❌ No resume log file found!")
        return
    
    print(f"📝 Monitoring: {log_file}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        while True:
            stats = get_process_stats(log_file)
            blacklist_count = count_blacklist_entries()
            
            print(f"\r📊 Progress: {stats.get('urls_processed', 0)} URLs | "
                  f"⚡ Skipped: {stats.get('already_processed', 0)} | "
                  f"🎯 Admiral: {stats.get('admiral_found', 0)} | "
                  f"🚫 Blacklist: {blacklist_count} | "
                  f"❌ Errors: {stats.get('errors', 0)} | "
                  f"🕐 {datetime.now().strftime('%H:%M:%S')}", end='', flush=True)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")

if __name__ == "__main__":
    main() 