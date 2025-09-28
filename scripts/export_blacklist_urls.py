#!/usr/bin/env python3
"""
Script to export only the URLs (first column) from the consolidated blacklist file
"""
import csv
import os
from datetime import datetime

# Path to the consolidated blacklist file
CONSOLIDATED_FILE = "./data/tmp/blacklist_consolidated.csv"

# Create output directory if it doesn't exist
os.makedirs("./data/exports", exist_ok=True)

# Output file with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"./data/exports/blacklist_urls_only_{timestamp}.csv"

def export_urls_only():
    """Export only the URLs column from the consolidated blacklist"""
    print(f"Exporting URLs from {CONSOLIDATED_FILE} to {OUTPUT_FILE}")
    
    urls = []
    
    # Read the consolidated file
    try:
        with open(CONSOLIDATED_FILE, "r", newline="") as infile:
            reader = csv.reader(infile)
            # Skip header
            header = next(reader)
            
            # Extract only the first column (URLs)
            for row in reader:
                if row and len(row) > 0:
                    urls.append(row[0])
        
        # Write URLs to output file
        with open(OUTPUT_FILE, "w", newline="") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["URL"])  # Header
            
            for url in urls:
                writer.writerow([url])
        
        print(f"Successfully exported {len(urls)} URLs to {OUTPUT_FILE}")
        return OUTPUT_FILE
    
    except FileNotFoundError:
        print(f"Error: Could not find consolidated blacklist file at {CONSOLIDATED_FILE}")
        return None
    except Exception as e:
        print(f"Error exporting URLs: {str(e)}")
        return None

if __name__ == "__main__":
    export_urls_only() 