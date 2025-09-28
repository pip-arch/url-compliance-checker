"""
Test script to search for content in Pinecone based on keywords.
"""
import asyncio
import logging
from app.services.vector_db import pinecone_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def search_pinecone(query: str, top_k: int = 5):
    """Search for content in Pinecone based on the provided query."""
    logger.info(f"Searching for: '{query}' (top {top_k} results)")
    
    if not pinecone_service.is_initialized:
        logger.error("Pinecone service is not initialized!")
        return
    
    results = await pinecone_service.search_similar_content(query, top_k=top_k)
    
    logger.info(f"Found {len(results)} results")
    if not results:
        logger.info("No results found.")
        return
    
    # Display results
    logger.info("=" * 80)
    logger.info(f"SEARCH RESULTS FOR: '{query}'")
    logger.info("=" * 80)
    
    for i, result in enumerate(results):
        logger.info(f"\nResult {i+1} (Score: {result['score']:.4f})")
        logger.info(f"URL: {result['url']}")
        logger.info(f"Title: {result['title']}")
        logger.info("-" * 40)
        logger.info(f"Mention: {result['text']}")
        logger.info(f"Context: ...{result['context_before']} [{result['text']}] {result['context_after']}...")
        logger.info("-" * 40)
    
    logger.info("\n" + "=" * 80)

async def main():
    """Run multiple searches to test Pinecone."""
    search_queries = [
        "Admiral Markets review",
        "forex trading Admiral Markets",
        "Admiral Markets reliability",
        "trading platforms admiralmarkets",
        "AdmiralMarkets regulations"
    ]
    
    for query in search_queries:
        await search_pinecone(query)
        logger.info("\n")

if __name__ == "__main__":
    asyncio.run(main()) 