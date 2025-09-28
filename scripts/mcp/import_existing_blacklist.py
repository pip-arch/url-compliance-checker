#!/usr/bin/env python3
"""
Import existing blacklist from CSV into Supabase for state management.
This preserves all existing blacklisted URLs while enabling better tracking.
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from supabase import create_client, Client
from urllib.parse import urlparse
import json
from typing import List, Dict, Tuple

# Supabase configuration
SUPABASE_URL = "https://jyyhtegtspvhntrrebmf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5eWh0ZWd0c3B2aG50cnJlYm1mIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjExMDU4MywiZXhwIjoyMDYxNjg2NTgzfQ.a4SZ0b4Frymd5wTlmsjpbb8hPW_vWtm31zyRP_3th8U"

def extract_domain(url: str) -> Tuple[str, str]:
    """Extract domain and main domain from URL."""
    try:
        parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'http://{url}')
        domain = parsed.netloc or parsed.path.split('/')[0]
        # Simple main domain extraction (could be improved with tldextract)
        parts = domain.split('.')
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net']:
            main_domain = '.'.join(parts[-3:])
        else:
            main_domain = '.'.join(parts[-2:]) if len(parts) > 1 else domain
        return domain, main_domain
    except:
        return url, url

def read_blacklist_csv(filepath: str) -> List[Dict]:
    """Read the existing blacklist CSV and parse it."""
    blacklist_data = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        # Try to detect the delimiter
        sample = f.read(1024)
        f.seek(0)
        
        # Check if it's comma or tab delimited
        if '\t' in sample:
            delimiter = '\t'
        else:
            delimiter = ','
            
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for row in reader:
            # Handle different possible column names
            url = row.get('url') or row.get('URL') or row.get('Url') or ''
            domain = row.get('domain') or row.get('Domain') or ''
            reason = row.get('reason') or row.get('Reason') or row.get('compliance_issues') or ''
            confidence = row.get('confidence') or row.get('Confidence') or '0.0'
            category = row.get('category') or row.get('Category') or 'BLACKLIST'
            batch_id = row.get('batch_id') or row.get('Batch ID') or 'imported'
            
            if url:
                if not domain:
                    domain, main_domain = extract_domain(url)
                else:
                    _, main_domain = extract_domain(domain)
                    
                blacklist_data.append({
                    'url': url.strip(),
                    'domain': domain.strip(),
                    'main_domain': main_domain.strip(),
                    'reason': reason.strip(),
                    'confidence': float(confidence) if confidence else 0.0,
                    'category': category.strip(),
                    'batch_id': batch_id.strip()
                })
    
    return blacklist_data

def import_to_supabase(supabase: Client, blacklist_data: List[Dict]):
    """Import blacklist data into Supabase tables."""
    print(f"Importing {len(blacklist_data)} URLs into Supabase...")
    
    # Remove duplicates from blacklist_data
    seen_urls = set()
    unique_blacklist_data = []
    for item in blacklist_data:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_blacklist_data.append(item)
    
    print(f"Found {len(unique_blacklist_data)} unique URLs after deduplication")
    blacklist_data = unique_blacklist_data
    
    # Prepare batch data
    urls_to_insert = []
    domains_to_track = {}
    history_records = []
    
    for item in blacklist_data:
        # Prepare URL queue entry
        urls_to_insert.append({
            'url': item['url'],
            'domain': item['domain'],
            'main_domain': item['main_domain'],
            'status': 'processed',
            'source_file': 'blacklist_consolidated.csv'
        })
        
        # Track domain statistics
        if item['main_domain'] not in domains_to_track:
            domains_to_track[item['main_domain']] = {
                'domain': item['main_domain'],
                'main_domain': item['main_domain'],
                'total_urls': 0,
                'blacklisted_urls': 0,
                'processed_urls': 0
            }
        
        domains_to_track[item['main_domain']]['total_urls'] += 1
        domains_to_track[item['main_domain']]['blacklisted_urls'] += 1
        domains_to_track[item['main_domain']]['processed_urls'] += 1
    
    # Insert URLs in batches
    batch_size = 50  # Reduced batch size
    for i in range(0, len(urls_to_insert), batch_size):
        batch = urls_to_insert[i:i + batch_size]
        try:
            result = supabase.table('url_processing_queue').insert(
                batch
            ).execute()
            print(f"Inserted batch {i//batch_size + 1}/{(len(urls_to_insert) + batch_size - 1)//batch_size}")
        except Exception as e:
            # Try to insert individually if batch fails
            print(f"Batch insert failed, trying individual inserts: {e}")
            for url_item in batch:
                try:
                    supabase.table('url_processing_queue').insert(url_item).execute()
                except:
                    pass  # Skip if already exists
    
    # Insert/update domain statistics
    domain_stats = list(domains_to_track.values())
    
    # Mark domains with 3+ blacklisted URLs as blacklisted
    for stat in domain_stats:
        if stat['blacklisted_urls'] >= 3:
            stat['is_blacklisted'] = True
            stat['blacklist_reason'] = f"Imported from existing blacklist: {stat['blacklisted_urls']} blacklisted URLs"
    
    try:
        result = supabase.table('domain_statistics').upsert(
            domain_stats,
            on_conflict='domain'
        ).execute()
        print(f"Updated statistics for {len(domain_stats)} domains")
    except Exception as e:
        print(f"Error updating domain statistics: {e}")
    
    # Create processing history records for audit trail
    print("Creating processing history records...")
    
    # Process URLs in smaller chunks to avoid query length issues
    chunk_size = 50
    for chunk_start in range(0, min(len(blacklist_data), 500), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(blacklist_data))
        chunk_urls = [item['url'] for item in blacklist_data[chunk_start:chunk_end]]
        
        try:
            # Get the inserted URL IDs for this chunk
            url_records = supabase.table('url_processing_queue').select('id, url').in_('url', chunk_urls).execute()
            url_id_map = {record['url']: record['id'] for record in url_records.data}
            
            # Create history records for this chunk
            chunk_history = []
            for item in blacklist_data[chunk_start:chunk_end]:
                if item['url'] in url_id_map:
                    chunk_history.append({
                        'url_id': url_id_map[item['url']],
                        'url': item['url'],
                        'batch_id': item['batch_id'],
                        'status': 'processed',
                        'category': 'blacklist',
                        'confidence': item['confidence'],
                        'analysis_method': 'Imported from existing blacklist',
                        'api_calls_made': {'source': 'legacy_import', 'reason': item['reason']}
                    })
            
            # Insert history records for this chunk
            if chunk_history:
                try:
                    result = supabase.table('processing_history').insert(chunk_history).execute()
                except Exception as e:
                    print(f"Error inserting history batch: {e}")
        except Exception as e:
            print(f"Error processing chunk {chunk_start}-{chunk_end}: {e}")
    
    print(f"Import completed!")
    
    # Get and display summary statistics
    try:
        metrics = supabase.rpc('get_processing_metrics').execute()
        print("\nDatabase Statistics:")
        for metric in metrics.data:
            print(f"  {metric['metric_name']}: {metric['metric_value']}")
    except Exception as e:
        print(f"Error fetching metrics: {e}")

def main():
    """Main function to run the import."""
    # Check if blacklist file exists
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    
    if not os.path.exists(blacklist_file):
        print(f"Error: {blacklist_file} not found!")
        return
    
    print(f"Reading blacklist from {blacklist_file}...")
    blacklist_data = read_blacklist_csv(blacklist_file)
    print(f"Found {len(blacklist_data)} URLs in blacklist")
    
    # Show sample data
    if blacklist_data:
        print("\nSample entry:")
        print(json.dumps(blacklist_data[0], indent=2))
    
    # Connect to Supabase
    print("\nConnecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Import data
    import_to_supabase(supabase, blacklist_data)
    
    # Create initial checkpoint
    print("\nCreating initial checkpoint...")
    try:
        checkpoint_data = {
            'checkpoint_name': 'initial_import',
            'last_processed_index': len(blacklist_data),
            'last_processed_url': blacklist_data[-1]['url'] if blacklist_data else '',
            'batch_id': 'import_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
            'total_urls': len(blacklist_data),
            'processed_urls': len(blacklist_data),
            'failed_urls': 0,
            'skipped_urls': 0,
            'blacklisted_count': len(blacklist_data),
            'whitelisted_count': 0,
            'review_count': 0,
            'processing_stats': {
                'import_date': datetime.now().isoformat(),
                'source_file': blacklist_file,
                'total_domains': len(set(item['main_domain'] for item in blacklist_data))
            }
        }
        
        result = supabase.table('processing_checkpoints').insert(checkpoint_data).execute()
        print("Initial checkpoint created successfully!")
    except Exception as e:
        print(f"Error creating checkpoint: {e}")

if __name__ == "__main__":
    main() 