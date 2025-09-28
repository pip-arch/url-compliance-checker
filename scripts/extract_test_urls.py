#!/usr/bin/env python3
"""Extract 100 random URLs from Admiral Markets CSV file for testing."""

import csv
import random
import sys
from pathlib import Path

def extract_random_urls(input_file, output_file, sample_size=100):
    """Extract random URLs from CSV file."""
    urls = []
    
    # Try different encodings
    encodings = ['utf-16', 'utf-16-le', 'utf-16-be', 'utf-8', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(input_file, 'r', encoding=encoding) as f:
                # Try tab-delimited first
                reader = csv.reader(f, delimiter='\t')
                header = next(reader, None)
                
                if not header:
                    continue
                
                # Find URL column (usually "Referring page URL")
                url_col = None
                for i, col in enumerate(header):
                    if 'URL' in col and 'Referring' in col:
                        url_col = i
                        break
                
                if url_col is None:
                    # Try second column as fallback
                    url_col = 1
                
                # Collect all URLs
                for row in reader:
                    if len(row) > url_col:
                        url = row[url_col].strip()
                        if url.startswith(('http://', 'https://')):
                            urls.append(url)
                
                print(f"Successfully read file with {encoding} encoding")
                print(f"Found {len(urls)} URLs")
                break
                
        except Exception as e:
            print(f"Failed with {encoding}: {e}")
            continue
    
    if not urls:
        print("No URLs found!")
        return
    
    # Sample random URLs
    sample = random.sample(urls, min(sample_size, len(urls)))
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("url\n")  # Header
        for url in sample:
            f.write(f"{url}\n")
    
    print(f"Wrote {len(sample)} random URLs to {output_file}")

if __name__ == "__main__":
    input_file = "data/tmp/admiralmarkets.com-backlinks-subdomains_2025-04-16_13-31-57.csv"
    output_file = "data/test_files/test_100_urls.csv"
    
    extract_random_urls(input_file, output_file) 