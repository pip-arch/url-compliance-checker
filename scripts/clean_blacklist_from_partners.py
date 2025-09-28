#!/usr/bin/env python3
"""
Clean blacklist by removing partner resources and IP-based Admiral URLs
"""

import pandas as pd
import re
from urllib.parse import urlparse
import csv

def extract_partner_urls(partner_file):
    """Extract all URLs from partner resources file"""
    partner_urls = set()
    partner_domains = set()
    
    # Read the CSV file with error handling
    try:
        df = pd.read_csv(partner_file, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(partner_file, encoding='latin-1')
        except:
            df = pd.read_csv(partner_file, encoding='iso-8859-1')
    
    # Extract URLs from the Resources column
    for _, row in df.iterrows():
        if pd.notna(row.get('Resources', '')):
            resources = str(row['Resources'])
            
            # Find all URLs in the text
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, resources)
            
            for url in urls:
                # Clean up the URL
                url = url.strip().rstrip('/')
                if not url.startswith('http'):
                    url = 'https://' + url
                
                partner_urls.add(url)
                
                # Extract domain
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain:
                        partner_domains.add(domain)
                        # Also add without www
                        if domain.startswith('www.'):
                            partner_domains.add(domain[4:])
                except:
                    pass
    
    # Also extract plain domain names from resources
    for _, row in df.iterrows():
        if pd.notna(row.get('Resources', '')):
            resources = str(row['Resources'])
            # Look for domain patterns (more specific to avoid false matches)
            domain_pattern = r'(?:^|\s|/)([a-zA-Z0-9-]+\.(?:com|org|net|de|fr|eu|uk|co\.uk))(?:$|\s|/|\.)'
            domains = re.findall(domain_pattern, resources)
            for domain in domains:
                domain = domain.lower()
                partner_domains.add(domain)
                if domain.startswith('www.'):
                    partner_domains.add(domain[4:])
    
    return partner_urls, partner_domains

def is_ip_admiral_url(url):
    """Check if URL is IP-based with Admiral Markets path"""
    try:
        parsed = urlparse(url)
        # Check if hostname is an IP address
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', parsed.netloc):
            # Check if path contains admiral-related keywords
            if 'admiral' in url.lower():
                return True
    except:
        pass
    return False

def is_partner_resource(url, partner_urls, partner_domains):
    """Check if URL belongs to partner resources"""
    url_lower = url.lower()
    
    # Direct URL match
    if url in partner_urls:
        return True
    
    # Check domain match
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check exact domain match
        if domain in partner_domains:
            return True
        
        # Check without www
        if domain.startswith('www.') and domain[4:] in partner_domains:
            return True
        
        # Check subdomain matches
        for partner_domain in partner_domains:
            if domain.endswith('.' + partner_domain) or domain == partner_domain:
                return True
    except:
        pass
    
    return False

def main():
    # File paths
    blacklist_file = 'data/tmp/blacklist_consolidated.csv'
    partner_file = 'Partners_Resources_EU(Sheet1).csv'
    output_file = 'data/outputs/blacklist_urls_cleaned.csv'
    removed_file = 'data/outputs/removed_urls.csv'
    
    print("Loading partner resources...")
    partner_urls, partner_domains = extract_partner_urls(partner_file)
    
    print(f"Found {len(partner_urls)} partner URLs and {len(partner_domains)} partner domains")
    print("\nPartner domains found:")
    for domain in sorted(partner_domains):
        print(f"  - {domain}")
    
    print("\nLoading blacklist...")
    # Read blacklist with error handling for encoding and parsing
    try:
        df_blacklist = pd.read_csv(blacklist_file, encoding='utf-8', on_bad_lines='skip')
    except:
        try:
            df_blacklist = pd.read_csv(blacklist_file, encoding='latin-1', on_bad_lines='skip')
        except:
            # Last resort: read line by line
            urls = []
            with open(blacklist_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        # Get the first comma-separated value
                        url = line.split(',')[0].strip()
                        if url:
                            urls.append(url)
            df_blacklist = pd.DataFrame({'url': urls})
    
    # Get the first column (URLs)
    url_column = df_blacklist.iloc[:, 0].astype(str)
    
    print(f"Total URLs in blacklist: {len(url_column)}")
    
    # Check for matches
    partner_matches = []
    ip_admiral_matches = []
    clean_urls = []
    
    for url in url_column:
        if pd.isna(url) or url == 'nan':
            continue
            
        url = url.strip()
        
        # Check if it's a partner resource
        if is_partner_resource(url, partner_urls, partner_domains):
            partner_matches.append(url)
        # Check if it's IP-based Admiral URL
        elif is_ip_admiral_url(url):
            ip_admiral_matches.append(url)
        else:
            clean_urls.append(url)
    
    print(f"\nFound {len(partner_matches)} partner resource URLs in blacklist")
    if partner_matches:
        print("Partner URLs found in blacklist:")
        for url in partner_matches[:10]:  # Show first 10
            print(f"  - {url}")
        if len(partner_matches) > 10:
            print(f"  ... and {len(partner_matches) - 10} more")
    
    print(f"\nFound {len(ip_admiral_matches)} IP-based Admiral URLs")
    if ip_admiral_matches:
        print("IP-based Admiral URLs found:")
        for url in ip_admiral_matches[:10]:  # Show first 10
            print(f"  - {url}")
        if len(ip_admiral_matches) > 10:
            print(f"  ... and {len(ip_admiral_matches) - 10} more")
    
    # Save cleaned URLs
    print(f"\nSaving {len(clean_urls)} cleaned URLs to {output_file}")
    pd.DataFrame({'url': clean_urls}).to_csv(output_file, index=False)
    
    # Save removed URLs for reference
    removed_data = []
    for url in partner_matches:
        removed_data.append({'url': url, 'reason': 'partner_resource'})
    for url in ip_admiral_matches:
        removed_data.append({'url': url, 'reason': 'ip_based_admiral'})
    
    if removed_data:
        pd.DataFrame(removed_data).to_csv(removed_file, index=False)
        print(f"Saved {len(removed_data)} removed URLs to {removed_file}")
    
    print("\nProcess completed!")
    print(f"Original blacklist: {len(url_column)} URLs")
    print(f"Cleaned blacklist: {len(clean_urls)} URLs")
    print(f"Removed: {len(removed_data)} URLs")

if __name__ == "__main__":
    main() 