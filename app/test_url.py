"""
Test script to verify Pinecone integration and check if information is being saved correctly.
"""
import asyncio
import logging
from datetime import datetime
from app.models.url import URLContent, URLContentMatch
from app.services.vector_db import pinecone_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pinecone_integration():
    """Test Pinecone integration with a sample URL content that contains mentions of Admiral Markets."""
    logger.info("Starting Pinecone integration test...")
    
    # Creating a sample URLContent with multiple mentions of admiralmarkets
    sample_content = URLContent(
        url="https://test-blog.example.com/review-of-admiralmarkets",
        title="Comprehensive Review of Admiral Markets",
        full_text="""
        Admiral Markets is a globally recognized broker offering trading services for forex, CFDs, stocks, and more.
        Founded in 2001, admiralmarkets has built a reputation for reliability and transparency.
        Traders using admiralmarkets have access to the MT4 and MT5 platforms.
        The company is regulated by several authorities, ensuring AdmiralMarkets customers are protected.
        Visit https://admiralmarkets.com for more information about their services.
        """,
        crawled_at=datetime.now(),
        metadata={"source": "test", "crawled_with": "test_script"}
    )
    
    # Find all mentions of admiralmarkets (case insensitive)
    mention_variations = ["Admiral Markets", "admiralmarkets", "AdmiralMarkets"]
    for variation in mention_variations:
        find_and_add_mentions(sample_content, variation)
        
    logger.info(f"Created sample content with {len(sample_content.mentions)} mentions")
    
    # Store the content in Pinecone
    if not pinecone_service.is_initialized:
        logger.error("Pinecone service is not initialized! Test will fail.")
        return False
    
    embedding_ids = await pinecone_service.store_content(sample_content)
    
    # Verify results
    logger.info(f"Stored {len(embedding_ids)} embeddings in Pinecone")
    for idx, embedding_id in embedding_ids.items():
        logger.info(f"Mention {idx}: {sample_content.mentions[idx].text} -> Embedding ID: {embedding_id}")
    
    # Test search functionality
    logger.info("Testing search functionality...")
    search_results = await pinecone_service.search_similar_content("Admiral Markets review", top_k=3)
    
    logger.info(f"Found {len(search_results)} similar content items")
    for i, result in enumerate(search_results):
        logger.info(f"Result {i+1}: Score: {result['score']:.4f}, URL: {result['url']}")
        logger.info(f"  Title: {result['title']}")
        logger.info(f"  Text: {result['text']}")
        logger.info(f"  Context: ...{result['context_before']} [{result['text']}] {result['context_after']}...")
    
    return len(embedding_ids) > 0 and len(search_results) > 0

def find_and_add_mentions(url_content: URLContent, mention_text: str):
    """Find all instances of mention_text in the full_text and add them as URLContentMatch objects."""
    if not url_content.full_text:
        return
    
    full_text_lower = url_content.full_text.lower()
    mention_text_lower = mention_text.lower()
    
    # Find all occurrences
    start_pos = 0
    while True:
        pos = full_text_lower.find(mention_text_lower, start_pos)
        if pos == -1:
            break
            
        # Get context (100 characters before and after)
        context_start = max(0, pos - 100)
        context_end = min(len(url_content.full_text), pos + len(mention_text) + 100)
        
        # Add the mention
        url_content.mentions.append(URLContentMatch(
            text=url_content.full_text[pos:pos+len(mention_text)],  # Use the actual case from the text
            position=pos,
            context_before=url_content.full_text[context_start:pos],
            context_after=url_content.full_text[pos+len(mention_text):context_end]
        ))
        
        # Move to the next position
        start_pos = pos + len(mention_text)

async def main():
    """Run the test and report results."""
    success = await test_pinecone_integration()
    if success:
        logger.info("✅ Pinecone integration test PASSED - Successfully stored and retrieved embeddings!")
    else:
        logger.error("❌ Pinecone integration test FAILED - Could not store or retrieve embeddings.")

if __name__ == "__main__":
    asyncio.run(main()) 