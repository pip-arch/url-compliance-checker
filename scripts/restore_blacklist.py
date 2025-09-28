#!/usr/bin/env python3
"""
Script to restore the consolidated blacklist from the JSON export
"""
import csv
import json
import os
from datetime import datetime

# Path to the JSON export file
LATEST_EXPORT = "./data/tmp/blacklist_export_20250417_125450.json"
CONSOLIDATED_FILE = "./data/tmp/blacklist_consolidated.csv"

def restore_blacklist():
    print(f"Restoring blacklist from {LATEST_EXPORT} to {CONSOLIDATED_FILE}")
    
    # Read the JSON export
    with open(LATEST_EXPORT, "r") as f:
        blacklist_data = json.load(f)
    
    # Create a new consolidated file with headers
    with open(CONSOLIDATED_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "URL",
            "Main Domain",
            "Reason",
            "Confidence",
            "Category",
            "Compliance Issues",
            "Batch ID",
            "Timestamp"
        ])
        
        # Add each blacklisted domain
        for domain, data in blacklist_data.items():
            for url in data["urls"]:
                reason = list(data["reasons"])[0] if data["reasons"] else "N/A"
                confidence = data.get("confidence", 0.0)
                # Use the first category or default to 'blacklist'
                category = list(data["categories"])[0] if data["categories"] else "blacklist"
                compliance_issues = list(data["compliance_issues"])
                batch_id = list(data["batch_ids"])[0] if data["batch_ids"] else ""
                timestamp = data.get("first_added", datetime.now().isoformat())
                
                # Write row to consolidated file
                writer.writerow([
                    url,
                    domain,
                    reason,
                    confidence,
                    category,
                    ",".join(compliance_issues),
                    batch_id,
                    timestamp
                ])
    
    print(f"Restored {len(blacklist_data)} domains to consolidated blacklist file")

if __name__ == "__main__":
    restore_blacklist() 