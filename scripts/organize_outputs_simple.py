#!/usr/bin/env python3
"""
Simple script to organize blacklist_consolidated.csv into separate output files.
This reads directly from the CSV file instead of the database.
"""
import os
import csv
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

def organize_outputs():
    """Organize URLs from blacklist_consolidated.csv into separate files."""
    print("\n" + "="*80)
    print("📁 ORGANIZING URL CHECKER OUTPUTS (Simple Version)")
    print("="*80)
    
    # Input file
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    
    if not os.path.exists(blacklist_file):
        print(f"❌ Blacklist file not found: {blacklist_file}")
        return
    
    # Create output directory
    output_dir = "data/outputs/organized"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Output file paths
    blacklist_output = os.path.join(output_dir, f"blacklist_final_{timestamp}.csv")
    domain_summary = os.path.join(output_dir, f"domain_summary_{timestamp}.csv")
    
    # Read blacklist data
    blacklist_urls = []
    domain_stats = defaultdict(lambda: {
        'urls': [],
        'reasons': set(),
        'confidence_scores': [],
        'analysis_methods': set()
    })
    
    print(f"\n📊 Reading blacklist from: {blacklist_file}")
    
    with open(blacklist_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Extract data
            url = row.get('URL', '')
            main_domain = row.get('Main Domain', '')
            reason = row.get('Reason', '')
            confidence = row.get('Confidence', '0')
            category = row.get('Category', 'blacklist')
            compliance_issues = row.get('Compliance Issues', '')
            batch_id = row.get('Batch ID', '')
            timestamp_str = row.get('Timestamp', '')
            
            # Parse confidence
            try:
                confidence_float = float(confidence)
            except:
                confidence_float = 0.0
            
            # Extract analysis method from reason
            analysis_method = 'unknown'
            if 'real_llm:' in reason:
                analysis_method = 'real_llm'
            elif 'openai:' in reason:
                analysis_method = 'openai'
            elif 'fallback:' in reason:
                analysis_method = 'fallback'
            
            # Clean reason
            clean_reason = reason.split(':', 1)[-1].strip() if ':' in reason else reason
            
            # Add to blacklist
            blacklist_urls.append({
                'url': url,
                'domain': main_domain,
                'confidence': confidence_float,
                'analysis_method': analysis_method,
                'reason': clean_reason,
                'compliance_issues': compliance_issues,
                'batch_id': batch_id,
                'timestamp': timestamp_str
            })
            
            # Update domain stats
            if main_domain:
                domain_stats[main_domain]['urls'].append(url)
                domain_stats[main_domain]['reasons'].add(clean_reason)
                domain_stats[main_domain]['confidence_scores'].append(confidence_float)
                domain_stats[main_domain]['analysis_methods'].add(analysis_method)
    
    print(f"✅ Read {len(blacklist_urls)} blacklisted URLs")
    print(f"✅ Found {len(domain_stats)} unique domains")
    
    # Write organized blacklist
    print(f"\n📝 Writing organized blacklist: {blacklist_output}")
    with open(blacklist_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'url', 'domain', 'confidence', 'analysis_method', 
            'reason', 'compliance_issues', 'batch_id', 'timestamp'
        ])
        writer.writeheader()
        writer.writerows(sorted(blacklist_urls, key=lambda x: (x['domain'], x['url'])))
    
    # Write domain summary
    print(f"\n📝 Writing domain summary: {domain_summary}")
    with open(domain_summary, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Domain', 'URL Count', 'Avg Confidence', 
            'Analysis Methods', 'Top Reasons', 'Status'
        ])
        
        for domain, stats in sorted(domain_stats.items(), 
                                   key=lambda x: len(x[1]['urls']), 
                                   reverse=True):
            # Calculate average confidence
            avg_confidence = sum(stats['confidence_scores']) / len(stats['confidence_scores']) if stats['confidence_scores'] else 0
            
            # Determine status
            url_count = len(stats['urls'])
            if url_count >= 3:
                status = 'BLACKLISTED_DOMAIN'
            elif url_count >= 2:
                status = 'SUSPICIOUS'
            else:
                status = 'FLAGGED'
            
            # Get top reasons (first 3)
            top_reasons = list(stats['reasons'])[:3]
            top_reasons_str = ' | '.join(r[:50] + '...' if len(r) > 50 else r for r in top_reasons)
            
            writer.writerow([
                domain,
                url_count,
                f"{avg_confidence:.2f}",
                ', '.join(stats['analysis_methods']),
                top_reasons_str,
                status
            ])
    
    # Print summary
    print("\n" + "="*80)
    print("📊 ORGANIZATION SUMMARY")
    print("="*80)
    print(f"✅ Blacklisted URLs: {len(blacklist_urls)}")
    print(f"📁 Unique Domains: {len(domain_stats)}")
    
    # Show top blacklisted domains
    print("\n🔝 Top 10 Blacklisted Domains:")
    for domain, stats in sorted(domain_stats.items(), 
                               key=lambda x: len(x[1]['urls']), 
                               reverse=True)[:10]:
        print(f"   - {domain}: {len(stats['urls'])} URLs")
    
    # Show domain status distribution
    status_counts = defaultdict(int)
    for domain, stats in domain_stats.items():
        url_count = len(stats['urls'])
        if url_count >= 3:
            status_counts['BLACKLISTED_DOMAIN'] += 1
        elif url_count >= 2:
            status_counts['SUSPICIOUS'] += 1
        else:
            status_counts['FLAGGED'] += 1
    
    print("\n📊 Domain Status Distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"   - {status}: {count} domains")
    
    print(f"\n📁 Output files saved to: {output_dir}")
    print("   - blacklist_final_*.csv: Organized blacklist with all details")
    print("   - domain_summary_*.csv: Summary by domain with status")
    
    # Note about missing features
    print("\n⚠️  Note: This simple version only processes blacklisted URLs.")
    print("   Whitelist and review files require database access.")


if __name__ == "__main__":
    organize_outputs() 