#!/usr/bin/env python3
"""Analyze patterns in the existing blacklist to improve detection."""

import pandas as pd
from collections import Counter, defaultdict
from urllib.parse import urlparse
import re

def analyze_blacklist():
    """Analyze the consolidated blacklist for patterns."""
    
    # Load blacklist
    blacklist_path = "data/outputs/blacklists/blacklist_consolidated_master.csv"
    
    try:
        df = pd.read_csv(blacklist_path)
        print(f"📊 Analyzing {len(df)} blacklisted URLs...\n")
    except Exception as e:
        print(f"Error loading blacklist: {e}")
        return
    
    # Extract domains
    domains = []
    tlds = []
    paths = []
    
    for url in df['url']:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domains.append(domain)
            
            # Extract TLD
            tld = domain.split('.')[-1] if '.' in domain else 'unknown'
            tlds.append(tld)
            
            # Extract path patterns
            path = parsed.path.lower()
            if path and path != '/':
                paths.append(path)
        except:
            continue
    
    # Analyze domains
    domain_counts = Counter(domains)
    print("🌐 TOP 20 BLACKLISTED DOMAINS:")
    for domain, count in domain_counts.most_common(20):
        print(f"  {domain}: {count} URLs")
    
    # Analyze TLDs
    tld_counts = Counter(tlds)
    print(f"\n🔤 TOP LEVEL DOMAINS:")
    for tld, count in tld_counts.most_common(10):
        percentage = (count / len(tlds)) * 100
        print(f"  .{tld}: {count} ({percentage:.1f}%)")
    
    # Analyze path patterns
    path_keywords = defaultdict(int)
    keywords = ['forex', 'trading', 'broker', 'invest', 'money', 'profit', 
                'bonus', 'signal', 'robot', 'ea', 'indicator', 'strategy',
                'course', 'tutorial', 'review', 'scam', 'best', 'top']
    
    for path in paths:
        for keyword in keywords:
            if keyword in path:
                path_keywords[keyword] += 1
    
    print(f"\n🔍 COMMON PATH KEYWORDS:")
    sorted_keywords = sorted(path_keywords.items(), key=lambda x: x[1], reverse=True)
    for keyword, count in sorted_keywords[:15]:
        percentage = (count / len(paths)) * 100 if paths else 0
        print(f"  '{keyword}': {count} ({percentage:.1f}%)")
    
    # Analyze URL patterns
    patterns = {
        'numeric_domain': 0,
        'subdomain_heavy': 0,
        'long_path': 0,
        'query_params': 0,
        'non_standard_port': 0,
        'ip_address': 0,
    }
    
    for url in df['url']:
        try:
            parsed = urlparse(url)
            
            # Check for numeric domains
            if re.search(r'\d{3,}', parsed.netloc):
                patterns['numeric_domain'] += 1
            
            # Check for multiple subdomains
            if parsed.netloc.count('.') > 2:
                patterns['subdomain_heavy'] += 1
            
            # Check for long paths
            if len(parsed.path) > 50:
                patterns['long_path'] += 1
            
            # Check for query parameters
            if parsed.query:
                patterns['query_params'] += 1
            
            # Check for non-standard ports
            if parsed.port and parsed.port not in [80, 443]:
                patterns['non_standard_port'] += 1
            
            # Check for IP addresses
            if re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc):
                patterns['ip_address'] += 1
        except:
            continue
    
    print(f"\n📐 URL PATTERNS:")
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(df)) * 100
        print(f"  {pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Generate recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("1. Focus on domains with multiple violations")
    print("2. Flag URLs with common path keywords: " + ", ".join([k[0] for k in sorted_keywords[:5]]))
    print("3. Be suspicious of:")
    for pattern, count in patterns.items():
        if count > len(df) * 0.1:  # More than 10%
            print(f"   - {pattern.replace('_', ' ').title()}")
    
    # Export domain statistics
    domain_stats = pd.DataFrame(
        [(domain, count) for domain, count in domain_counts.most_common()],
        columns=['domain', 'violation_count']
    )
    domain_stats.to_csv('data/outputs/analysis_results/blacklist_domain_stats.csv', index=False)
    print(f"\n✅ Domain statistics exported to: data/outputs/analysis_results/blacklist_domain_stats.csv")

if __name__ == "__main__":
    analyze_blacklist() 