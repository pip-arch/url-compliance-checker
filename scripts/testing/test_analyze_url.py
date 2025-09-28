#!/usr/bin/env python3
"""
Test script to analyze a specific URL with verbose logging
"""
import asyncio
import logging
import os
import sys
import json

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Set up very verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def analyze_url():
    """Analyze a specific URL and show detailed logs"""
    from app.services.ai import ai_service
    from app.models.url_content import URLContent
    
    # Test URL info
    test_url = "https://app.playpager.com/"
    test_html = """<html><body><h1>Test Page</h1><p>This is a test page with some content.</p></body></html>"""
    
    # Create AI service instance
    ai = ai_service.AIService()
    
    # Create URL content object
    url_content = URLContent(url=test_url, html_content=test_html)
    
    try:
        logger.info(f"Starting analysis of URL: {test_url}")
        
        # Analyze the URL content
        results = await ai.analyze_content(url_content)
        
        # Log the results
        logger.info("Analysis complete. Results:")
        logger.info(f"Model: {results.model}")
        logger.info(f"Category: {results.category}")
        logger.info(f"Confidence: {results.confidence}")
        logger.info(f"Explanation: {results.explanation}")
        
        if results.compliance_issues:
            logger.info("Compliance issues:")
            for issue in results.compliance_issues:
                logger.info(f"- {issue}")
        else:
            logger.info("No compliance issues found.")
        
        # Print full results as JSON
        logger.info("Full results JSON:")
        logger.info(json.dumps(results.model_dump(), indent=2))
        
    except Exception as e:
        logger.error(f"Error analyzing URL: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(analyze_url()) 