#!/usr/bin/env python3
"""
Firecrawl API service for web crawling with JavaScript support.
This service handles authentication, request formatting, and response parsing.
"""

import os
import json
import asyncio
import logging
import aiohttp
import re
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class FirecrawlService:
    """Service for interacting with the Firecrawl API."""
    
    def __init__(self):
        """Initialize the Firecrawl service with API configuration."""
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
        
        # Speed optimization settings from environment
        self.timeout = int(os.getenv('FIRECRAWL_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '2'))
        
        # Admiral Markets pattern variations
        self.admiral_patterns = [
            r'admiral\s*markets',
            r'admiralmarkets',
            r'admiral\.markets',
            r'admiral-markets',
            r'admirals'  # New brand name
        ]
        
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY not set, Firecrawl service will not be available")
    
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
        Scrape a URL using Firecrawl API.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the response data or error information
        """
        if not self.api_key:
            logger.error("Cannot scrape URL: FIRECRAWL_API_KEY not set")
            return {
                "success": False,
                "error": "API key not configured",
                "error_type": "configuration"
            }
        
        # Set up request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["markdown", "html"],
            "timeout": self.timeout * 1000,  # Convert to milliseconds
            "skipTlsVerification": True  # Skip SSL verification for problematic certificates
        }
        
        # Initialize retry counter
        retry_count = 0
        
        while retry_count <= self.max_retries:
            if retry_count > 0:
                # Calculate backoff time (exponential backoff)
                backoff_time = 2 ** retry_count
                logger.info(f"Retrying request ({retry_count}/{self.max_retries}) after {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            
            try:
                async with aiohttp.ClientSession() as session:
                    start_time = datetime.now()
                    
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout + 5  # Add 5 seconds buffer
                    ) as response:
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        # Read response
                        response_text = await response.text()
                        status_code = response.status
                        
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse Firecrawl response as JSON. Status: {status_code}")
                            
                            # Only retry on server errors or timeout
                            if status_code >= 500 or status_code == 408:
                                retry_count += 1
                                continue
                                
                            return {
                                "success": False,
                                "status_code": status_code,
                                "duration": duration,
                                "error": "Invalid JSON response",
                                "error_type": "parsing"
                            }
                        
                        # Check if successful
                        if status_code == 200 and response_json.get("success", False):
                            logger.info(f"Firecrawl request successful: {url} (Duration: {duration:.2f}s)")
                            
                            # Add duration and status code to response
                            response_json["duration"] = duration
                            response_json["status_code"] = status_code
                            
                            return response_json
                        
                        # Handle rate limiting
                        if status_code == 429:
                            logger.warning(f"Firecrawl rate limit hit for {url}. Retrying...")
                            retry_count += 1
                            continue
                        
                        # Handle server errors
                        if status_code >= 500:
                            logger.warning(f"Firecrawl server error ({status_code}) for {url}. Retrying...")
                            retry_count += 1
                            continue
                        
                        # Handle other errors (client errors, etc.)
                        logger.error(f"Firecrawl request failed: {url}, Status: {status_code}")
                        return {
                            "success": False,
                            "status_code": status_code,
                            "duration": duration,
                            "error": response_json.get("error", "Unknown error"),
                            "error_type": "api_error"
                        }
                        
            except aiohttp.ClientError as e:
                logger.error(f"Firecrawl connection error for {url}: {str(e)}")
                retry_count += 1
                continue
                
            except asyncio.TimeoutError:
                logger.error(f"Firecrawl request timed out for {url} after {self.timeout} seconds")
                retry_count += 1
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error during Firecrawl request for {url}: {str(e)}", exc_info=True)
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
        Extract content from a URL using Firecrawl API.
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
