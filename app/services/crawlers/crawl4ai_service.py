#!/usr/bin/env python3
"""
Crawl4AI service for web crawling with JavaScript support.
This service handles authentication, request formatting, and response parsing.
Implemented as a backup crawler.
"""

import os
import json
import asyncio
import logging
import re
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

# Import Crawl4AI specific libraries
import crawl4ai
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

logger = logging.getLogger(__name__)

class Crawl4AIService:
    """Service for interacting with the Crawl4AI library."""
    
    def __init__(self):
        """Initialize the Crawl4AI service."""
        self.api_key = os.getenv("CRAWL4AI_API_KEY")  # Optional, may not be needed as Crawl4AI is open source
        self.timeout = int(os.getenv("CRAWL4AI_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRY_COUNT", "3"))
        self.cache_mode = os.getenv("CRAWL4AI_CACHE_MODE", "BYPASS")
        
        # Admiral Markets pattern variations
        self.admiral_patterns = [
            r'admiral\s*markets',
            r'admiralmarkets',
            r'admiral\.markets',
            r'admiral-markets',
            r'admirals'  # New brand name
        ]
        
        # Browser configuration
        self.browser_config = BrowserConfig(
            headless=True,
            viewport_width=1280,
            viewport_height=720
        )
    
    def _extract_title_from_html(self, html_content: str) -> str:
        """Extract title from HTML content."""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        return ""
    
    def _find_admiral_mentions(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all Admiral Markets mentions in text.
        
        Returns:
            List of tuples (start_index, end_index, matched_text)
        """
        mentions = []
        
        for pattern in self.admiral_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append((match.start(), match.end(), match.group()))
        
        # Remove duplicate/overlapping mentions
        mentions.sort(key=lambda x: x[0])
        unique_mentions = []
        last_end = -1
        
        for start, end, text in mentions:
            if start >= last_end:
                unique_mentions.append((start, end, text))
                last_end = end
        
        return unique_mentions
    
    def _extract_context_around_mention(self, text: str, mention_start: int, mention_end: int, words_before: int = 100, words_after: int = 100) -> Dict[str, Any]:
        """
        Extract context around a mention.
        
        Args:
            text: Full text content
            mention_start: Start index of mention
            mention_end: End index of mention
            words_before: Number of words to extract before mention
            words_after: Number of words to extract after mention
            
        Returns:
            Dict with context information
        """
        # Convert text to words with their positions
        words = []
        word_pattern = re.compile(r'\b\w+\b')
        
        for match in word_pattern.finditer(text):
            words.append({
                'word': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Find the word containing the mention
        mention_word_idx = None
        for i, word_info in enumerate(words):
            if word_info['start'] <= mention_start <= word_info['end']:
                mention_word_idx = i
                break
        
        if mention_word_idx is None:
            # Fallback to character-based extraction
            context_start = max(0, mention_start - 500)
            context_end = min(len(text), mention_end + 500)
            return {
                'context': text[context_start:context_end],
                'mention_text': text[mention_start:mention_end],
                'words_before': None,
                'words_after': None
            }
        
        # Extract words before and after
        start_word_idx = max(0, mention_word_idx - words_before)
        end_word_idx = min(len(words), mention_word_idx + words_after + 1)
        
        # Get the actual text positions
        if start_word_idx < len(words):
            context_start = words[start_word_idx]['start']
        else:
            context_start = 0
            
        if end_word_idx > 0 and end_word_idx <= len(words):
            context_end = words[end_word_idx - 1]['end']
        else:
            context_end = len(text)
        
        context_text = text[context_start:context_end]
        
        return {
            'context': context_text,
            'mention_text': text[mention_start:mention_end],
            'words_before': mention_word_idx - start_word_idx,
            'words_after': end_word_idx - mention_word_idx - 1,
            'position_in_text': {
                'start': mention_start,
                'end': mention_end,
                'percentage': (mention_start / len(text) * 100) if len(text) > 0 else 0
            }
        }
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape a URL using Crawl4AI library.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the response data or error information
        """
        # Set up crawler configuration
        config = CrawlerRunConfig(
            cache_mode=CacheMode.DISABLED,
            page_timeout=int(os.getenv('CRAWL4AI_TIMEOUT', '20000')),
            wait_until='domcontentloaded'  # Faster than networkidle
        )
        
        # Initialize retry counter
        retry_count = 0
        
        while retry_count <= self.max_retries:
            if retry_count > 0:
                # Calculate backoff time (exponential backoff)
                backoff_time = 2 ** retry_count
                logger.info(f"Retrying request ({retry_count}/{self.max_retries}) after {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            
            try:
                start_time = datetime.now()
                
                # Create crawler and run it
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    result = await crawler.arun(url=url, config=config)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    if result.success:
                        logger.info(f"Crawl4AI request successful: {url} (Duration: {duration:.2f}s)")
                        
                        # Extract title from HTML if available
                        title = self._extract_title_from_html(result.cleaned_html)
                        
                        # Format response
                        response = {
                            "success": True,
                            "duration": duration,
                            "data": {
                                "markdown": result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else result.markdown,
                                "html": result.cleaned_html,
                                "metadata": {
                                    "title": title,
                                    "url": result.url,
                                    "crawl_time": str(end_time)
                                }
                            }
                        }
                        
                        return response
                    else:
                        logger.error(f"Crawl4AI request failed: {url}, Error: {result.error_message}")
                        
                        # Check if we should retry based on error
                        if "timeout" in result.error_message.lower() or "connection" in result.error_message.lower():
                            retry_count += 1
                            continue
                        
                        return {
                            "success": False,
                            "duration": duration,
                            "error": result.error_message,
                            "error_type": "api_error"
                        }
                        
            except Exception as e:
                logger.error(f"Unexpected error during Crawl4AI request for {url}: {str(e)}", exc_info=True)
                
                # For connection or timeout errors, retry
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    retry_count += 1
                    continue
                
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": "unexpected"
                }
        
        # If we get here, we've exhausted all retries
        logger.error(f"Failed to scrape {url} after {self.max_retries} retries")
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} retries",
            "error_type": "max_retries"
        }
    
    async def extract_content(self, url: str) -> Dict[str, Union[bool, str, Dict[str, Any]]]:
        """
        Extract content from a URL using Crawl4AI.
        This is a convenience method that returns a simplified response.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the extracted content or error information
        """
        response = await self.scrape_url(url)
        
        if not response.get("success", False):
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "url": url
            }
        
        data = response.get("data", {})
        markdown = data.get("markdown", "")
        html = data.get("html", "")
        metadata = data.get("metadata", {})
        
        # Check for Admiral Markets mentions
        mentions = self._find_admiral_mentions(markdown)
        
        if not mentions:
            logger.info(f"No Admiral Markets mentions found on {url}, skipping analysis")
            return {
                "success": True,
                "url": url,
                "markdown": markdown,
                "html": html,
                "metadata": metadata,
                "duration": response.get("duration", 0),
                "skip_analysis": True,
                "skip_reason": "No Admiral Markets mentions found"
            }
        
        # Extract context around mentions
        mention_contexts = []
        for start, end, mention_text in mentions:
            context = self._extract_context_around_mention(markdown, start, end)
            mention_contexts.append(context)
        
        logger.info(f"Found {len(mentions)} Admiral Markets mentions on {url}")
        
        return {
            "success": True,
            "url": url,
            "markdown": markdown,
            "html": html,
            "metadata": metadata,
            "duration": response.get("duration", 0),
            "skip_analysis": False,
            "admiral_mentions": len(mentions),
            "mention_contexts": mention_contexts
        } 