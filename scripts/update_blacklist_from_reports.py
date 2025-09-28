#!/usr/bin/env python3
"""
Update blacklist CSV file from compliance reports.
This ensures all URLs categorized as blacklist by the compliance checker
are saved to the consolidated blacklist file.
"""
import csv
import logging
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Set
from app.models.report import ComplianceReport, URLCategory

logger = logging.getLogger(__name__)

CONSOLIDATED_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"

def load_existing_blacklist_urls() -> Set[str]:
    """Load already blacklisted URLs to avoid duplicates."""
    existing_urls = set()
    try:
        with open(CONSOLIDATED_BLACKLIST_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row:  # Ensure row is not empty
                    existing_urls.add(row[0])  # URL is in first column
    except FileNotFoundError:
        # Create file with headers if it doesn't exist
        with open(CONSOLIDATED_BLACKLIST_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Main Domain", "Reason", "Confidence", "Category", "Compliance Issues", "Batch ID", "Timestamp"])
    except Exception as e:
        logger.error(f"Error loading existing blacklist: {str(e)}")
    return existing_urls

def extract_main_domain(url: str) -> str:
    """Extract main domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Get main domain (e.g., example.com from www.example.com)
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
    except:
        return ""

async def update_blacklist_from_report(report: ComplianceReport) -> int:
    """
    Update the blacklist CSV file with URLs from a compliance report.
    Returns the number of new blacklisted URLs added.
    """
    existing_urls = load_existing_blacklist_urls()
    new_blacklist_count = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(CONSOLIDATED_BLACKLIST_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            
            # Process each URL report
            for url_report in report.url_reports:
                if url_report.category == URLCategory.BLACKLIST and url_report.url not in existing_urls:
                    main_domain = extract_main_domain(url_report.url)
                    
                    # Extract confidence and compliance issues from AI analysis if available
                    confidence = 0.9  # Default high confidence
                    compliance_issues = ""
                    
                    if url_report.ai_analysis:
                        confidence = url_report.ai_analysis.confidence
                        compliance_issues = ", ".join(url_report.ai_analysis.compliance_issues) if isinstance(url_report.ai_analysis.compliance_issues, list) else str(url_report.ai_analysis.compliance_issues)
                    
                    # Write to CSV
                    writer.writerow([
                        url_report.url,
                        main_domain,
                        f"{url_report.analysis_method}: {url_report.ai_analysis.explanation if url_report.ai_analysis else 'Compliance violation'}",
                        confidence,
                        "blacklist",
                        compliance_issues,
                        report.batch_id,
                        timestamp
                    ])
                    
                    new_blacklist_count += 1
                    existing_urls.add(url_report.url)  # Track to avoid duplicates in same run
                    logger.info(f"Added to blacklist: {url_report.url} (domain: {main_domain})")
        
        if new_blacklist_count > 0:
            logger.info(f"✅ Added {new_blacklist_count} new URLs to blacklist file")
            
    except Exception as e:
        logger.error(f"Error updating blacklist file: {str(e)}")
        
    return new_blacklist_count 