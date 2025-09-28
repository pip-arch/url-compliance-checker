#!/usr/bin/env python3
"""
Sync blacklisted URLs from the master file to Supabase.
Mark them as 'processed' since 'blacklisted' is not a valid status.
"""
import os
import sys
import csv
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Set

# Load environment variables FIRST
load_dotenv()

# Import supabase after loading env
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
MASTER_BLACKLIST_FILE = "data/outputs/blacklists/blacklist_consolidated_master.csv"
TMP_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"

class BlacklistSyncer:
    def __init__(self):
        # Get from environment variables
        SUPABASE_URL = os.getenv("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY")
            
        if not SUPABASE_KEY:
            raise ValueError("SUPABASE_ANON_KEY not found in environment")
        if not SUPABASE_URL:
            raise ValueError("SUPABASE_URL not found in environment")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"Connected to Supabase")
    
    def load_blacklist_from_file(self) -> List[Dict]:
        """Load blacklisted URLs from the master file"""
        blacklist_data = []
        
        if not os.path.exists(MASTER_BLACKLIST_FILE):
            logger.error(f"Master blacklist file not found: {MASTER_BLACKLIST_FILE}")
            return blacklist_data
        
        with open(MASTER_BLACKLIST_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                blacklist_data.append({
                    'url': row.get('URL', ''),
                    'main_domain': row.get('Main Domain', ''),
                    'reason': row.get('Reason', 'blacklist'),
                    'batch_id': row.get('Batch ID', ''),
                    'timestamp': row.get('Timestamp', '')
                })
        
        logger.info(f"Loaded {len(blacklist_data)} URLs from master blacklist file")
        return blacklist_data
    
    def sync_to_supabase(self, blacklist_data: List[Dict]):
        """Sync blacklisted URLs to Supabase"""
        if not blacklist_data:
            logger.info("No blacklist data to sync")
            return
        
        # Sync to blacklisted_urls table
        batch_size = 100
        total_synced = 0
        successful_batches = 0
        
        for i in range(0, len(blacklist_data), batch_size):
            batch = blacklist_data[i:i+batch_size]
            
            # Prepare records for blacklisted_urls
            blacklist_records = []
            for item in batch:
                blacklist_records.append({
                    'url': item['url'],
                    'main_domain': item['main_domain'],
                    'reason': item['reason'],
                    'batch_id': item['batch_id']
                })
            
            try:
                # Insert into blacklisted_urls table
                result = self.supabase.table('blacklisted_urls').upsert(
                    blacklist_records,
                    on_conflict='url'
                ).execute()
                
                total_synced += len(batch)
                successful_batches += 1
                logger.info(f"✅ Synced batch {successful_batches} to blacklisted_urls table (total: {total_synced}/{len(blacklist_data)})")
                
            except Exception as e:
                logger.error(f"❌ Error syncing batch: {e}")
                
                # Also try to update url_processing_queue
                try:
                    # Prepare records for url_processing_queue
                    queue_records = []
                    for item in batch:
                        # Extract domain info
                        from urllib.parse import urlparse
                        parsed = urlparse(item['url'])
                        domain = parsed.netloc
                        
                        queue_records.append({
                            'url': item['url'],
                            'domain': domain,
                            'main_domain': item['main_domain'] or domain,
                            'source_file': 'blacklist_import',
                            'priority': 0,
                            'status': 'processed',  # Use valid enum value
                            'retry_count': 0
                        })
                    
                    # Upsert to url_processing_queue
                    result = self.supabase.table('url_processing_queue').upsert(
                        queue_records,
                        on_conflict='url'
                    ).execute()
                    
                    logger.info(f"✅ Also updated url_processing_queue for batch")
                    
                except Exception as e2:
                    logger.error(f"❌ Could not update url_processing_queue: {e2}")
        
        logger.info(f"🎯 Total synced: {total_synced} URLs in {successful_batches} batches")
    
    def ensure_file_consistency(self):
        """Ensure the tmp blacklist file matches the master file"""
        if os.path.exists(MASTER_BLACKLIST_FILE):
            # Copy master to tmp location
            import shutil
            shutil.copy2(MASTER_BLACKLIST_FILE, TMP_BLACKLIST_FILE)
            logger.info(f"✅ Synced master blacklist to {TMP_BLACKLIST_FILE}")
        else:
            logger.error("❌ Master blacklist file not found!")
    
    def get_stats(self):
        """Get sync statistics"""
        stats = {
            'file_count': 0,
            'blacklisted_urls_count': 0,
            'processed_urls_count': 0
        }
        
        # File count
        if os.path.exists(MASTER_BLACKLIST_FILE):
            with open(MASTER_BLACKLIST_FILE, 'r') as f:
                stats['file_count'] = sum(1 for _ in f) - 1  # Subtract header
        
        # Try to get count from blacklisted_urls table
        try:
            result = self.supabase.table('blacklisted_urls').select('url', count='exact').execute()
            stats['blacklisted_urls_count'] = result.count
        except:
            pass
        
        # Get count of processed URLs
        try:
            result = self.supabase.table('url_processing_queue').select('url', count='exact').eq('status', 'processed').execute()
            stats['processed_urls_count'] = result.count
        except:
            pass
        
        return stats

async def main():
    """Main sync function"""
    try:
        syncer = BlacklistSyncer()
        
        # Get initial stats
        stats_before = syncer.get_stats()
        logger.info(f"📊 Before sync - File: {stats_before['file_count']}, Blacklisted URLs table: {stats_before['blacklisted_urls_count']}, Processed URLs: {stats_before['processed_urls_count']}")
        
        # Ensure file consistency first
        syncer.ensure_file_consistency()
        
        # Load blacklist data
        blacklist_data = syncer.load_blacklist_from_file()
        
        if blacklist_data:
            # Sync to Supabase
            syncer.sync_to_supabase(blacklist_data)
        
        # Get final stats
        stats_after = syncer.get_stats()
        logger.info(f"📊 After sync - File: {stats_after['file_count']}, Blacklisted URLs table: {stats_after['blacklisted_urls_count']}, Processed URLs: {stats_after['processed_urls_count']}")
        
        logger.info("✅ Blacklist sync completed!")
        
    except Exception as e:
        logger.error(f"❌ Error during sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 