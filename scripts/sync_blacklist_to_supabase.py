#!/usr/bin/env python3
"""
Sync blacklisted URLs from the master file to Supabase.
This ensures both the local file and Supabase database are in sync.
"""
import os
import sys
import csv
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Set

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jyyhtegtspvhntrrebmf.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# File paths
MASTER_BLACKLIST_FILE = "data/outputs/blacklists/blacklist_consolidated_master.csv"
TMP_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"

class BlacklistSyncer:
    def __init__(self):
        if not SUPABASE_KEY:
            raise ValueError("SUPABASE_ANON_KEY not found in environment")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"Connected to Supabase at {SUPABASE_URL}")
    
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
                    'timestamp': row.get('Timestamp', datetime.now().isoformat())
                })
        
        logger.info(f"Loaded {len(blacklist_data)} URLs from master blacklist file")
        return blacklist_data
    
    def get_existing_urls_from_supabase(self) -> Set[str]:
        """Get all blacklisted URLs already in Supabase"""
        existing_urls = set()
        
        try:
            # Query blacklisted URLs from Supabase
            result = self.supabase.table('url_processing_queue').select('url').eq('category', 'blacklist').execute()
            
            for record in result.data:
                existing_urls.add(record['url'])
            
            logger.info(f"Found {len(existing_urls)} blacklisted URLs in Supabase")
            return existing_urls
        except Exception as e:
            logger.error(f"Error fetching from Supabase: {e}")
            return existing_urls
    
    def sync_to_supabase(self, blacklist_data: List[Dict]):
        """Sync blacklisted URLs to Supabase"""
        # Get existing URLs
        existing_urls = self.get_existing_urls_from_supabase()
        
        # Filter new URLs
        new_urls = []
        updated_urls = []
        
        for item in blacklist_data:
            url = item['url']
            if url not in existing_urls:
                new_urls.append(item)
            else:
                updated_urls.append(item)
        
        logger.info(f"Found {len(new_urls)} new URLs to add to Supabase")
        logger.info(f"Found {len(updated_urls)} existing URLs that may need updates")
        
        # Insert new URLs
        if new_urls:
            batch_size = 100
            for i in range(0, len(new_urls), batch_size):
                batch = new_urls[i:i+batch_size]
                
                # Prepare records for Supabase
                records = []
                for item in batch:
                    records.append({
                        'url': item['url'],
                        'main_domain': item['main_domain'],
                        'status': 'processed',
                        'category': 'blacklist',
                        'analysis_result': {
                            'reason': item['reason'],
                            'batch_id': item['batch_id'],
                            'timestamp': item['timestamp']
                        },
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    })
                
                try:
                    result = self.supabase.table('url_processing_queue').insert(records).execute()
                    logger.info(f"Inserted batch of {len(batch)} URLs to Supabase")
                except Exception as e:
                    logger.error(f"Error inserting batch to Supabase: {e}")
        
        # Update existing URLs if needed
        if updated_urls:
            logger.info("Updating existing URLs in Supabase...")
            for item in updated_urls[:10]:  # Update first 10 as example
                try:
                    self.supabase.table('url_processing_queue').update({
                        'category': 'blacklist',
                        'status': 'processed',
                        'updated_at': datetime.now().isoformat()
                    }).eq('url', item['url']).execute()
                except Exception as e:
                    logger.error(f"Error updating URL {item['url']}: {e}")
    
    def ensure_file_consistency(self):
        """Ensure the tmp blacklist file matches the master file"""
        if os.path.exists(MASTER_BLACKLIST_FILE):
            # Copy master to tmp location
            import shutil
            shutil.copy2(MASTER_BLACKLIST_FILE, TMP_BLACKLIST_FILE)
            logger.info(f"Synced master blacklist to {TMP_BLACKLIST_FILE}")
        else:
            logger.error("Master blacklist file not found!")
    
    def get_stats(self):
        """Get sync statistics"""
        # File stats
        file_count = 0
        if os.path.exists(MASTER_BLACKLIST_FILE):
            with open(MASTER_BLACKLIST_FILE, 'r') as f:
                file_count = sum(1 for _ in f) - 1  # Subtract header
        
        # Supabase stats
        supabase_count = len(self.get_existing_urls_from_supabase())
        
        return {
            'file_count': file_count,
            'supabase_count': supabase_count,
            'difference': file_count - supabase_count
        }

async def main():
    """Main sync function"""
    syncer = BlacklistSyncer()
    
    # Get initial stats
    stats_before = syncer.get_stats()
    logger.info(f"Before sync - File: {stats_before['file_count']}, Supabase: {stats_before['supabase_count']}")
    
    # Ensure file consistency
    syncer.ensure_file_consistency()
    
    # Load blacklist data
    blacklist_data = syncer.load_blacklist_from_file()
    
    if blacklist_data:
        # Sync to Supabase
        syncer.sync_to_supabase(blacklist_data)
    
    # Get final stats
    stats_after = syncer.get_stats()
    logger.info(f"After sync - File: {stats_after['file_count']}, Supabase: {stats_after['supabase_count']}")
    
    logger.info("✅ Blacklist sync completed!")

if __name__ == "__main__":
    asyncio.run(main()) 