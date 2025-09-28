#!/usr/bin/env python3
"""Extract all URLs from Admiral Markets CSV files for processing."""

import csv
import sys
from pathlib import Path
from collections import defaultdict

def extract_all_urls(input_files, output_file):
    """Extract all unique URLs from multiple CSV files."""
    all_urls = set()
    url_info = defaultdict(list)
    
    for input_file in input_files:
        print(f"\nProcessing {input_file}...")
        
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
                    target_url_col = None
                    
                    for i, col in enumerate(header):
                        if 'Referring page URL' in col:
                            url_col = i
                        elif 'Target URL' in col:
                            target_url_col = i
                    
                    if url_col is None:
                        # Try second column as fallback
                        url_col = 1
                    
                    # Collect all URLs
                    row_count = 0
                    for row in reader:
                        row_count += 1
                        
                        # Get referring page URL
                        if len(row) > url_col:
                            url = row[url_col].strip()
                            if url.startswith(('http://', 'https://')):
                                all_urls.add(url)
                                url_info[url].append({
                                    'source': input_file,
                                    'type': 'referring_page'
                                })
                        
                        # Also get target URL if available
                        if target_url_col is not None and len(row) > target_url_col:
                            target_url = row[target_url_col].strip()
                            if target_url.startswith(('http://', 'https://')):
                                # Skip Admiral Markets URLs as they're the target site
                                if 'admiralmarkets.com' not in target_url:
                                    all_urls.add(target_url)
                                    url_info[target_url].append({
                                        'source': input_file,
                                        'type': 'target_url'
                                    })
                    
                    print(f"  Successfully read with {encoding} encoding")
                    print(f"  Processed {row_count} rows")
                    print(f"  Total unique URLs so far: {len(all_urls)}")
                    break
                    
            except Exception as e:
                print(f"  Failed with {encoding}: {e}")
                continue
    
    if not all_urls:
        print("\nNo URLs found!")
        return
    
    # Convert to list and sort
    url_list = sorted(list(all_urls))
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("url\n")  # Header
        for url in url_list:
            f.write(f"{url}\n")
    
    print(f"\n=== EXTRACTION COMPLETE ===")
    print(f"Total unique URLs extracted: {len(url_list)}")
    print(f"Output file: {output_file}")
    
    # Print some statistics
    print(f"\nURL Statistics:")
    domain_counts = defaultdict(int)
    for url in url_list:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            domain_counts[domain] += 1
        except:
            pass
    
    # Show top 10 domains
    print(f"\nTop 10 domains by URL count:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {domain}: {count} URLs")
    
    return len(url_list)

if __name__ == "__main__":
    input_files = [
        "data/tmp/admiralmarkets.com-backlinks-subdomains_2025-04-16_13-31-57.csv",
        "data/tmp/admiralmarkets.com-backlinks-subdomains_2025-04-16_13-30-28.csv"
    ]
    output_file = "data/test_files/all_admiral_urls.csv"
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    extract_all_urls(input_files, output_file) 