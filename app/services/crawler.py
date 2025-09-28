"""
Web crawler service for extracting content from URLs.
Uses a fallback approach: first tries to use Firecrawl API if available,
otherwise falls back to a custom implementation using requests and BeautifulSoup.
"""
import os
import logging
import time
import requests
import random
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import asyncio
import json
import re
import traceback
import httpx
from dotenv import load_dotenv
import aiohttp

# Force reload environment variables to pick up latest changes
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define custom exception class
class CrawlerError(Exception):
    """Custom exception for crawler errors."""
    pass

# Get environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
USER_AGENT = os.getenv("USER_AGENT", "URL-Checker Bot/1.0 (Compliance monitoring for Admiral Markets)")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
# Credit saving settings
USE_MOCK_PERCENTAGE = int(os.getenv("USE_MOCK_PERCENTAGE", "0"))  # Read from environment, default to 0
MOCK_CRAWL_DOMAINS = set(os.getenv("MOCK_CRAWL_DOMAINS", "").split(","))
FIRECRAWL_CREDIT_LIMIT = int(os.getenv("FIRECRAWL_CREDIT_LIMIT", "99000"))  # Stop real API calls after this limit
# Concurrency settings for Firecrawl plan
MAX_CONCURRENT_BROWSERS = int(os.getenv("MAX_CONCURRENT_BROWSERS", "50"))  # 50 for Standard plan


