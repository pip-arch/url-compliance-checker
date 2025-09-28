#!/usr/bin/env python3
"""
Convert referring_urls.txt to CSV format for processing.
"""

import pandas as pd
import sys

def convert_txt_to_csv():
    """Convert text file with one URL per line to CSV format."""
    
    input_file = "data/inputs/admiral_markets/referring_urls.txt"
    output_file = "data/inputs/admiral_markets/referring_urls.csv"
    
    print(f"Converting {input_file} to CSV format...")
    
    # Read URLs from text file
    urls = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if url:  # Skip empty lines
                urls.append(url)
    
    print(f"Found {len(urls)} URLs")
    
    # Create DataFrame and save as CSV
    df = pd.DataFrame({'url': urls})
    df.to_csv(output_file, index=False)
    
    print(f"✅ Saved {len(urls)} URLs to {output_file}")
    
    # Show sample
    print("\nFirst 5 URLs:")
    for url in urls[:5]:
        print(f"  - {url}")

if __name__ == "__main__":
    convert_txt_to_csv() 