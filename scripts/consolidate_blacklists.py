#!/usr/bin/env python3
"""
Consolidate blacklist files into a single file, preserving unique entries
"""

import csv
import os
import logging
import shutil
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/blacklist_consolidation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blacklist_consolidation")

# Define file paths
CONSOLIDATED_BLACKLIST = "data/tmp/blacklist_consolidated.csv"
DIRECT_BLACKLIST = "data/tmp/blacklist_direct.csv"
BACKUP_DIR = "data/tmp/backups"

def backup_file(file_path):
    """Create a backup of the specified file"""
    if not os.path.exists(file_path):
        logger.warning(f"Cannot backup non-existent file: {file_path}")
        return False
        
    # Create backup directory if it doesn't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Create backup filename with timestamp
    filename = os.path.basename(file_path)
    backup_name = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return False

def load_blacklist_urls(file_path):
    """Load URLs from a blacklist file into a dictionary with URLs as keys"""
    urls = {}
    
    if not os.path.exists(file_path):
        logger.warning(f"Blacklist file does not exist: {file_path}")
        return urls
        
    try:
        with open(file_path, "r", newline='') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Get headers
            
            url_index = headers.index("URL") if "URL" in headers else 0
            
            for row in reader:
                if row and len(row) > url_index:
                    url = row[url_index].strip()
                    # IMPORTANT: Accept ALL URLs, regardless of format
                    if url:  # Only check if URL is non-empty
                        urls[url] = row  # Store the whole row
        
        logger.info(f"Loaded {len(urls)} URLs from {file_path}")
        return urls
    except Exception as e:
        logger.error(f"Error loading URLs from {file_path}: {e}")
        return urls

def consolidate_blacklists():
    """Consolidate multiple blacklist files into one file"""
    # First, create backups of existing files
    if os.path.exists(CONSOLIDATED_BLACKLIST):
        backup_file(CONSOLIDATED_BLACKLIST)
    
    if os.path.exists(DIRECT_BLACKLIST):
        backup_file(DIRECT_BLACKLIST)
    
    # Safety check - count lines in file before processing
    consolidated_line_count = 0
    if os.path.exists(CONSOLIDATED_BLACKLIST):
        with open(CONSOLIDATED_BLACKLIST, 'r') as f:
            consolidated_line_count = sum(1 for _ in f) - 1  # Subtract header
        logger.info(f"Pre-consolidation line count: {consolidated_line_count} URLs in {CONSOLIDATED_BLACKLIST}")
    
    # Load URLs from both files
    consolidated_urls = load_blacklist_urls(CONSOLIDATED_BLACKLIST)
    direct_urls = load_blacklist_urls(DIRECT_BLACKLIST)
    
    # SAFETY CHECK: Ensure we haven't lost URLs during loading
    if len(consolidated_urls) < consolidated_line_count:
        logger.error(f"CRITICAL SAFETY ERROR: Loaded {len(consolidated_urls)} URLs but file has {consolidated_line_count} URLs")
        logger.error(f"Aborting consolidation to prevent data loss. Restore from backup if needed.")
        return False, 0, 0
    
    # Combine URLs, with direct_urls taking precedence if there are duplicates
    for url, row in direct_urls.items():
        if url not in consolidated_urls:
            consolidated_urls[url] = row
    
    # Create or update the consolidated file
    try:
        # Determine field names - use those from CONSOLIDATED_BLACKLIST if it exists,
        # otherwise use a default set that should work with all files
        field_names = ["URL", "Main Domain", "Reason", "Confidence", "Category", 
                      "Compliance Issues", "Analysis Method", "Batch ID", "Timestamp"]
        
        if os.path.exists(CONSOLIDATED_BLACKLIST):
            with open(CONSOLIDATED_BLACKLIST, "r", newline='') as f:
                reader = csv.reader(f)
                existing_headers = next(reader)
                # Use existing headers if they exist and seem valid
                if len(existing_headers) >= 5:  # Sanity check
                    field_names = existing_headers
        
        # Create a new consolidated file
        temp_file = f"{CONSOLIDATED_BLACKLIST}.temp"
        with open(temp_file, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(field_names)
            
            # Write all URLs
            for row in consolidated_urls.values():
                # Handle case where row might have fewer columns than field_names
                if len(row) < len(field_names):
                    row.extend([''] * (len(field_names) - len(row)))
                writer.writerow(row[:len(field_names)])  # Trim if needed
        
        # SAFETY CHECK: Count lines in the new file before replacing
        with open(temp_file, 'r') as f:
            new_line_count = sum(1 for _ in f) - 1  # Subtract header
        
        if new_line_count < consolidated_line_count:
            logger.error(f"CRITICAL ERROR: New file has {new_line_count} URLs but original has {consolidated_line_count}")
            logger.error("Aborting to prevent data loss!")
            os.remove(temp_file)  # Delete the temp file
            return False, 0, 0
            
        # Replace the old file with the new one
        shutil.move(temp_file, CONSOLIDATED_BLACKLIST)
        logger.info(f"Successfully consolidated {len(consolidated_urls)} unique URLs into {CONSOLIDATED_BLACKLIST}")
        
        # Return success and counts
        return True, len(consolidated_urls), len(direct_urls)
    
    except Exception as e:
        logger.error(f"Error consolidating blacklists: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)  # Clean up temp file if there was an error
        return False, 0, 0

def update_scripts_to_use_consolidated_file():
    """Update scripts to use the consolidated blacklist file"""
    # List of scripts to update
    scripts = [
        "url_analyzer_direct.py",
        "reanalyze_remaining.py",
        "reanalyze_remaining_with_fallback.py",
        "reanalyze_remaining_with_openai.py"
    ]
    
    for script in scripts:
        if not os.path.exists(script):
            logger.warning(f"Script not found: {script}")
            continue
            
        # Backup the script
        backup_file(script)
        
        try:
            # Read the script content
            with open(script, "r") as f:
                content = f.read()
            
            # Update the blacklist file path if needed
            if 'blacklist_file = "data/tmp/blacklist_direct.csv"' in content:
                content = content.replace(
                    'blacklist_file = "data/tmp/blacklist_direct.csv"',
                    'blacklist_file = "data/tmp/blacklist_consolidated.csv"'
                )
                logger.info(f"Updated blacklist file path in {script}")
            elif 'data/tmp/blacklist_' in content and 'blacklist_consolidated.csv' not in content:
                logger.warning(f"Script {script} has a different blacklist file format, manual review recommended")
            
            # Write the updated content
            with open(script, "w") as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"Error updating script {script}: {e}")

if __name__ == "__main__":
    logger.info("Starting blacklist consolidation process")
    
    # Consolidate blacklists
    success, total_urls, direct_urls = consolidate_blacklists()
    
    if success:
        logger.info(f"Consolidation complete: {total_urls} total unique URLs (including {direct_urls} from direct blacklist)")
        
        # Update scripts to use consolidated file
        update_scripts_to_use_consolidated_file()
    else:
        logger.error("Consolidation failed") 