#!/usr/bin/env python
import os
import csv
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def check_url_against_blacklist(url, blacklist_file="data/tmp/blacklist_consolidated.csv"):
    """
    Check if the URL or its domain is in the blacklist.
    Returns (is_blacklisted, reason) tuple.
    """
    domain = extract_domain(url)
    
    if not os.path.exists(blacklist_file):
        logger.warning(f"Blacklist file {blacklist_file} does not exist")
        return False, None
    
    try:
        with open(blacklist_file, "r") as f:
            reader = csv.reader(f)
            header = next(reader)  # skip header
            
            url_index = 0  # Default to first column
            reason_index = 2  # Default to third column
            domain_index = None  # For domain column if it exists
            
            # Find the proper column indices
            if "URL" in header:
                url_index = header.index("URL")
            if "Reason" in header:
                reason_index = header.index("Reason")
            if "Main Domain" in header:
                domain_index = header.index("Main Domain")
            
            for row in reader:
                if len(row) <= max(url_index, reason_index):
                    continue  # Skip rows that don't have enough columns
                
                blacklisted_url = row[url_index].strip()
                
                # Check for exact URL match
                if blacklisted_url.lower() == url.lower():
                    return True, row[reason_index] if reason_index < len(row) else "Unknown"
                
                # Check for domain match from Main Domain column if available
                if domain_index is not None and domain_index < len(row):
                    blacklisted_domain = row[domain_index].strip()
                    if blacklisted_domain and blacklisted_domain.lower() == domain.lower():
                        return True, f"Domain in blacklist: {blacklisted_domain}"
                
                # Fallback: extract domain from URL if Main Domain column not available
                try:
                    blacklisted_url_domain = extract_domain(blacklisted_url)
                    if blacklisted_url_domain and blacklisted_url_domain.lower() == domain.lower():
                        return True, f"Domain in blacklist: {blacklisted_url_domain}"
                except Exception as e:
                    logger.debug(f"Error extracting domain from {blacklisted_url}: {e}")
                    pass  # Skip if we can't parse the domain
                
        return False, None
    except Exception as e:
        logger.error(f"Error checking blacklist: {e}")
        return False, None 