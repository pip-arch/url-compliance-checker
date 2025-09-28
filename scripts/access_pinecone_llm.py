#!/usr/bin/env python3
"""
Script to verify Pinecone access and analyze processed URLs with LLM
"""
import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from urllib.parse import urlparse
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to test Pinecone access and analyze URLs"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Pinecone access and analyze URLs via LLM")
    parser.add_argument("--limit", type=int, default=5, help="Limit the number of URLs to query")
    parser.add_argument("--analyze", action="store_true", help="Run LLM analysis on returned content")
    parser.add_argument("--query", type=str, default="admiralmarkets", help="Query string to search in Pinecone")
    args = parser.parse_args()
    
    # Import services after loading environment variables
    from app.services.vector_db import pinecone_service
    from app.services.ai import ai_service
    from app.services.database import database_service
    
    # Verify Pinecone is initialized
    if not pinecone_service.is_initialized:
        logger.error("❌ Pinecone service failed to initialize")
        return False
    
    logger.info("✅ Pinecone service initialized successfully!")
    
    # Get some processed URLs from the database
    logger.info(f"Querying for up to {args.limit} processed URLs...")
    
    # Method 1: Get processed URLs from the database
    try:
        processed_urls = await database_service.get_processed_urls(limit=args.limit)
        logger.info(f"Found {len(processed_urls)} processed URLs in database")
        
        if processed_urls:
            logger.info("Sample URLs with processed status:")
            for i, url in enumerate(processed_urls[:5], 1):
                logger.info(f"{i}. {url.url}")
    except Exception as e:
        logger.error(f"Error querying database: {str(e)}")
        processed_urls = []
    
    # Method 2: Search in Pinecone vector DB
    try:
        logger.info(f"Searching Pinecone for content matching '{args.query}'...")
        search_results = await pinecone_service.search_similar_content(args.query, top_k=args.limit)
        
        if search_results:
            logger.info(f"Found {len(search_results)} results in Pinecone")
            logger.info("Sample results from Pinecone:")
            for i, result in enumerate(search_results[:5], 1):
                url = result.get("url", "N/A")
                score = result.get("score", 0)
                text = result.get("text", "")[:50] + "..." if len(result.get("text", "")) > 50 else result.get("text", "")
                logger.info(f"{i}. URL: {url} (score: {score:.4f})")
                logger.info(f"   Text: {text}")
                
                # Run LLM analysis if requested
                if args.analyze:
                    logger.info(f"Analyzing content with LLM for URL: {url}")
                    try:
                        # Format the content for LLM analysis
                        context_before = result.get("context_before", "")
                        text = result.get("text", "")
                        context_after = result.get("context_after", "")
                        
                        full_context = f"{context_before}{text}{context_after}"
                        
                        # Create a simple URL content object for analysis
                        from app.models.url import URLContent, URLContentMatch
                        
                        match = URLContentMatch(
                            text=text,
                            position=0,
                            context_before=context_before,
                            context_after=context_after
                        )
                        
                        content = URLContent(
                            url=url,
                            title=result.get("title", ""),
                            full_text=full_context,
                            mentions=[match]
                        )
                        
                        # Run AI analysis
                        analysis_result = await ai_service.analyze_content(content)
                        
                        # Display analysis results
                        logger.info("LLM Analysis Results:")
                        logger.info(f"Category: {analysis_result.category}")
                        logger.info(f"Confidence: {analysis_result.confidence}")
                        logger.info(f"Explanation: {analysis_result.explanation}")
                        if analysis_result.compliance_issues:
                            logger.info(f"Issues: {', '.join(analysis_result.compliance_issues)}")
                    except Exception as e:
                        logger.error(f"Error analyzing with LLM: {str(e)}")
        else:
            logger.warning(f"No results found in Pinecone for query '{args.query}'")
    except Exception as e:
        logger.error(f"Error searching Pinecone: {str(e)}")
    
    # Check if URL crawler is skipping already processed URLs
    try:
        logger.info("Checking URL processor logic for already processed URLs...")
        from app.core.url_processor import URLProcessor
        
        # Create instance of processor
        processor = URLProcessor()
        
        # Get a few processed URLs to test with
        test_urls = [url.url for url in processed_urls[:3]] if processed_urls else []
        
        if test_urls:
            for test_url in test_urls:
                existing_url = await processor._get_url_by_url_string(test_url)
                is_processed = existing_url and existing_url.status == "processed" and hasattr(existing_url, 'content') and existing_url.content
                
                logger.info(f"URL: {test_url}")
                logger.info(f"Status: {'Already processed' if is_processed else 'Would be processed again'}")
                logger.info(f"Has content: {hasattr(existing_url, 'content') and bool(existing_url.content) if existing_url else False}")
                logger.info("---")
        else:
            logger.warning("No processed URLs available to test crawler logic")
    except Exception as e:
        logger.error(f"Error checking URL processor logic: {str(e)}")

    return True

if __name__ == "__main__":
    asyncio.run(main()) 