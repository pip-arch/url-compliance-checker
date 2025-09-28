#!/usr/bin/env python3
"""
Organize URL checker outputs into separate files for blacklist, whitelist, and review.
This script processes the database and creates well-organized output files.
"""
import os
import sys
import csv
import asyncio
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import database_service
from app.models.report import URLCategory


async def organize_outputs():
    """Organize URLs into separate output files based on their category."""
    print("\n" + "="*80)
    print("📁 ORGANIZING URL CHECKER OUTPUTS")
    print("="*80)
    
    # Create output directory
    output_dir = "data/outputs/organized"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Output file paths
    blacklist_file = os.path.join(output_dir, f"blacklist_final_{timestamp}.csv")
    whitelist_file = os.path.join(output_dir, f"whitelist_verified_{timestamp}.csv")
    review_file = os.path.join(output_dir, f"review_needed_{timestamp}.csv")
    
    # Get all URL reports from database
    print("\n📊 Fetching URL reports from database...")
    
    try:
        # Get all URL reports directly
        all_url_reports = await database_service.get_all_url_reports(limit=10000)
        
        print(f"✅ Found {len(all_url_reports)} URL reports total")
        
        if not all_url_reports:
            print("❌ No URL reports found!")
            print("   Trying to read from blacklist_consolidated.csv instead...")
            
            # Fall back to reading from CSV file
            blacklist_file = "data/tmp/blacklist_consolidated.csv"
            if os.path.exists(blacklist_file):
                print(f"   Reading from {blacklist_file}")
                import subprocess
                subprocess.run(["python", "scripts/organize_outputs_simple.py"])
                return
            else:
                print("   No blacklist file found either!")
                return
        
        # Organize by category
        blacklist_urls = []
        whitelist_urls = []
        review_urls = []
        
        # Domain statistics
        domain_stats = defaultdict(lambda: {
            'blacklist': 0,
            'whitelist': 0,
            'review': 0,
            'total': 0
        })
        
        # Track unique URLs to avoid duplicates
        seen_urls = set()
        
        for report in all_url_reports:
            # Skip duplicates
            if report.url in seen_urls:
                continue
            seen_urls.add(report.url)
            
            # Parse domain
            domain = urlparse(report.url).netloc
            main_domain = ".".join(domain.split(".")[-2:]) if len(domain.split(".")) > 1 else domain
            
            # Prepare row data
            row_data = {
                'url': report.url,
                'domain': main_domain,
                'confidence': getattr(report.ai_analysis, 'confidence', 0.0) if report.ai_analysis else 0.0,
                'analysis_method': getattr(report, 'analysis_method', 'unknown'),
                'explanation': getattr(report.ai_analysis, 'explanation', '') if report.ai_analysis else '',
                'compliance_issues': ', '.join(str(issue) for issue in getattr(report.ai_analysis, 'compliance_issues', [])) if report.ai_analysis else '',
                'rule_matches': len(report.rule_matches) if report.rule_matches else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Update domain stats
            domain_stats[main_domain]['total'] += 1
            
            # Categorize URL
            if report.category == URLCategory.BLACKLIST or report.category == 'blacklist':
                blacklist_urls.append(row_data)
                domain_stats[main_domain]['blacklist'] += 1
            elif report.category == URLCategory.WHITELIST or report.category == 'whitelist':
                # Create whitelist-specific row data
                whitelist_row = {
                    'url': report.url,
                    'domain': main_domain,
                    'confidence': getattr(report.ai_analysis, 'confidence', 0.0) if report.ai_analysis else 0.0,
                    'analysis_method': getattr(report, 'analysis_method', 'unknown'),
                    'explanation': getattr(report.ai_analysis, 'explanation', '') if report.ai_analysis else '',
                    'timestamp': datetime.now().isoformat()
                }
                whitelist_urls.append(whitelist_row)
                domain_stats[main_domain]['whitelist'] += 1
            else:
                review_urls.append(row_data)
                domain_stats[main_domain]['review'] += 1
        
        # Write blacklist file
        print(f"\n📝 Writing blacklist file: {blacklist_file}")
        with open(blacklist_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'domain', 'confidence', 'analysis_method', 
                'explanation', 'compliance_issues', 'rule_matches', 'timestamp'
            ])
            writer.writeheader()
            writer.writerows(sorted(blacklist_urls, key=lambda x: (x['domain'], x['url'])))
        print(f"✅ Wrote {len(blacklist_urls)} blacklisted URLs")
        
        # Write whitelist file
        print(f"\n📝 Writing whitelist file: {whitelist_file}")
        with open(whitelist_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'domain', 'confidence', 'analysis_method', 
                'explanation', 'timestamp'
            ])
            writer.writeheader()
            writer.writerows(sorted(whitelist_urls, key=lambda x: (x['domain'], x['url'])))
        print(f"✅ Wrote {len(whitelist_urls)} whitelisted URLs")
        
        # Write review file with enhanced information
        print(f"\n📝 Writing review file: {review_file}")
        with open(review_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'domain', 'confidence', 'analysis_method',
                'explanation', 'compliance_issues', 'rule_matches', 
                'action_needed', 'priority', 'timestamp'
            ])
            writer.writeheader()
            
            # Add priority and action needed
            for url_data in review_urls:
                # Determine priority based on confidence and rule matches
                if url_data['confidence'] > 0.7 or url_data['rule_matches'] > 2:
                    url_data['priority'] = 'HIGH'
                    url_data['action_needed'] = 'Urgent review - likely blacklist'
                elif url_data['confidence'] > 0.5 or url_data['rule_matches'] > 0:
                    url_data['priority'] = 'MEDIUM'
                    url_data['action_needed'] = 'Review compliance issues'
                else:
                    url_data['priority'] = 'LOW'
                    url_data['action_needed'] = 'Manual verification needed'
            
            writer.writerows(sorted(review_urls, key=lambda x: (
                {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['priority']], 
                x['domain'], 
                x['url']
            )))
        print(f"✅ Wrote {len(review_urls)} URLs for review")
        
        # Write domain summary
        summary_file = os.path.join(output_dir, f"domain_summary_{timestamp}.csv")
        print(f"\n📝 Writing domain summary: {summary_file}")
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Domain', 'Total URLs', 'Blacklisted', 'Whitelisted', 'For Review', 'Status'])
            
            for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['blacklist'], reverse=True):
                # Determine domain status
                if stats['blacklist'] >= 3:
                    status = 'BLACKLISTED_DOMAIN'
                elif stats['blacklist'] > stats['whitelist']:
                    status = 'SUSPICIOUS'
                elif stats['whitelist'] > 0 and stats['blacklist'] == 0:
                    status = 'TRUSTED'
                else:
                    status = 'MIXED'
                
                writer.writerow([
                    domain,
                    stats['total'],
                    stats['blacklist'],
                    stats['whitelist'],
                    stats['review'],
                    status
                ])
        
        # Print summary
        print("\n" + "="*80)
        print("📊 ORGANIZATION SUMMARY")
        print("="*80)
        print(f"✅ Blacklisted URLs: {len(blacklist_urls)}")
        print(f"✅ Whitelisted URLs: {len(whitelist_urls)}")
        print(f"⚠️  URLs for Review: {len(review_urls)}")
        print(f"📁 Total Domains: {len(domain_stats)}")
        
        # Show high-priority review items
        high_priority = [u for u in review_urls if u.get('priority') == 'HIGH']
        if high_priority:
            print(f"\n🚨 High Priority Reviews: {len(high_priority)}")
            for url_data in high_priority[:5]:
                print(f"   - {url_data['url']} (confidence: {url_data['confidence']:.2f})")
        
        print(f"\n📁 Output files saved to: {output_dir}")
        
    except Exception as e:
        print(f"❌ Error organizing outputs: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run the output organization."""
    await organize_outputs()


if __name__ == "__main__":
    asyncio.run(main()) 