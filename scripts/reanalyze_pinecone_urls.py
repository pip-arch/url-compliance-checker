#!/usr/bin/env python3
"""
Script to reanalyze URLs already stored in Pinecone
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
        logging.FileHandler("data/reanalysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cost calculation constants
CLAUDE_3_OPUS_COST_PER_1K = 0.015  # $0.015 per 1K tokens
LLAMA_70B_COST_PER_1K = 0.0009  # $0.0009 per 1K tokens
AVG_TOKENS_PER_ANALYSIS = 3000  # Estimated average tokens per analysis

async def reanalyze_urls(max_urls=1000, reanalyze_reviewed=False):
    """
    Reanalyze URLs already stored in Pinecone
    
    Args:
        max_urls (int): Maximum number of URLs to reanalyze
        reanalyze_reviewed (bool): Whether to reanalyze URLs that have already been reviewed
    """
    # Import modules
    from app.services.vector_db import pinecone_service
    from app.services.ai import ai_service
    from app.models.report import URLCategory, URLReport, AIAnalysisResult
    import os
    
    # Get current model name for logging
    current_model = os.getenv("OPENROUTER_MODEL", "unknown")
    logger.info(f"Using OpenRouter model: {current_model}")
    
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
        
        # Create a batch ID for this reanalysis
        batch_id = f"reanalysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
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
        
        # Query Pinecone for all URLs - using a general query that should match most URLs
        logger.info(f"Querying Pinecone for up to {max_urls} URLs...")
        results = await pinecone_service.search_similar_content(
            "url website internet", 
            top_k=min(total_count, max_urls)  # Get up to max_urls results
        )
        
        logger.info(f"Got {len(results)} results from Pinecone")
        
        # Process all URLs
        total_analyzed = 0
        total_blacklisted = 0
        total_skipped = 0
        new_blacklisted_urls = []
        start_time = time.time()
        
        # Set up cost tracking
        cost_claude = 0
        cost_llama = 0
        
        for i, result in enumerate(results):
            # Extract URL from result
            url = result.get("url", "")
            
            if not url or not url.startswith("http"):
                logger.warning(f"Invalid URL in Pinecone: {url}")
                continue
            
            # Skip if already blacklisted
            if url in existing_blacklisted:
                logger.info(f"Skipping already blacklisted URL: {url}")
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
                # Analyze content
                logger.info(f"Analyzing URL: {url}")
                analysis_result = await ai_service.analyze_content(url_content)
                
                # Check if blacklisted
                if analysis_result and analysis_result.category == URLCategory.BLACKLIST:
                    logger.info(f"Blacklisted URL: {url}")
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
                
                total_analyzed += 1
                
                # Calculate token usage and costs
                estimated_tokens = AVG_TOKENS_PER_ANALYSIS
                cost_claude += (estimated_tokens / 1000) * CLAUDE_3_OPUS_COST_PER_1K
                cost_llama += (estimated_tokens / 1000) * LLAMA_70B_COST_PER_1K
                
                # Report progress periodically
                if total_analyzed % 10 == 0 or i == len(results) - 1:
                    # Calculate progress statistics
                    elapsed = time.time() - start_time
                    urls_per_second = total_analyzed / elapsed if elapsed > 0 else 0
                    remaining_urls = len(results) - (i + 1)
                    est_remaining_time = remaining_urls / urls_per_second if urls_per_second > 0 else 0
                    
                    # Calculate cost savings
                    cost_savings = cost_claude - cost_llama
                    
                    logger.info(f"Progress: {total_analyzed}/{len(results)} URLs analyzed, {total_blacklisted} blacklisted, {total_skipped} skipped")
                    logger.info(f"Speed: {urls_per_second:.2f} URLs/sec, Est. remaining: {est_remaining_time/60:.1f} min")
                    logger.info(f"Cost: ${cost_llama:.4f} (saving ${cost_savings:.4f} vs Claude 3 Opus)")
            
            except Exception as e:
                logger.error(f"Error analyzing URL {url}: {e}")
        
        # Write new blacklisted URLs to the file
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
        total_cost_claude = (total_analyzed * AVG_TOKENS_PER_ANALYSIS / 1000) * CLAUDE_3_OPUS_COST_PER_1K
        total_cost_llama = (total_analyzed * AVG_TOKENS_PER_ANALYSIS / 1000) * LLAMA_70B_COST_PER_1K
        total_savings = total_cost_claude - total_cost_llama
        
        logger.info(f"Reanalysis complete: {total_analyzed} URLs analyzed, {total_blacklisted} newly blacklisted")
        logger.info(f"Total time: {total_time:.1f} seconds ({total_analyzed/total_time:.2f} URLs/sec)")
        logger.info(f"Estimated cost: ${total_cost_llama:.4f} (saving ${total_savings:.4f} vs Claude 3 Opus)")
    
    except Exception as e:
        logger.error(f"Error during reanalysis: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Reanalyze URLs already stored in Pinecone")
    parser.add_argument("--max-urls", type=int, default=1000, help="Maximum number of URLs to reanalyze")
    parser.add_argument("--reanalyze-reviewed", action="store_true", help="Reanalyze URLs that have already been reviewed")
    
    args = parser.parse_args()
    
    # Run the reanalysis
    asyncio.run(reanalyze_urls(args.max_urls, args.reanalyze_reviewed)) 