class FirecrawlService:
    """
    Service for crawling web pages and extracting content:
    1. Try to use Firecrawl API if available
    2. Fall back to custom implementation if Firecrawl is not available
    3. Extract title, full text, and relevant content
    """
    
    def __init__(self):
        """Initialize the crawler service."""
        self.use_firecrawl = FIRECRAWL_API_KEY is not None
        self.last_request_time = 0
        self.url_cache = {}  # Cache crawl results by exact URL
        self.credits_used = int(os.getenv("FIRECRAWL_CREDITS_USED", "603"))  # Track credits used
        self.total_requests = 0
        self.real_requests = 0
        self.mock_requests = 0
        # Add Firecrawl API parameters as instance attributes
        self.FIRECRAWL_API_KEY = FIRECRAWL_API_KEY
        self.FIRECRAWL_API_URL = FIRECRAWL_API_URL
        # Concurrency control
        self.browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
        
        logger.info(f"Crawler service initialized. Using Firecrawl: {self.use_firecrawl}")
        logger.info(f"Mock crawl percentage: {USE_MOCK_PERCENTAGE}%")
        logger.info(f"Starting with {self.credits_used} Firecrawl credits used")
        logger.info(f"Credit limit: {FIRECRAWL_CREDIT_LIMIT}")
        logger.info(f"Maximum concurrent browsers: {MAX_CONCURRENT_BROWSERS}")
        
        # Log Firecrawl API key status (safely)
        if self.use_firecrawl:
            key_prefix = FIRECRAWL_API_KEY[:8] if len(FIRECRAWL_API_KEY) > 8 else "****"
            logger.info(f"Firecrawl API key provided. Prefix: {key_prefix}...")
            logger.info(f"Firecrawl API URL: {FIRECRAWL_API_URL}")
        else:
            logger.warning("No Firecrawl API key provided. Will use custom crawler only.")
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """
        Crawl a URL and extract content.
        Decides whether to use real Firecrawl API or custom crawler based on configuration.
        """
        self.total_requests += 1
        logger.info(f"Crawling URL: {url}")
        
        # Check URL cache first for exact matches
        if url in self.url_cache:
            logger.info(f"Using cached result for URL: {url}")
            return self._clone_result(self.url_cache[url])
        
        # Respect rate limiting
        await self._respect_rate_limit()
        
        # Check if we should use mock crawler based on configuration
        use_mock = self._should_use_mock(url)
        
        try:
            if use_mock:
                self.mock_requests += 1
                logger.warning(f"MOCK CRAWL USED! This should be disabled in production! URL: {url}")
                result = await self._mock_crawl(url)
                logger.info(f"Used mock crawler for URL: {url} (Mock requests: {self.mock_requests}/{self.total_requests})")
                return result
            elif self.use_firecrawl:
                try:
                    self.real_requests += 1
                    self.credits_used += 1
                    logger.info(f"Using Firecrawl for URL: {url} (Real requests: {self.real_requests}/{self.total_requests}, Credits used: {self.credits_used})")
                    result = await self._crawl_with_firecrawl(url)
                    
                    # Cache the result
                    self._cache_result(url, result)
                    return result
                except Exception as e:
                    logger.warning(f"Firecrawl failed, falling back to custom crawler: {str(e)}")
            else:
                logger.info(f"Firecrawl not available, using custom crawler for URL: {url}")
            
            # Fall back to custom crawler
            result = await self._crawl_with_custom(url)
            self._cache_result(url, result)
            return result
        except Exception as e:
            logger.error(f"Error crawling URL {url}: {str(e)}")
            return {
                "url": url,
                "title": None,
                "full_text": None,
                "error": str(e)
            }
    
    def _should_use_mock(self, url: str) -> bool:
        """Determine if we should use mock crawler for this URL."""
        # When USE_MOCK_PERCENTAGE is 0, we should never use mock data
        if USE_MOCK_PERCENTAGE == 0:
            return False
            
        # Always use mock if we're above the credit limit
        if self.credits_used >= FIRECRAWL_CREDIT_LIMIT:
            return True
            
        # Parse domain from URL
        domain = urlparse(url).netloc
        
        # Always use mock for specific domains in the configuration
        if domain in MOCK_CRAWL_DOMAINS:
            return True
            
        # Use random selection based on configured percentage
        return random.randint(1, 100) <= USE_MOCK_PERCENTAGE
    
    def _cache_result(self, url: str, result: Dict[str, Any]) -> None:
        """Cache the crawl result by URL."""
        # Cache by exact URL
        self.url_cache[url] = self._clone_result(result)
    
    def _clone_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep clone of the result to avoid modifying cached data."""
        return json.loads(json.dumps(result))
    
    async def _respect_rate_limit(self):
        """Respect rate limiting by waiting if needed."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < CRAWL_DELAY:
            wait_time = CRAWL_DELAY - time_since_last_request
            logger.debug(f"Rate limiting: waiting for {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _mock_crawl(self, url: str) -> Dict[str, Any]:
        """
        Generate a realistic mock crawl result based on URL patterns.
        This simulates Firecrawl API responses to save credits during testing.
        ONLY used when testing and development, never in production.
        """
        # Extract keywords from URL to create more realistic content
        path = urlparse(url).path
        domain = urlparse(url).netloc
        keywords = [k for k in path.split("/") if k]
        
        # Extract page name from URL (last part of path)
        page_name = keywords[-1] if keywords else "page"
        if page_name.endswith((".html", ".php", ".asp")):
            page_name = page_name.rsplit(".", 1)[0]
        
        # Replace hyphens with spaces
        page_name = page_name.replace("-", " ").replace("_", " ")
        
        # Determine if this URL might contain a mention of "admiralmarkets"
        has_mention = "admiral" in url.lower() or "trader" in url.lower() or "forex" in url.lower() or random.random() < 0.3
        
        # Create title
        title = f"{page_name.title()} | {domain.split('.')[0].title()}"
        
        # Create content with proper paragraphs
        paragraphs = []
        paragraphs.append(f"Welcome to the {page_name} page on {domain}.")
        paragraphs.append(f"This is the main content section of the {page_name} page.")
        
        # Add mention of admiralmarkets if appropriate
        if has_mention:
            mention_paragraphs = [
                f"We have reviewed several trading platforms including AdmiralMarkets and found them to be reliable for forex trading.",
                f"AdmiralMarkets offers competitive spreads and a user-friendly platform for traders of all levels.",
                f"When comparing brokers like AdmiralMarkets with others in the industry, we consider factors such as fees, platform reliability, and customer service."
            ]
            paragraphs.extend(random.sample(mention_paragraphs, k=random.randint(1, len(mention_paragraphs))))
        
        # Add some generic content
        generic_paragraphs = [
            f"The {domain.split('.')[0]} website provides valuable information about various topics.",
            f"Users can find detailed guides and tutorials in our resources section.",
            f"Our team of experts regularly updates the content to ensure accuracy.",
            f"Feel free to contact us if you have any questions about {page_name}.",
            f"The latest industry trends show significant changes in how users interact with content."
        ]
        paragraphs.extend(random.sample(generic_paragraphs, k=random.randint(2, 4)))
        
        # Create full text with paragraphs
        full_text = "\n\n".join(paragraphs)
        
        # Simulate API delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Return mock result
        return {
            "url": url,
            "title": title,
            "full_text": full_text,
            "html": f"<html><head><title>{title}</title></head><body>{''.join([f'<p>{p}</p>' for p in paragraphs])}</body></html>",
            "metadata": {
                "status_code": 200,
                "content_type": "text/html",
                "crawled_with": "firecrawl-mock",
                "mock_type": "generated"
            }
        }
    
    async def _crawl_with_firecrawl(self, url: str) -> Dict[str, Any]:
        """
        Crawl a URL using the Firecrawl API.
        
        This method makes an API call to Firecrawl and returns the result as a dictionary.
        The response includes the title and full text content of the URL.
        """
        logger.info(f"Crawling {url} with Firecrawl")
        
        # Use browser semaphore to respect concurrent browser limit
        async with self.browser_semaphore:
            # Use the instance attribute for the URL
            firecrawl_url = self.FIRECRAWL_API_URL
            
            # Prepare the payload - updated for Firecrawl v1/scrape endpoint
            payload = {
                "url": url,
                "formats": ["markdown", "html"],
                "timeout": 30000,
                "skipTlsVerification": True  # Skip SSL verification for problematic certificates
            }
            
            # Firecrawl API headers - Updated to use Bearer authentication
            headers = {
                "Authorization": f"Bearer {self.FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            try:
                # Make the API request
                logger.info(f"Making Firecrawl API request for {url}")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(firecrawl_url, json=payload, headers=headers)
                    
                    # Check if request was successful
                    if response.status_code != 200:
                        error_msg = f"Firecrawl API returned status code {response.status_code}"
                        logger.error(error_msg)
                        try:
                            error_json = response.json()
                            logger.error(f"Firecrawl error details: {json.dumps(error_json)}")
                        except:
                            logger.error(f"Firecrawl error response: {response.text}")
                        raise CrawlerError(error_msg)
                    
                    # Parse response
                    response_data = response.json()
                    
                    # Verify we have data
                    if not response_data or not response_data.get("success") or not response_data.get("data"):
                        logger.error(f"Firecrawl returned empty or invalid response for {url}")
                        raise CrawlerError("Empty or invalid response from Firecrawl")
                    
                    # Extract content from the response
                    data = response_data.get("data", {})
                    
                    # Extract title, markdown content, and HTML
                    title = data.get("metadata", {}).get("title", "")
                    markdown = data.get("markdown", "")
                    html = data.get("html", "")
                    
                    # Validate content
                    if not title:
                        title = f"Content from {urlparse(url).netloc}"
                        
                    if not markdown:
                        logger.warning(f"No content extracted from {url}")
                        markdown = f"Failed to extract content from {url}"
                    else:
                        logger.info(f"Successfully extracted {len(markdown)} chars of content from {url}")
                    
                    # Return the result
                    return {
                        "url": url,
                        "title": title,
                        "full_text": markdown,
                        "html": html,
                        "metadata": {
                            "status_code": 200,
                            "content_type": "text/html",
                            "crawled_with": "firecrawl",
                            "extraction_quality": "high"
                        }
                    }
                    
            except httpx.RequestError as e:
                logger.error(f"HTTP error making Firecrawl API request: {str(e)}")
                raise CrawlerError(f"HTTP error with Firecrawl: {str(e)}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding Firecrawl API response: {str(e)}")
                raise CrawlerError(f"Invalid JSON response from Firecrawl: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error with Firecrawl API: {str(e)}")
                traceback.print_exc()
                raise CrawlerError(f"Unexpected error with Firecrawl: {str(e)}")
    
    async def _crawl_with_custom(self, url: str) -> Dict[str, Any]:
        """
        Custom fallback crawling implementation using requests and BeautifulSoup.
        This is used when the Firecrawl API fails or is unavailable.
        """
        logger.info(f"Falling back to custom crawler for {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        loop = asyncio.get_event_loop()
        
        # Set up a single session for all requests
        session = requests.Session()
        
        async def make_request():
            try:
                return await loop.run_in_executor(
                    None,
                    lambda: session.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        allow_redirects=True,
                        verify=True  # Try with verification first
                    )
                )
            except requests.exceptions.SSLError:
                logger.warning(f"SSL error when accessing {url}, retrying without verification")
                return await loop.run_in_executor(
                    None,
                    lambda: session.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        allow_redirects=True,
                        verify=False  # Disable SSL verification on error
                    )
                )
        
        attempt = 0
        while attempt < MAX_RETRIES:
            try:
                logger.info(f"Custom crawler GET {url} (attempt {attempt+1})")
                
                # Make the request
                response = await make_request()
                logger.info(f"Custom crawler response status: {response.status_code}")
                
                # If we got a redirect, update the URL for logging purposes
                final_url = response.url
                if final_url != url:
                    logger.info(f"URL was redirected: {url} -> {final_url}")
                
                # Only proceed if we got a successful response
                if response.status_code == 200:
                    # Try to determine the content type
                    content_type = response.headers.get("Content-Type", "")
                    logger.info(f"Content-Type: {content_type}")
                    
                    # Process HTML content
                    if "text/html" in content_type or "application/xhtml+xml" in content_type:
                        try:
                            # Try different parsers in case one fails
                            for parser in ["lxml", "html.parser", "html5lib"]:
                                try:
                                    soup = BeautifulSoup(response.text, parser)
                                    logger.info(f"Successfully parsed HTML with {parser}")
                                    break
                                except Exception as e:
                                    logger.warning(f"Failed to parse with {parser}: {str(e)}")
                                    if parser == "html5lib":  # Last parser in the list
                                        raise
                            
                            # Extract title
                            title = ""
                            if soup.title and soup.title.string:
                                title = soup.title.string.strip()
                            else:
                                # Try other common title elements
                                for selector in ["h1", ".title", "#title", "[class*='title']", "header h1", "article h1"]:
                                    title_elem = soup.select_one(selector)
                                    if title_elem and title_elem.get_text(strip=True):
                                        title = title_elem.get_text(strip=True)
                                        break
                            
                            logger.info(f"Extracted title: '{title}'")
                            
                            # Remove script and style elements
                            for script_or_style in soup(["script", "style", "nav", "footer", "aside", "noscript", "header"]):
                                script_or_style.extract()
                            
                            # Get the primary content (attempt to identify main content area)
                            main_content_selectors = [
                                "main", "article", "#content", ".content", "[role='main']", "#main", ".main",
                                "[class*='content']", "[id*='content']", ".post", "#post", "div.entry", 
                                ".entry-content", ".post-content", ".article-content"
                            ]
                            
                            main_content = None
                            for selector in main_content_selectors:
                                try:
                                    elements = soup.select(selector)
                                    if elements:
                                        # Choose the one with the most text
                                        most_text_elem = max(elements, key=lambda e: len(e.get_text(strip=True)))
                                        if len(most_text_elem.get_text(strip=True)) > 100:  # Only if it has substantial content
                                            main_content = most_text_elem
                                            logger.info(f"Found main content using selector: {selector}")
                                            break
                                except Exception as e:
                                    logger.warning(f"Error finding content with selector {selector}: {str(e)}")
                            
                            # If we couldn't identify a main content area, use the whole body
                            full_text = ""
                            if main_content:
                                full_text = main_content.get_text(separator="\n", strip=True)
                                logger.info(f"Extracted {len(full_text)} chars from main content area")
                                
                                # If main content doesn't have enough text, fall back to full body
                                if len(full_text) < 200:
                                    logger.info("Main content too short, falling back to full body")
                                    full_text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
                            else:
                                logger.info("No main content area identified, using full body")
                                full_text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
                            
                            logger.info(f"Final extracted text length: {len(full_text)}")
                            
                            # Clean up the extracted text
                            if full_text:
                                # Remove excessive whitespace
                                full_text = re.sub(r'\n\s*\n', '\n\n', full_text)
                                # Remove multiple spaces
                                full_text = re.sub(r' +', ' ', full_text)
                                # Trim to reasonable length for analysis
                                if len(full_text) > 100000:
                                    logger.warning(f"Text too long ({len(full_text)} chars), truncating to 100k chars")
                                    full_text = full_text[:100000]
                            
                            # Create markdown version for consistency with Firecrawl
                            markdown = full_text
                            
                            return {
                                "url": final_url,
                                "title": title or f"Content from {urlparse(final_url).netloc}",
                                "full_text": markdown or f"Failed to extract content from {final_url}",
                                "html": response.text if len(response.text) < 500000 else response.text[:500000],  # Limit HTML size
                                "metadata": {
                                    "status_code": response.status_code,
                                    "content_type": content_type,
                                    "crawled_with": "custom",
                                    "extraction_quality": "low" if not markdown or len(markdown) < 100 else "high"
                                }
                            }
                            
                        except Exception as e:
                            logger.error(f"Error parsing HTML from {url}: {str(e)}")
                            traceback.print_exc()
                    
                    # Process JSON content
                    elif "application/json" in content_type:
                        try:
                            json_data = response.json()
                            # Extract text content from common JSON fields
                            content_fields = []
                            
                            def extract_text_from_json(obj, field_path=""):
                                if isinstance(obj, dict):
                                    for key, value in obj.items():
                                        # Look for likely content fields
                                        if isinstance(value, str) and len(value) > 50 and any(c in key.lower() for c in ["content", "text", "body", "description"]):
                                            content_fields.append((f"{field_path}.{key}" if field_path else key, value))
                                        extract_text_from_json(value, f"{field_path}.{key}" if field_path else key)
                                elif isinstance(obj, list):
                                    for i, item in enumerate(obj):
                                        extract_text_from_json(item, f"{field_path}[{i}]")
                            
                            extract_text_from_json(json_data)
                            
                            # Sort by content length and take the longest
                            content_fields.sort(key=lambda x: len(x[1]), reverse=True)
                            
                            full_text = "\n\n".join([value for _, value in content_fields[:5]]) if content_fields else ""
                            title = urlparse(final_url).netloc
                            
                            return {
                                "url": final_url,
                                "title": title,
                                "full_text": full_text or f"JSON data from {final_url}",
                                "html": json.dumps(json_data, indent=2),
                                "metadata": {
                                    "status_code": response.status_code,
                                    "content_type": content_type,
                                    "crawled_with": "custom",
                                    "extraction_quality": "low" if not full_text else "medium"
                                }
                            }
                            
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing JSON from {url}")
                    
                    # Other content types
                    else:
                        logger.warning(f"Unsupported content type: {content_type}")
                        return {
                            "url": final_url,
                            "title": f"Content from {urlparse(final_url).netloc}",
                            "full_text": f"Unsupported content type: {content_type}",
                            "html": "",
                            "metadata": {
                                "status_code": response.status_code,
                                "content_type": content_type,
                                "crawled_with": "custom",
                                "extraction_quality": "low"
                            }
                        }
                        
                # Handle redirect loops or other non-200 status codes
                else:
                    logger.warning(f"Non-200 status code: {response.status_code} for {url}")
                    # Try once more with a different User-Agent if we got blocked
                    if response.status_code in [403, 429] and attempt < MAX_RETRIES - 1:
                        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
                        logger.info("Changing User-Agent and retrying")
                        await asyncio.sleep(2)
                        attempt += 1
                        continue
                    
                    return {
                        "url": final_url,
                        "title": f"Error {response.status_code}",
                        "full_text": f"Failed to access {final_url}: HTTP {response.status_code}",
                        "html": "",
                        "metadata": {
                            "status_code": response.status_code,
                            "content_type": response.headers.get("Content-Type", ""),
                            "crawled_with": "custom",
                            "extraction_quality": "none"
                        }
                    }
                    
            except (requests.RequestException, asyncio.TimeoutError) as e:
                logger.error(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                    attempt += 1
                else:
                    logger.error(f"All {MAX_RETRIES} attempts failed for {url}")
                    return {
                        "url": url,
                        "title": "Failed to access",
                        "full_text": f"Failed to access {url} after {MAX_RETRIES} attempts: {str(e)}",
                        "html": "",
                        "metadata": {
                            "status_code": getattr(e, "status_code", 0),
                            "content_type": "",
                            "crawled_with": "custom-failed",
                            "extraction_quality": "none",
                            "error": str(e)
                        }
                    }
            
            # If we got here, we've successfully crawled the URL
            break
            
        # We should never reach this point, but just in case
        return {
            "url": url,
            "title": "Unknown error",
            "full_text": f"An unknown error occurred while crawling {url}",
            "html": "",
            "metadata": {
                "status_code": 0,
                "content_type": "",
                "crawled_with": "custom-error",
                "extraction_quality": "none"
            }
        }
    
    def _mock_crawl_result(self, url: str) -> Dict[str, Any]:
        """Create a mock crawl result for test URLs."""
        # Extract the part of the URL that mentions admiralmarkets
        url_parts = url.split("/")
        relevant_parts = [part for part in url_parts if "admiralmarkets" in part.lower()]
        relevant_text = " ".join(relevant_parts) if relevant_parts else "admiralmarkets"
        
        # Create a mock title and content
        title = f"Admiral Markets Test Page - {url_parts[-1] if len(url_parts) > 1 else 'Home'}"
        
        # Mock content with admiralmarkets mentions
        content = f"""
        This is a test page for {url}.
        
        Admiral Markets offers trading solutions for forex, CFDs, and commodities.
        The platform admiralmarkets provides various trading options and educational resources.
        
        Admiral Markets is regulated by multiple authorities and offers competitive spreads.
        If you're looking to trade with admiralmarkets, you should consider their MetaTrader offerings.
        
        Learn more about Admiral Markets today!
        """
        
        logger.info(f"Mock crawler returning content for {url} - title: {title}")
        
        return {
            "url": url,
            "title": title,
            "full_text": content,
            "html": f"<html><head><title>{title}</title></head><body>{content}</body></html>",
            "metadata": {
                "status_code": 200,
                "content_type": "text/html",
                "crawled_with": "mock"
            }
        }


# Singleton instance
crawler_service = FirecrawlService() 