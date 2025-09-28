#!/usr/bin/env python3
"""
Script to get the total count of vectors in Pinecone index
"""
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

async def get_total_count():
    """Get total count of vectors in Pinecone index"""
    # Lazy import so we don't import unless needed
    from app.services.vector_db import pinecone_service
    
    # Ensure pinecone service is initialized
    if not pinecone_service.is_initialized:
        logger.error("Pinecone service not initialized")
        return
    
    # Get total count of vectors
    try:
        stats = pinecone_service.index.describe_index_stats()
        logger.info(f"Full stats: {stats}")
        
        if hasattr(stats, "total_vector_count"):
            total_count = stats.total_vector_count
            logger.info(f"Total vectors in Pinecone index: {total_count}")
        elif hasattr(stats, "namespaces"):
            total_count = sum(ns.get("vector_count", 0) for ns in stats.namespaces.values())
            logger.info(f"Total vectors in Pinecone index (summed across namespaces): {total_count}")
        elif hasattr(stats, "dimension"):
            # For pinecone v2
            logger.info(f"Pinecone index dimension: {stats.dimension}")
            logger.info(f"Total vectors: Stats object doesn't have total_vector_count")
    except Exception as e:
        logger.error(f"Error getting Pinecone stats: {e}")

if __name__ == "__main__":
    asyncio.run(get_total_count()) 