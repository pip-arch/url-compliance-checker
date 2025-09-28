#!/usr/bin/env python3
"""Extract external URLs from Admiral Markets CSV files."""
import csv
import codecs
from urllib.parse import urlparse
from collections import Counter

def extract_external_urls(file_path, limit=50):
    """Extract external URLs from the Referring page URL column."""
    external_urls = []
    domains = Counter()
    
    try:
        # Open file with UTF-8 BOM encoding
        with codecs.open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            print(f"Column names: {list(reader.fieldnames)[:5]}...")
            
            # Extract external referring URLs
            for i, row in enumerate(reader):
                if i > 5000:  # Check first 5000 rows
                    break
                    
                url = row.get('Referring page URL', '').strip()
                if url and url.startswith('http'):
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    
                    # Skip Admiral Markets domains
                    if 'admiralmarkets' not in domain and 'admirals' not in domain:
                        external_urls.append(url)
                        domains[domain] += 1
                        
                        if len(external_urls) >= limit:
                            break
            
            print(f"\nFound {len(external_urls)} external URLs")
            print(f"\nTop 10 domains:")
            for domain, count in domains.most_common(10):
                print(f"  - {domain}: {count} URLs")
            
            return external_urls
            
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

# Check both files
print("=== Checking admiralmarkets_latest_utf8.csv ===")
urls1 = extract_external_urls('data/inputs/admiral_markets/admiralmarkets_latest_utf8.csv')

print("\n=== Checking admiralmarkets_utf8.csv ===")
urls2 = extract_external_urls('data/inputs/admiral_markets/admiralmarkets_utf8.csv')

# Create test file with external URLs
all_urls = list(set(urls1 + urls2))[:30]  # Get 30 unique URLs

if all_urls:
    with open('data/test_external_urls.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in all_urls:
            writer.writerow([url])
    
    print(f"\n✅ Created test file with {len(all_urls)} external URLs: data/test_external_urls.csv")
    print("\nFirst 10 URLs:")
    for url in all_urls[:10]:
        print(f"  - {url}")
else:
    print("\n❌ No external URLs found") 