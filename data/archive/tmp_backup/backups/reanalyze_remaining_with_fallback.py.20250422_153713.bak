#!/usr/bin/env python3
"""
Script to reanalyze the remaining URLs already stored in Pinecone
that were not covered in the previous analysis.
Uses keyword fallback when OpenRouter fails.
"""
import asyncio
import logging
import time
from datetime import datetime
import csv
import os
import argparse
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/reanalysis_fallback.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cost calculation constants
CLAUDE_3_OPUS_COST_PER_1K = 0.015  # $0.015 per 1K tokens
LLAMA_70B_COST_PER_1K = 0.0009  # $0.0009 per 1K tokens
AVG_TOKENS_PER_ANALYSIS = 3000  # Estimated average tokens per analysis

async def reanalyze_with_fallback(skip_first=1000, max_additional=500):
    """
    Reanalyze the remaining URLs stored in Pinecone, skipping the first N already processed.
    Uses keyword fallback when OpenRouter fails.
    
    Args:
        skip_first (int): Number of URLs to skip from the beginning
        max_additional (int): Maximum number of additional URLs to process
    """
    # Import modules
    from app.services.vector_db import pinecone_service
    from app.services.ai import ai_service
    from app.models.report import URLCategory, URLReport, AIAnalysisResult
    from app.core.blacklist_keywords import blacklist_keywords
    import os
    
    # Get current model name for logging
    current_model = os.getenv("OPENROUTER_MODEL", "unknown")
    logger.info(f"Using OpenRouter model: {current_model} with keyword fallback")
    
    # Ensure services are initialized
    if not pinecone_service.is_initialized:
        logger.error("Pinecone service not initialized")
        return
    
    if not hasattr(ai_service, 'is_initialized') or not ai_service.is_initialized:
        logger.error("AI service not initialized")
        return
    
    # Get a batch of URLs from Pinecone
    try:
        # Get total count first
        stats = pinecone_service.index.describe_index_stats()
        total_count = stats.total_vector_count if hasattr(stats, "total_vector_count") else 0
        logger.info(f"Total vectors in Pinecone: {total_count}")
        
        remaining_count = total_count - skip_first
        if remaining_count <= 0:
            logger.error(f"No remaining URLs to process. Total count ({total_count}) is less than or equal to skip_first ({skip_first})")
            return
            
        logger.info(f"Found {remaining_count} remaining URLs to process")
        
        # Create a batch ID for this reanalysis
        batch_id = f"reanalysis_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Set up a blacklist file path for adding new entries
        blacklist_file = "data/tmp/blacklist_consolidated.csv"
        
        # Load existing blacklisted URLs to avoid duplicates
        existing_blacklisted = set()
        try:
            with open(blacklist_file, "r", newline='') as f:
                reader = csv.reader(f)
                # Skip header
                next(reader)
                for row in reader:
                    if row and len(row) > 0:
                        url = row[0].strip()
                        if url and url.startswith("http"):
                            existing_blacklisted.add(url)
            logger.info(f"Loaded {len(existing_blacklisted)} existing blacklisted URLs")
        except Exception as e:
            logger.error(f"Error loading existing blacklisted URLs: {e}")
        
        # Fetch all URLs at once
        logger.info(f"Querying Pinecone for all URLs...")
        all_results = await pinecone_service.search_similar_content(
            "url website internet", 
            top_k=total_count  # Get as many as possible
        )
        
        logger.info(f"Got {len(all_results)} total results from Pinecone")
        
        # Skip the first N and limit to max_additional
        results_to_process = all_results[skip_first:skip_first + max_additional]
        logger.info(f"After skipping {skip_first} URLs, {len(results_to_process)} URLs remain to be processed")
        
        # Process remaining URLs
        total_processed = 0
        total_blacklisted = 0
        total_skipped = 0
        total_llm = 0
        total_fallback = 0
        new_blacklisted_urls = []
        start_time = time.time()
        
        # Set up cost tracking
        cost_claude = 0
        cost_llama = 0
        
        # Process in batches to avoid memory issues
        batch_size = 10
        for i in range(0, len(results_to_process), batch_size):
            batch = results_to_process[i:i + batch_size]
            batch_analyzed = 0
            batch_blacklisted = 0
            batch_skipped = 0
            batch_llm = 0
            batch_fallback = 0
            
            for result in batch:
                # Extract URL from result
                url = result.get("url", "")
                
                if not url or not url.startswith("http"):
                    logger.warning(f"Invalid URL in Pinecone: {url}")
                    continue
                
                # Skip if already blacklisted
                if url in existing_blacklisted:
                    logger.info(f"Skipping already blacklisted URL: {url}")
                    batch_skipped += 1
                    total_skipped += 1
                    continue
                
                # Get content from result
                content = result.get("text", "")
                
                # Create content object for analysis
                from app.models.url import URLContent, URLContentMatch
                
                # Create content with empty mentions
                url_content = URLContent(
                    url=url,
                    title=result.get("title", ""),
                    content=content,
                    mentions=[]
                )
                
                # Add text as URLContentMatch if we have content
                if content:
                    match = URLContentMatch(
                        text=content,
                        position=0,  # Add position field
                        context_before=result.get("context_before", ""),
                        context_after=result.get("context_after", ""),
                        embedding_id="reanalysis"
                    )
                    url_content.mentions.append(match)
                
                try:
                    # First try with OpenRouter
                    analysis_result = None
                    analysis_method = "fallback"
                    
                    try:
                        # Try OpenRouter first
                        logger.info(f"Analyzing URL with OpenRouter: {url}")
                        analysis_result = await ai_service.analyze_content(url_content)
                        analysis_method = "real_llm"
                        batch_llm += 1
                        total_llm += 1
                        logger.info(f"Successfully analyzed URL {url} using OpenRouter")
                    except Exception as e:
                        # OpenRouter failed, use fallback
                        logger.warning(f"OpenRouter analysis failed for URL {url}: {str(e)}")
                        logger.info(f"Falling back to keyword analysis for URL: {url}")
                        analysis_result = blacklist_keywords.analyze_content(url_content)
                        analysis_method = "fallback"
                        batch_fallback += 1
                        total_fallback += 1
                        logger.info(f"Successfully analyzed URL {url} using keyword fallback")
                    
                    # Check if blacklisted
                    if analysis_result and analysis_result.category == URLCategory.BLACKLIST:
                        logger.info(f"Blacklisted URL: {url}")
                        batch_blacklisted += 1
                        total_blacklisted += 1
                        
                        # Extract domain
                        domain = urlparse(url).netloc
                        
                        # Create a new blacklist entry
                        new_entry = {
                            "URL": url,
                            "Main Domain": domain,
                            "Reason": analysis_result.explanation,
                            "Confidence": analysis_result.confidence,
                            "Category": "URLCategory.BLACKLIST",
                            "Compliance Issues": ",".join(analysis_result.compliance_issues),
                            "Batch ID": batch_id,
                            "Timestamp": datetime.now().isoformat()
                        }
                        
                        new_blacklisted_urls.append(new_entry)
                    
                    batch_analyzed += 1
                    total_processed += 1
                    
                    # Calculate token usage and costs
                    estimated_tokens = AVG_TOKENS_PER_ANALYSIS
                    if analysis_method == "real_llm":
                        cost_claude += (estimated_tokens / 1000) * CLAUDE_3_OPUS_COST_PER_1K
                        cost_llama += (estimated_tokens / 1000) * LLAMA_70B_COST_PER_1K
                    
                except Exception as e:
                    logger.error(f"Error analyzing URL {url}: {str(e)}")
            
            # Report progress at the end of each batch
            elapsed = time.time() - start_time
            urls_per_second = total_processed / elapsed if elapsed > 0 else 0
            remaining_urls = len(results_to_process) - total_processed - total_skipped
            est_remaining_time = remaining_urls / urls_per_second if urls_per_second > 0 else 0
            
            # Calculate cost savings
            cost_savings = cost_claude - cost_llama
            
            logger.info(f"Batch progress: {batch_analyzed} URLs analyzed, {batch_blacklisted} blacklisted, {batch_skipped} skipped")
            logger.info(f"Batch methods: {batch_llm} LLM, {batch_fallback} fallback")
            logger.info(f"Overall progress: {total_processed}/{len(results_to_process)} URLs analyzed, {total_blacklisted} blacklisted, {total_skipped} skipped")
            logger.info(f"Analysis methods: {total_llm} LLM ({total_llm/total_processed*100:.1f}%), {total_fallback} fallback ({total_fallback/total_processed*100:.1f}%)")
            logger.info(f"Speed: {urls_per_second:.2f} URLs/sec, Est. remaining: {est_remaining_time/60:.1f} min")
            logger.info(f"Cost: ${cost_llama:.4f} (saving ${cost_savings:.4f} vs Claude 3 Opus)")
            
            # Write new blacklisted URLs to the file periodically to avoid losing data
            if new_blacklisted_urls and (i + batch_size >= len(results_to_process) or len(new_blacklisted_urls) >= 10):
                try:
                    with open(blacklist_file, "a", newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=["URL", "Main Domain", "Reason", "Confidence", "Category", "Compliance Issues", "Batch ID", "Timestamp"])
                        writer.writerows(new_blacklisted_urls)
                    
                    logger.info(f"Added {len(new_blacklisted_urls)} new blacklisted URLs to {blacklist_file}")
                    new_blacklisted_urls = []  # Reset after writing
                except Exception as e:
                    logger.error(f"Error writing to blacklist file: {e}")
        
        # Write any remaining blacklisted URLs to the file
        if new_blacklisted_urls:
            try:
                with open(blacklist_file, "a", newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["URL", "Main Domain", "Reason", "Confidence", "Category", "Compliance Issues", "Batch ID", "Timestamp"])
                    writer.writerows(new_blacklisted_urls)
                
                logger.info(f"Added {len(new_blacklisted_urls)} new blacklisted URLs to {blacklist_file}")
            except Exception as e:
                logger.error(f"Error writing to blacklist file: {e}")
        
        # Final summary
        total_time = time.time() - start_time
        total_cost_claude = (total_llm * AVG_TOKENS_PER_ANALYSIS / 1000) * CLAUDE_3_OPUS_COST_PER_1K
        total_cost_llama = (total_llm * AVG_TOKENS_PER_ANALYSIS / 1000) * LLAMA_70B_COST_PER_1K
        total_savings = total_cost_claude - total_cost_llama
        
        logger.info(f"Reanalysis of remaining URLs complete: {total_processed} URLs analyzed, {total_blacklisted} newly blacklisted")
        logger.info(f"Analysis methods: {total_llm} LLM ({total_llm/total_processed*100:.1f}%), {total_fallback} fallback ({total_fallback/total_processed*100:.1f}%)")
        logger.info(f"Total time: {total_time:.1f} seconds ({total_processed/total_time:.2f} URLs/sec)")
        logger.info(f"Estimated cost: ${total_cost_llama:.4f} (saving ${total_savings:.4f} vs Claude 3 Opus)")
    
    except Exception as e:
        logger.error(f"Error during reanalysis: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Reanalyze remaining URLs stored in Pinecone with fallback")
    parser.add_argument("--skip-first", type=int, default=1000, help="Number of URLs to skip from the beginning")
    parser.add_argument("--max-additional", type=int, default=500, help="Maximum number of additional URLs to process")
    
    args = parser.parse_args()
    
    # Run the reanalysis
    asyncio.run(reanalyze_with_fallback(args.skip_first, args.max_additional)) 