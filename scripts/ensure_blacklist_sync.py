#!/usr/bin/env python3
"""
Patch the URL processor to ensure blacklisted URLs are saved to both
the master blacklist file and Supabase during processing.
"""
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.url_processor import URLProcessor
from app.models.url import URLStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
MASTER_BLACKLIST_FILE = "data/outputs/blacklists/blacklist_consolidated_master.csv"
TMP_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"

# Monkey-patch the URL processor to ensure dual saving
original_process_urls = URLProcessor.process_urls

async def patched_process_urls(self, urls, batch_id):
    """Patched version that ensures blacklisted URLs are saved to both locations"""
    # Call original method
    result = await original_process_urls(self, urls, batch_id)
    
    # After processing, ensure blacklist sync
    logger.info("Ensuring blacklist synchronization...")
    
    # Copy from tmp to master location
    import shutil
    import csv
    
    if os.path.exists(TMP_BLACKLIST_FILE):
        # Read tmp file
        blacklisted_urls = []
        with open(TMP_BLACKLIST_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                blacklisted_urls.append(row)
        
        # Ensure master directory exists
        os.makedirs(os.path.dirname(MASTER_BLACKLIST_FILE), exist_ok=True)
        
        # Write to master file (append mode to preserve existing)
        file_exists = os.path.exists(MASTER_BLACKLIST_FILE)
        with open(MASTER_BLACKLIST_FILE, 'a' if file_exists else 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['URL', 'Main Domain', 'Reason', 'Batch ID', 'Timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            # Write new blacklisted URLs
            new_count = 0
            for row in blacklisted_urls:
                # Check if this is a new entry (simple check based on batch_id)
                if row.get('Batch ID') == batch_id:
                    writer.writerow(row)
                    new_count += 1
            
            if new_count > 0:
                logger.info(f"Added {new_count} new blacklisted URLs to master file")
        
        # Also sync to Supabase if available
        try:
            from scripts.sync_blacklist_to_supabase import BlacklistSyncer
            syncer = BlacklistSyncer()
            syncer.sync_to_supabase(blacklisted_urls)
            logger.info("✅ Synced blacklist to Supabase")
        except Exception as e:
            logger.warning(f"Could not sync to Supabase: {e}")
    
    return result

# Apply the patch
URLProcessor.process_urls = patched_process_urls
logger.info("✅ URL processor patched for dual blacklist saving")

if __name__ == "__main__":
    print("This script patches the URL processor to ensure blacklist sync.")
    print("Import this module before running the URL processor.") 