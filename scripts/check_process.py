#!/usr/bin/env python3
"""
Script to check if the URL processing is creating output files
"""
import os
import time
from datetime import datetime

def check_output_files():
    """Check the data directories for recent files"""
    
    # Directories to check
    dirs_to_check = [
        "data/batch_state",
        "data/exports", 
        "data/tmp",
        "data/test_results"
    ]
    
    print(f"\nChecking for processing activity at {datetime.now()}\n")
    
    # Check each directory for recent files
    for dir_path in dirs_to_check:
        if not os.path.exists(dir_path):
            print(f"Directory {dir_path} does not exist")
            continue
            
        print(f"Files in {dir_path}:")
        
        # Get file stats
        files = []
        for filename in os.listdir(dir_path):
            if os.path.isfile(os.path.join(dir_path, filename)):
                file_path = os.path.join(dir_path, filename)
                mod_time = os.path.getmtime(file_path)
                size = os.path.getsize(file_path)
                files.append((filename, mod_time, size))
        
        # Sort by modification time, newest first
        files.sort(key=lambda x: x[1], reverse=True)
        
        # Display files
        if not files:
            print("  No files found")
        else:
            for i, (filename, mod_time, size) in enumerate(files[:5]):  # Show only 5 most recent
                mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
                size_kb = size / 1024
                print(f"  {filename}: {size_kb:.2f} KB, modified {mod_time_str}")
            
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more files")
                
        print()
    
    # Also check for log files with recent edits
    log_files = ["server.log", "firecrawl_debug.log"]
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            mod_time = os.path.getmtime(log_file)
            mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
            size_mb = size / (1024 * 1024)
            print(f"{log_file}: {size_mb:.2f} MB, last modified {mod_time_str}")
            
            # Check if the file is actively being written to
            print(f"Last few lines of {log_file}:")
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:  # Last 5 lines
                        print(f"  {line.strip()}")
            except Exception as e:
                print(f"  Error reading file: {e}")

if __name__ == "__main__":
    check_output_files() 