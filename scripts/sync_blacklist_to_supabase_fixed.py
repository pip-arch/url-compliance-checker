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
from typing import List, Dict, Set

# Load environment variables FIRST
load_dotenv()

# Import supabase after loading env
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Debug log
logger.info(f"SUPABASE_URL: {SUPABASE_URL}")
logger.info(f"SUPABASE_KEY: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "SUPABASE_KEY: None")

# File paths
MASTER_BLACKLIST_FILE = "data/outputs/blacklists/blacklist_consolidated_master.csv"
TMP_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"

class BlacklistSyncer:
    def __init__(self):
        if not SUPABASE_KEY:
            raise ValueError("SUPABASE_ANON_KEY not found in environment")
        if not SUPABASE_URL:
            raise ValueError("SUPABASE_URL not found in environment")
        
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
    
    def sync_to_supabase(self, blacklist_data: List[Dict]):
        """Sync blacklisted URLs to Supabase"""
        if not blacklist_data:
            logger.info("No blacklist data to sync")
            return
        
        # Prepare records for url_processing_queue
        batch_size = 100
        total_synced = 0
        
        for i in range(0, len(blacklist_data), batch_size):
            batch = blacklist_data[i:i+batch_size]
            
            # Prepare records
            records = []
            for item in batch:
                # Extract domain info
                from urllib.parse import urlparse
                parsed = urlparse(item['url'])
                domain = parsed.netloc
                
                records.append({
                    'url': item['url'],
                    'domain': domain,
                    'main_domain': item['main_domain'] or domain,
                    'source_file': 'blacklist_import',
                    'priority': 0,
                    'status': 'blacklisted',
                    'retry_count': 0,
                    'created_at': item['timestamp'],
                    'updated_at': datetime.now().isoformat()
                })
            
            try:
                # Upsert to url_processing_queue
                result = self.supabase.table('url_processing_queue').upsert(
                    records,
                    on_conflict='url'
                ).execute()
                
                total_synced += len(batch)
                logger.info(f"Synced batch of {len(batch)} URLs (total: {total_synced}/{len(blacklist_data)})")
                
            except Exception as e:
                logger.error(f"Error syncing batch to Supabase: {e}")
    
    def ensure_file_consistency(self):
        """Ensure the tmp blacklist file matches the master file"""
        if os.path.exists(MASTER_BLACKLIST_FILE):
            # Copy master to tmp location
            import shutil
            shutil.copy2(MASTER_BLACKLIST_FILE, TMP_BLACKLIST_FILE)
            logger.info(f"Synced master blacklist to {TMP_BLACKLIST_FILE}")
        else:
            logger.error("Master blacklist file not found!")

async def main():
    """Main sync function"""
    try:
        syncer = BlacklistSyncer()
        
        # Ensure file consistency first
        syncer.ensure_file_consistency()
        
        # Load blacklist data
        blacklist_data = syncer.load_blacklist_from_file()
        
        if blacklist_data:
            # Sync to Supabase
            syncer.sync_to_supabase(blacklist_data)
        
        logger.info("✅ Blacklist sync completed!")
        
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 