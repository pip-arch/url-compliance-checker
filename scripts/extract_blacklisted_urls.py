#!/usr/bin/env python3
"""
Script to extract all blacklisted URLs from logs
"""
import re
import logging
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

def extract_blacklisted_urls():
    """Extract all blacklisted URLs from logs"""
    # Patterns to match in logs
    blacklist_patterns = [
        r"Domain blacklisted: (.+)",
        r"url_report\.category == URLCategory\.BLACKLIST.*url: (https?://[^\s,\"]+)",
        r"is_blacklisted = True.*url: (https?://[^\s,\"]+)",
        r"Category: URLCategory\.BLACKLIST.*URL: (https?://[^\s,\"]+)",
        r"Added to blacklist: (https?://[^\s,\"]+)",
        r"Blacklisted URL: (https?://[^\s,\"]+)",
        r"blacklisted_urls\[\d+\]: (https?://[^\s,\"]+)"
    ]

    # Read logs for compliance reports listing blacklisted count
    compliance_reports = {}
    try:
        with open("data/real_processing.log", "r") as f:
            for line in f:
                if "Compliance report" in line and "blacklisted" in line:
                    match = re.search(r"Compliance report (report-[^ ]+) stats: (\d+) blacklisted", line)
                    if match:
                        report_id = match.group(1)
                        blacklist_count = int(match.group(2))
                        if blacklist_count > 0:
                            compliance_reports[report_id] = blacklist_count
                            logger.info(f"Found compliance report {report_id} with {blacklist_count} blacklisted URLs")
    except Exception as e:
        logger.error(f"Error reading logs for compliance reports: {e}")

    # Read the logs for URL analysis results
    blacklisted_urls_in_logs = set()
    try:
        with open("data/real_processing.log", "r") as f:
            for line in f:
                # Check for direct mentions of blacklisted URLs
                for pattern in blacklist_patterns:
                    match = re.search(pattern, line)
                    if match:
                        url = match.group(1)
                        if url.startswith("http"):
                            blacklisted_urls_in_logs.add(url)
                
                # Look for LLM analysis with blacklist categorization
                if "Successfully analyzed URL" in line:
                    url_match = re.search(r"Successfully analyzed URL (https?://[^\s]+)", line)
                    if url_match:
                        url = url_match.group(1)
                        # Check if the URL appears in a later log entry with blacklist category
                        for next_line in f:
                            if "URLCategory.BLACKLIST" in next_line and url in next_line:
                                blacklisted_urls_in_logs.add(url)
                                break
                            # Stop if we hit another URL analysis or end of relevant logs
                            if "Successfully analyzed URL" in next_line or len(next_line.strip()) == 0:
                                break
    except Exception as e:
        logger.error(f"Error reading logs for URL analysis: {e}")

    # Read the blacklist file
    blacklisted_urls_in_file = set()
    try:
        with open("data/tmp/blacklist_consolidated.csv", "r") as f:
            reader = csv.reader(f)
            # Skip header
            next(reader)
            for row in reader:
                if not row:
                    continue
                url = row[0].strip() if row else ""
                if url and url.startswith("http"):
                    blacklisted_urls_in_file.add(url)
    except Exception as e:
        logger.error(f"Error reading blacklist file: {e}")

    # Try to extract URLs from all batch reports
    logger.info(f"Checking for batch reports in the data folder...")
    import os
    batch_report_urls = set()
    for filename in os.listdir("data"):
        if filename.startswith("report-real_batch_") and filename.endswith(".json"):
            try:
                import json
                with open(os.path.join("data", filename), "r") as f:
                    data = json.load(f)
                    for report in data.get("url_reports", []):
                        if report.get("category") == "blacklist":
                            url = report.get("url")
                            if url:
                                batch_report_urls.add(url)
                                logger.info(f"Found blacklisted URL in report {filename}: {url}")
            except Exception as e:
                logger.error(f"Error reading batch report {filename}: {e}")

    # Compare
    logger.info(f"Found {len(blacklisted_urls_in_logs)} blacklisted URLs in logs")
    logger.info(f"Found {len(blacklisted_urls_in_file)} blacklisted URLs in blacklist file")
    logger.info(f"Found {len(batch_report_urls)} blacklisted URLs in batch reports")
    logger.info(f"Found {len(compliance_reports)} compliance reports with blacklisted URLs")
    total_blacklisted = sum(compliance_reports.values())
    logger.info(f"Total blacklisted URLs mentioned in compliance reports: {total_blacklisted}")

    # Print URLs missing from blacklist
    missing_urls = blacklisted_urls_in_logs - blacklisted_urls_in_file
    missing_urls.update(batch_report_urls - blacklisted_urls_in_file)
    logger.info(f"Found {len(missing_urls)} blacklisted URLs missing from blacklist file")

    # Print top 20 blacklisted URLs from logs
    logger.info("Top 20 blacklisted URLs from logs:")
    for i, url in enumerate(list(blacklisted_urls_in_logs)[:20]):
        logger.info(f"{i+1}. {url}")

    # Print top 20 blacklisted URLs from batch reports
    logger.info("Top 20 blacklisted URLs from batch reports:")
    for i, url in enumerate(list(batch_report_urls)[:20]):
        logger.info(f"{i+1}. {url}")

    # Print top 20 missing URLs
    logger.info("Top 20 URLs missing from blacklist file:")
    for i, url in enumerate(list(missing_urls)[:20]):
        logger.info(f"{i+1}. {url}")

    # Create a combined list from all sources for potential addition to blacklist
    all_blacklisted = blacklisted_urls_in_logs.union(batch_report_urls)
    logger.info(f"Total unique blacklisted URLs found across all sources: {len(all_blacklisted)}")

    return all_blacklisted, blacklisted_urls_in_file, missing_urls

if __name__ == "__main__":
    extract_blacklisted_urls() 