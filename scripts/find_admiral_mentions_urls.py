#!/usr/bin/env python3
"""
Find URLs that likely contain Admiral Markets mentions from our data files.
"""

import pandas as pd
import os

def find_admiral_mention_urls():
    """Find URLs that likely mention Admiral Markets."""
    
    # Look for forex/trading related URLs or competitor analysis pages
    admiral_related_keywords = [
        'forex', 'broker', 'trading', 'cfd', 'review', 
        'comparison', 'best', 'top', 'vs', 'alternative'
    ]
    
    admiral_urls = []
    
    # Check the all_admiral_urls.csv file
    csv_file = "data/test_files/all_admiral_urls.csv"
    if os.path.exists(csv_file):
        print(f"Searching {csv_file} for URLs likely to mention Admiral Markets...")
        try:
            df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
            
            # Get URL column
            url_col = None
            for col in df.columns:
                if 'url' in col.lower() or 'source' in col.lower():
                    url_col = col
                    break
            
            if url_col:
                for url in df[url_col].dropna():
                    url_lower = str(url).lower()
                    # Check if URL contains keywords that suggest it might mention Admiral Markets
                    if any(keyword in url_lower for keyword in admiral_related_keywords):
                        # Exclude Admiral Markets own domains
                        if not any(domain in url_lower for domain in ['admiralmarkets.com', 'admirals.com']):
                            admiral_urls.append(url)
                            if len(admiral_urls) >= 20:
                                break
        except Exception as e:
            print(f"Error reading CSV: {e}")
    
    # Also check external URLs for forex/broker related ones
    external_file = "data/test_external_urls.csv"
    if os.path.exists(external_file):
        print(f"\nSearching {external_file}...")
        try:
            df = pd.read_csv(external_file)
            if 'URL' in df.columns:
                for url in df['URL'].dropna():
                    url_lower = str(url).lower()
                    if any(keyword in url_lower for keyword in ['broker', 'forex', 'trading']):
                        admiral_urls.append(url)
        except Exception as e:
            print(f"Error reading external URLs: {e}")
    
    # Always use manual test URLs for reliable testing
    print("\nUsing curated test URLs likely to mention Admiral Markets...")
    manual_urls = [
        "https://www.investopedia.com/best-forex-brokers-5084736",
        "https://www.forexbrokers.com/",
        "https://www.dailyforex.com/forex-brokers",
        "https://brokerchooser.com/best-brokers/forex-brokers",
        "https://www.benzinga.com/money/best-forex-brokers/",
        "https://www.forbes.com/advisor/investing/best-forex-brokers/",
        "https://www.nerdwallet.com/best/investing/forex-brokers",
        "https://www.business.com/articles/best-forex-brokers/",
        "https://tradersunion.com/best-forex-brokers/",
        "https://www.compareforexbrokers.com/"
    ]
    
    output_file = "data/test_admiral_mention_urls.csv"
    pd.DataFrame({'URL': manual_urls}).to_csv(output_file, index=False)
    print(f"\n✅ Created {output_file} with {len(manual_urls)} URLs likely to mention Admiral Markets")
    print("\nTest URLs:")
    for i, url in enumerate(manual_urls, 1):
        print(f"  {i}. {url}")

if __name__ == "__main__":
    find_admiral_mention_urls() 