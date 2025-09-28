"""
OpenAI service for analyzing URL content when OpenRouter fails.
This serves as a middle fallback between OpenRouter and keyword-based analysis.
"""
import os
import logging
import json
import asyncio
import time
import random
from typing import List, Dict, Any, Optional
import openai

from app.models.url import URLContent
from app.models.report import AIAnalysisResult, URLCategory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1"))


class OpenAIService:
    """
    Service for analyzing URL content using OpenAI API:
    1. Connect to OpenAI API
    2. Generate prompts for content analysis
    3. Process AI responses
    4. Determine compliance status
    """
    
    def __init__(self):
        """Initialize the OpenAI service."""
        self.is_initialized = OPENAI_API_KEY is not None and OPENAI_API_KEY.strip() != ""
        self.last_request_time = 0
        self.analysis_counts = {"openai": 0}
        
        if not self.is_initialized:
            logger.error("CRITICAL: Valid OPENAI_API_KEY not found in environment variables! The OpenAI fallback will not be available.")
        else:
            logger.info(f"OpenAI service initialized with model: {OPENAI_MODEL}")
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    async def analyze_content(self, url_content: URLContent) -> AIAnalysisResult:
        """
        Analyze URL content for compliance:
        1. Generate prompt based on URL content
        2. Send prompt to OpenAI
        3. Process response and determine compliance category
        
        Raises an exception if OpenAI is not available.
        """
        if not self.is_initialized:
            logger.error(f"Failed to analyze URL {url_content.url}: OpenAI service not initialized. Valid API key required.")
            raise RuntimeError("OpenAI service not initialized. Cannot perform fallback analysis.")
        
        # Respect rate limiting
        await self._respect_rate_limit()
        
        try:
            # Generate prompt
            messages = self._generate_prompt(url_content)
            
            # Send to OpenAI
            response = await self._call_openai(messages)
            
            # Process response
            result = self._process_response(response, url_content)
            
            # Track successful analysis with OpenAI
            self.analysis_counts["openai"] += 1
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing content with OpenAI for URL {url_content.url}: {str(e)}")
            # Don't use mock results - explicitly fail
            raise
    
    async def _respect_rate_limit(self):
        """Respect rate limiting by waiting if needed."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - time_since_last_request
            logger.debug(f"Rate limiting: waiting for {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _generate_prompt(self, url_content: URLContent) -> List[Dict[str, Any]]:
        """Generate prompt for OpenAI based on URL content."""
        # Extract mentions and their context
        mentions_text = ""
        for i, mention in enumerate(url_content.mentions):
            context = mention.context_before + mention.text + mention.context_after
            mentions_text += f"Mention {i+1}:\n{context}\n\n"
        
        # Create system message
        system_message = """
        You are a compliance analyst for Admiral Markets, a financial services company. Your task is to evaluate content 
        from external websites that mention Admiral Markets to determine if they comply with financial regulations and 
        brand guidelines.

        Your evaluation will help determine if a URL should be:
        1. BLACKLISTED: Contains serious compliance issues (misleading claims, unauthorized offers, false representation, regulatory issues)
        2. WHITELISTED: Contains no compliance issues, accurately represents Admiral Markets
        3. NEEDS REVIEW: Contains potential issues that require human review

        Pay special attention to:
        - Misleading information (guaranteed profits, risk-free trading claims)
        - Unauthorized offers (bonuses, special offers not authorized by Admiral Markets)
        - False representation (falsely claiming partnership or endorsement)
        - Regulatory issues (content that could violate financial regulations)
        - Inappropriate marketing tactics (get-rich-quick schemes, exaggerated claims)

        After analyzing the content, provide:
        1. A category determination (BLACKLIST, WHITELIST, or NEEDS_REVIEW)
        2. A confidence score (0.0 to 1.0)
        3. A brief explanation of your decision
        4. A list of specific compliance issues found (if any)
        
        Format your response as a valid JSON object with these fields.
        """
        
        # Create user message
        user_message = f"""
        Please analyze the following content from {url_content.url} that mentions Admiral Markets.

        Title: {url_content.title or 'No title available'}

        Context surrounding "admiralmarkets" mentions:
        
        {mentions_text}

        Based on this content, evaluate compliance with financial regulations and brand guidelines.
        Return your analysis as a JSON object with these fields:
        1. "category": "BLACKLIST", "WHITELIST", or "NEEDS_REVIEW"
        2. "confidence": A float between 0.0 and 1.0 indicating your confidence in the classification
        3. "explanation": A brief explanation of your decision
        4. "compliance_issues": An array of specific compliance issues found (empty array if none)
        """
        
        # Create messages array
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    async def _call_openai(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call OpenAI API with messages."""
        # Run in asyncio executor pool since OpenAI client is synchronous
        loop = asyncio.get_event_loop()
        
        for attempt in range(MAX_RETRIES):
            try:
                # Define function that will be run
                def call_api():
                    response = self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                        temperature=0.2,  # Low temperature for more deterministic responses
                        max_tokens=1024,
                    )
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": response.choices[0].message.content
                                }
                            }
                        ]
                    }
                
                # Call the API in a separate thread
                response = await loop.run_in_executor(None, call_api)
                return response
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"OpenAI request failed (attempt {attempt+1}/{MAX_RETRIES}): {error_msg}")
                
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    backoff_time = (2 ** attempt) + (random.random() * 0.5)
                    logger.info(f"Retrying in {backoff_time:.2f} seconds")
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"OpenAI request failed after {MAX_RETRIES} attempts")
                    raise
    
    def _process_response(self, response: Dict[str, Any], url_content: URLContent) -> AIAnalysisResult:
        """Process OpenAI response and determine compliance category."""
        try:
            # Extract response content
            response_content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Parse JSON from response
            # First, try to find JSON in the response if it's not a pure JSON response
            json_match = response_content.strip()
            try:
                # Try to parse as is first
                analysis = json.loads(json_match)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON using a more permissive approach
                start_idx = json_match.find("{")
                end_idx = json_match.rfind("}")
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_match[start_idx:end_idx+1]
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("Could not extract valid JSON from response")
            
            # Map category string to enum
            category_str = analysis.get("category", "NEEDS_REVIEW").upper()
            if category_str == "BLACKLIST":
                category = URLCategory.BLACKLIST
            elif category_str == "WHITELIST":
                category = URLCategory.WHITELIST
            else:
                category = URLCategory.REVIEW
            
            # Process compliance issues - handle both string and dictionary formats
            compliance_issues = analysis.get("compliance_issues", [])
            
            # If compliance_issues is not a list, make it a list
            if not isinstance(compliance_issues, list):
                compliance_issues = [compliance_issues]
                
            # Create AI analysis result
            return AIAnalysisResult(
                model=OPENAI_MODEL,
                category=category,
                confidence=float(analysis.get("confidence", 0.5)),
                explanation=analysis.get("explanation", "No explanation provided"),
                compliance_issues=compliance_issues,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Error processing OpenAI response: {str(e)}")
            raise ValueError(f"Failed to process OpenAI response: {str(e)}")
    
    def get_analysis_stats(self):
        """Get statistics about analysis methods used."""
        return {
            "openai_count": self.analysis_counts["openai"]
        }


# Singleton instance
openai_service = OpenAIService() 