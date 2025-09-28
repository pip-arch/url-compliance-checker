import os
import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import asyncio
import time
import csv

# Import services
from app.services.crawler import crawler_service
from app.services.database import database_service
from app.services.vector_db import pinecone_service
from app.services.crawlers.firecrawl_service import FirecrawlService
from app.models.url import URL, URLBatch, URLStatus, URLFilterReason, URLContent, URLContentMatch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
OWN_DOMAINS = os.getenv("OWN_DOMAINS", "admiralmarkets.com,admirals.com").split(",")
REGULATOR_DOMAINS = os.getenv("REGULATOR_DOMAINS", "cysec.gov.cy,fca.org.uk").split(",")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "2"))
MAX_URLS_PER_BATCH = int(os.getenv("MAX_URLS_PER_BATCH", "100"))

# Consolidated blacklist file path
CONSOLIDATED_BLACKLIST_FILE = "data/tmp/blacklist_consolidated.csv"


class URLProcessor:
    """
    Main class for processing URLs:
    1. Validate and filter URLs
    2. Crawl valid URLs using Firecrawl
    3. Extract content and context around "admiralmarkets" mentions
    4. Store content in Pinecone vector database
    """
    
    def __init__(self):
        """Initialize URL processor with services."""
        self.crawler = crawler_service
        self.db = database_service
        self.vector_db = pinecone_service
        self.firecrawl = FirecrawlService()
        self.blacklisted_domains = self._load_blacklisted_domains()
        logger.info(f"URL processor initialized with {len(self.blacklisted_domains)} blacklisted domains")
    
    def _load_blacklisted_domains(self) -> set:
        """Load blacklisted domains from the consolidated blacklist file."""
        blacklisted_domains = set()
        try:
            if os.path.exists(CONSOLIDATED_BLACKLIST_FILE):
                with open(CONSOLIDATED_BLACKLIST_FILE, "r", newline="") as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    for row in reader:
                        if len(row) >= 2:  # URL, Main Domain, Reason
                            main_domain = row[1].strip().lower()
                            if main_domain:
                                blacklisted_domains.add(main_domain)
                logger.info(f"Loaded {len(blacklisted_domains)} blacklisted domains from {CONSOLIDATED_BLACKLIST_FILE}")
            else:
                # Create file with headers if it doesn't exist
                with open(CONSOLIDATED_BLACKLIST_FILE, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["URL", "Main Domain", "Reason", "Batch ID", "Timestamp"])
                logger.info(f"Created new blacklist file: {CONSOLIDATED_BLACKLIST_FILE}")
        except Exception as e:
            logger.error(f"Error loading blacklisted domains: {str(e)}")
        return blacklisted_domains
    
    async def process_urls(self, urls: List[str], batch_id: str) -> Dict[str, Any]:
        """
        Process a batch of URLs.
        """
        logger.info(f"Processing batch {batch_id} with {len(urls)} URLs")
        
        # Create batch record
        batch = URLBatch(
            id=batch_id,
            url_count=len(urls),
            status=URLStatus.PROCESSING
        )
        await self.db.save_batch(batch)
        
        # Track statistics
        already_processed_count = 0
        blacklisted_count = 0
        
        # Deduplicate: skip URLs already processed or whose main domain is blacklisted
        processed_urls = set()
        all_urls = []
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            main_domain = ".".join(domain.split(".")[-2:]) if len(domain.split(".")) > 1 else domain
            
            # Check if main domain is already blacklisted
            if main_domain in self.blacklisted_domains:
                logger.info(f"Skipping {url}: domain {main_domain} is blacklisted")
                blacklisted_count += 1
                continue
                
            # Check if URL exists in database and if it's already processed with content
            existing_url = await self._get_url_by_url_string(url)
            # Also check if URL exists in Pinecone
            in_pinecone = await self.url_exists_in_pinecone(url)
            
            if (existing_url and existing_url.status == URLStatus.PROCESSED and 
                hasattr(existing_url, 'content') and existing_url.content) or in_pinecone:
                logger.info(f"URL {url} already processed, skipping recrawling step")
                already_processed_count += 1
                # Add to processed URLs that don't need recrawling
                processed_urls.add(url)
                continue
                
            # Check if URL is already processed (older implementation)
            loop = asyncio.get_event_loop()
            existing = await loop.run_in_executor(
                None, self.db._fetch_one, "SELECT status FROM urls WHERE url = ?", (url,)
            )
            if existing and existing["status"] == URLStatus.PROCESSED.value:
                continue
            
            all_urls.append((url, domain, main_domain))
        
        # Initialize URL records
        url_records = []
        for url, domain, main_domain in all_urls:
            url_record = URL(
                id=str(uuid.uuid4()),
                url=url,
                batch_id=batch_id,
                status=URLStatus.PENDING
            )
            url_records.append(url_record)
            await self.db.save_url(url_record)
        
        # Process URLs with filtering
        filtered_urls = self.filter_urls(url_records)
        
        # Crawl and process valid URLs
        await self.crawl_urls(filtered_urls)
        
        # Get all processed URLs for this batch
        processed = await self.db.get_processed_urls_by_batch(batch_id)
        
        # Count blacklisted subdomains per main domain
        domain_blacklist_count = {}
        url_to_domain = {}
        newly_blacklisted_domains = set()
        
        for url in processed:
            parsed = urlparse(url.url)
            domain = parsed.netloc.lower()
            main_domain = ".".join(domain.split(".")[-2:]) if len(domain.split(".")) > 1 else domain
            url_to_domain[url.url] = main_domain
            
            # Check for category in a safer way by trying to get report from database
            try:
                report = await self.db.get_url_report_by_url_id(url.id)
                if report and report.category == 'blacklist':
                    domain_blacklist_count.setdefault(main_domain, 0)
                    domain_blacklist_count[main_domain] += 1
            except Exception as e:
                logger.error(f"Error checking URL report category: {str(e)}")
                
            # Old method with hasattr check that's causing the error
            # if url.status == URLStatus.PROCESSED and hasattr(url, 'category') and getattr(url, 'category', None) == 'blacklist':
            #     domain_blacklist_count.setdefault(main_domain, 0)
            #     domain_blacklist_count[main_domain] += 1
        
        # Blacklist main domains with >=3 blacklisted subdomains
        for main_domain, count in domain_blacklist_count.items():
            if count >= 3 and main_domain not in self.blacklisted_domains:
                newly_blacklisted_domains.add(main_domain)
                self.blacklisted_domains.add(main_domain)
                logger.info(f"Blacklisting domain {main_domain} with {count} non-compliant subdomains")
        
        # Mark all URLs from blacklisted main domains as blacklisted
        for url in processed:
            main_domain = url_to_domain.get(url.url)
            if main_domain in self.blacklisted_domains:
                url.status = URLStatus.PROCESSED
                # Don't directly set category on URL object
                # url.category = 'blacklist'
                await self.db.update_url(url)
                
                # Create or update URL report with blacklist category
                try:
                    report = await self.db.get_url_report_by_url_id(url.id)
                    if report:
                        report.category = 'blacklist'
                        await self.db.update_url_report(report)
                    else:
                        # Create minimal report for blacklisted URL if none exists
                        from app.models.report import URLReport, URLCategory
                        new_report = URLReport(
                            url_id=url.id,
                            url=url.url,
                            category=URLCategory.BLACKLIST,
                            analysis_method="domain_blacklist"
                        )
                        await self.db.save_url_report(new_report)
                except Exception as e:
                    logger.error(f"Error updating URL report for blacklisted domain: {str(e)}")
        
        # Update consolidated blacklist file with new entries
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        blacklist_count = 0
        try:
            with open(CONSOLIDATED_BLACKLIST_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                # Add entry for each URL from blacklisted domains
                for url in processed:
                    main_domain = url_to_domain.get(url.url)
                    is_blacklisted = False
                    
                    # Check if we have a report indicating this is blacklisted
                    try:
                        report = await self.db.get_url_report_by_url_id(url.id)
                        if report and report.category == 'blacklist':
                            is_blacklisted = True
                    except Exception:
                        pass
                        
                    if (is_blacklisted or main_domain in newly_blacklisted_domains) and main_domain in self.blacklisted_domains:
                        writer.writerow([url.url, main_domain, "blacklist", batch_id, current_timestamp])
                        blacklist_count += 1
                        # Add explicit blacklist logging similar to direct_analysis script
                        logger.info(f"Blacklisted URL: {url.url} (domain: {main_domain})")
            
            # Add explicit logging about writes to the blacklist file
            if blacklist_count > 0:
                logger.info(f"Added {blacklist_count} new blacklisted URLs to {CONSOLIDATED_BLACKLIST_FILE}")
        except Exception as e:
            logger.error(f"Error updating blacklist file: {e}")
        
        # Update batch status
        batch.processed_count = len(url_records)
        batch.status = URLStatus.PROCESSED
        await self.db.update_batch(batch)
        
        logger.info(f"Batch {batch_id} processing completed")
        
        return {
            "batch_id": batch_id,
            "total_urls": len(urls),
            "processed_urls": len(filtered_urls),
            "already_processed": already_processed_count,
            "blacklisted_skipped": blacklisted_count,
            "skipped_urls": len(urls) - len(filtered_urls),
            "status": URLStatus.PROCESSED,
            "blacklisted_domains": len(self.blacklisted_domains),
            "newly_blacklisted": len(newly_blacklisted_domains)
        }
    
    def filter_urls(self, url_records: List[URL]) -> List[URL]:
        """
        Filter URLs based on criteria:
        - Skip own domains (admiralmarkets.com, etc.)
        - Skip regulator domains (cysec.gov.cy, etc.)
        - Skip invalid URLs
        """
        filtered_urls = []
        
        for url_record in url_records:
            # Check if URL is valid
            try:
                parsed_url = urlparse(url_record.url)
                if not parsed_url.netloc:
                    url_record.status = URLStatus.SKIPPED
                    url_record.filter_reason = URLFilterReason.INVALID_URL
                    asyncio.create_task(self.db.update_url(url_record))
                    continue
                
                domain = parsed_url.netloc.lower()
                
                # Check if URL is from own domain
                if any(own_domain in domain for own_domain in OWN_DOMAINS):
                    url_record.status = URLStatus.SKIPPED
                    url_record.filter_reason = URLFilterReason.OWN_DOMAIN
                    asyncio.create_task(self.db.update_url(url_record))
                    continue
                
                # Check if URL is from regulator domain
                if any(reg_domain in domain for reg_domain in REGULATOR_DOMAINS):
                    url_record.status = URLStatus.SKIPPED
                    url_record.filter_reason = URLFilterReason.REGULATOR
                    asyncio.create_task(self.db.update_url(url_record))
                    continue
                
                # URL passed all filters
                filtered_urls.append(url_record)
                
            except Exception as e:
                logger.error(f"Error filtering URL {url_record.url}: {str(e)}")
                url_record.status = URLStatus.FAILED
                url_record.error = str(e)
                asyncio.create_task(self.db.update_url(url_record))
        
        logger.info(f"Filtered {len(filtered_urls)} URLs from {len(url_records)} total")
        return filtered_urls
    
    async def crawl_urls(self, url_records: List[URL]) -> None:
        """
        Crawl URLs using the crawler service and process content.
        """
        firecrawl_successes = 0
        total_crawled = 0
        for url_record in url_records:
            try:
                # Update URL status
                url_record.status = URLStatus.PROCESSING
                await self.db.update_url(url_record)
                
                # Try Firecrawl first, then fall back to generic crawler if needed
                try:
                    firecrawl_result = await self.firecrawl.extract_content(url_record.url)
                    if firecrawl_result.get("success", False):
                        # Check if we should skip analysis due to no Admiral Markets mentions
                        if firecrawl_result.get("skip_analysis", False):
                            logger.info(f"Skipping {url_record.url}: {firecrawl_result.get('skip_reason', 'No Admiral Markets mentions')}")
                            url_record.status = URLStatus.SKIPPED
                            url_record.filter_reason = URLFilterReason.NO_MENTION
                            await self.db.update_url(url_record)
                            continue
                            
                        content = {
                            "title": firecrawl_result.get("metadata", {}).get("title", ""),
                            "full_text": firecrawl_result.get("markdown", ""),
                            "metadata": {
                                **firecrawl_result.get("metadata", {}),
                                "crawled_with": "firecrawl",
                                "duration": firecrawl_result.get("duration", 0),
                                "html_length": len(firecrawl_result.get("html", "")),
                                "admiral_mentions": firecrawl_result.get("admiral_mentions", 0),
                                "mention_contexts": firecrawl_result.get("mention_contexts", [])
                            }
                        }
                        firecrawl_successes += 1
                    else:
                        # Log the error and fall back to generic crawler
                        logger.warning(f"Firecrawl failed for URL {url_record.url}: {firecrawl_result.get('error', 'Unknown error')}")
                        content = await self.crawler.crawl(url_record.url)
                except Exception as e:
                    logger.warning(f"Firecrawl error for URL {url_record.url}: {str(e)}")
                    content = await self.crawler.crawl(url_record.url)
                
                total_crawled += 1
                
                # Extract content - but trust the crawler's mention detection
                url_content = self.extract_content(content, url_record.url)
                
                # Skip if no mentions were found by the crawler
                if not url_content.mentions:
                    url_record.status = URLStatus.SKIPPED
                    url_record.filter_reason = URLFilterReason.NO_MENTION
                    await self.db.update_url(url_record)
                    continue
                
                # Store content in vector database
                embedding_ids = await self.vector_db.store_content(url_content)
                
                # Update mentions with embedding IDs
                for i, mention in enumerate(url_content.mentions):
                    if i in embedding_ids:
                        mention.embedding_id = embedding_ids[i]
                
                # Update URL record with content
                url_record.content = url_content
                url_record.status = URLStatus.PROCESSED
                await self.db.update_url(url_record)
                
                # Respect crawl delay to avoid overloading servers
                await asyncio.sleep(CRAWL_DELAY)
            except Exception as e:
                logger.error(f"Error processing URL {url_record.url}: {str(e)}")
                url_record.status = URLStatus.FAILED
                url_record.error = str(e)
                await self.db.update_url(url_record)
        
        # Log Firecrawl usage summary
        if total_crawled > 0:
            firecrawl_pct = firecrawl_successes / total_crawled * 100
            if firecrawl_pct < 80:
                logger.warning(f"Firecrawl was used for only {firecrawl_pct:.1f}% of URLs in this batch (threshold: 80%)")
            else:
                logger.info(f"Firecrawl was used for {firecrawl_pct:.1f}% of URLs in this batch.")
    
    def extract_content(self, content: Dict[str, Any], url: str) -> URLContent:
        """
        Extract content around "admiralmarkets" or "admirals" mentions.
        If the crawler already found mentions, use those instead of re-scanning.
        """
        url_content = URLContent(
            url=url,
            title=content.get("title", ""),
            full_text=content.get("full_text", ""),
            metadata=content.get("metadata", {})
        )
        
        if not url_content.full_text:
            return url_content
        
        # Check if the crawler already found mentions and provided contexts
        metadata = content.get("metadata", {})
        if metadata.get("admiral_mentions", 0) > 0 and metadata.get("mention_contexts"):
            # Trust the crawler's mention detection and use its contexts
            logger.info(f"Using {len(metadata['mention_contexts'])} Admiral Markets mention contexts from crawler")
            
            for context_info in metadata["mention_contexts"]:
                # Create content match from crawler's context
                content_match = URLContentMatch(
                    text=context_info.get("mention_text", ""),
                    position=context_info.get("position_in_text", {}).get("start", 0),
                    context_before=context_info.get("context", "")[:100],  # First 100 chars as before
                    context_after=context_info.get("context", "")[100:200]  # Next 100 chars as after
                )
                url_content.mentions.append(content_match)
            
            return url_content
        
        # Fallback: scan for mentions if crawler didn't provide them
        # Use the same patterns as the crawlers for consistency
        patterns = [
            r'admiral\s*markets',
            r'admiralmarkets',
            r'admiral\.markets',
            r'admiral-markets',
            r'admirals'  # New brand name
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, url_content.full_text, re.IGNORECASE):
                start_pos = match.start()
                end_pos = match.end()
                
                # Get context around mention (100 characters before and after)
                context_start = max(0, start_pos - 100)
                context_end = min(len(url_content.full_text), end_pos + 100)
                
                context_before = url_content.full_text[context_start:start_pos]
                matched_text = url_content.full_text[start_pos:end_pos]
                context_after = url_content.full_text[end_pos:context_end]
                
                # Create content match
                content_match = URLContentMatch(
                    text=matched_text,
                    position=start_pos,
                    context_before=context_before,
                    context_after=context_after
                )
                
                url_content.mentions.append(content_match)
        
        return url_content
    
    async def _get_url_by_url_string(self, url_string: str) -> Optional[URL]:
        """Get a URL object by its URL string."""
        try:
            loop = asyncio.get_event_loop()
            # First get the URL ID from the database
            url_data = await loop.run_in_executor(
                None, self.db._fetch_one, "SELECT id FROM urls WHERE url = ?", (url_string,)
            )
            
            if not url_data:
                return None
                
            # Then get the full URL object with its ID
            return await self.db.get_url(url_data["id"])
        except Exception as e:
            logger.warning(f"Error getting URL by string: {str(e)}")
            return None
            
    async def url_exists_in_pinecone(self, url: str) -> bool:
        """Check if URL already exists in Pinecone"""
        if not self.vector_db or not self.vector_db.is_initialized:
            return False
            
        try:
            # Search for the URL in Pinecone with a metadata filter
            search_results = await self.vector_db.search_similar_content(url, top_k=5)
            # Check if any of the results have the exact URL
            if search_results:
                for result in search_results:
                    if result.get("url") == url:
                        logger.info(f"Found exact URL match in Pinecone for {url}")
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking Pinecone for URL {url}: {str(e)}")
            return False


# Singleton instance
url_processor = URLProcessor()


async def process_urls(urls: List[str], batch_id: str) -> Dict[str, Any]:
    """Shortcut function to process URLs with the processor."""
    processor = URLProcessor()
    return await processor.process_urls(urls, batch_id) 