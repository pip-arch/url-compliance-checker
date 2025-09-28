"""
Pinecone vector database service for storing and retrieving URL content.
"""
import os
import logging
import json
import traceback
from typing import List, Dict, Any, Optional
import numpy as np
import pinecone
from sentence_transformers import SentenceTransformer
from app.models.url import URLContent, URLContentMatch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "url-checker-index")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))

# Print debug info - masked API key
if PINECONE_API_KEY:
    masked_key = PINECONE_API_KEY[:5] + "..." + PINECONE_API_KEY[-5:] if len(PINECONE_API_KEY) > 10 else "***"
    logger.info(f"Pinecone v3 config: API Key: {masked_key}, Index: {PINECONE_INDEX_NAME}, Environment: {PINECONE_ENVIRONMENT}")
else:
    logger.warning("No Pinecone API key found in environment variables!")

class PineconeService:
    """
    Service for interacting with Pinecone vector database:
    1. Initialize Pinecone client and embedding model
    2. Create or connect to index for storing URL content
    3. Generate embeddings for URL content
    4. Store and retrieve embeddings
    """
    
    def __init__(self):
        """Initialize Pinecone client and embedding model."""
        self.is_initialized = False
        self.encoder = None
        self.index = None
        
        try:
            if not PINECONE_API_KEY:
                logger.error("PINECONE_API_KEY not found in environment variables!")
                return
            
            # Initialize Pinecone client with v3 API
            logger.info(f"Initializing Pinecone with v3 API (version: {pinecone.__version__})")
            pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
            
            # List indexes
            indexes = pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            logger.info(f"Available indexes: {index_names}")
            
            # Check if our index exists
            if PINECONE_INDEX_NAME not in index_names:
                logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine"
                )
            else:
                logger.info(f"Using existing Pinecone index: {PINECONE_INDEX_NAME}")
            
            # Connect to index
            self.index = pc.Index(PINECONE_INDEX_NAME)
            
            # Initialize sentence transformer for embeddings
            self.encoder = SentenceTransformer(EMBEDDING_MODEL)
            
            self.is_initialized = True
            logger.info(f"Pinecone service successfully initialized with index: {PINECONE_INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone service: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using SentenceTransformer."""
        if not self.encoder:
            logger.error("Encoder not initialized, cannot generate embeddings")
            raise RuntimeError("Encoder not initialized")
        
        try:
            # Generate embedding
            embedding = self.encoder.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def store_content(self, url_content: URLContent) -> Dict[str, str]:
        """
        Store URL content in Pinecone:
        1. Generate embeddings for each mention
        2. Store embeddings with metadata
        3. Return mapping of mention to embedding ID
        """
        if not self.is_initialized or not self.index:
            logger.error("Pinecone service not initialized")
            raise RuntimeError("Pinecone service not initialized")
        
        if not url_content.mentions:
            logger.info(f"No mentions to store for URL: {url_content.url}")
            return {}
        
        embedding_ids = {}
        vectors_to_upsert = []
        
        try:
            # Generate embeddings for each mention
            for i, mention in enumerate(url_content.mentions):
                # Combine context and mention for embedding
                context_text = mention.context_before + mention.text + mention.context_after
                
                # Generate embedding
                embedding = self._generate_embedding(context_text)
                
                # Create embedding ID
                embedding_id = f"{url_content.url.replace('://', '_').replace('/', '_')}_{i}"
                embedding_ids[i] = embedding_id
                
                # Prepare metadata
                metadata = {
                    "url": url_content.url,
                    "title": url_content.title or "",
                    "text": mention.text,
                    "position": str(mention.position),  # Convert to string for Pinecone metadata
                    "context_before": mention.context_before,
                    "context_after": mention.context_after,
                    "crawled_at": url_content.crawled_at.isoformat()
                }
                
                # Add any custom metadata
                if url_content.metadata:
                    for k, v in url_content.metadata.items():
                        if isinstance(v, (str, int, float, bool)):
                            metadata[k] = str(v) if not isinstance(v, str) else v
                
                # Add to vectors for batch upsert
                vectors_to_upsert.append({
                    "id": embedding_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Batch upsert to Pinecone
            if vectors_to_upsert:
                logger.info(f"Upserting {len(vectors_to_upsert)} vectors to Pinecone")
                self.index.upsert(vectors=vectors_to_upsert)
                logger.info(f"Stored {len(vectors_to_upsert)} embeddings for URL: {url_content.url}")
            
            return embedding_ids
        except Exception as e:
            logger.error(f"Error storing content in Pinecone: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def search_similar_content(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar content in Pinecone:
        1. Generate embedding for query text
        2. Search for similar embeddings
        3. Return matches with metadata
        """
        if not self.is_initialized or not self.index:
            logger.error("Pinecone service not initialized")
            raise RuntimeError("Pinecone service not initialized")
        
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            # Format results for v3 response format
            matches = []
            for match in results.matches:
                match_data = {
                    "id": match.id,
                    "score": match.score,
                    "url": match.metadata.get("url", ""),
                    "title": match.metadata.get("title", ""),
                    "text": match.metadata.get("text", ""),
                    "context_before": match.metadata.get("context_before", ""),
                    "context_after": match.metadata.get("context_after", ""),
                    "crawled_at": match.metadata.get("crawled_at", "")
                }
                matches.append(match_data)
            
            logger.info(f"Found {len(matches)} similar content for query")
            return matches
        except Exception as e:
            logger.error(f"Error searching Pinecone: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def delete_content(self, url: str) -> bool:
        """Delete all content for a specific URL."""
        if not self.is_initialized or not self.index:
            logger.error("Pinecone service not initialized")
            raise RuntimeError("Pinecone service not initialized")
        
        try:
            # Format URL for embedding ID prefix
            url_prefix = url.replace("://", "_").replace("/", "_")
            
            # Find all embeddings with this URL prefix using filtering
            filter_dict = {"url": {"$eq": url}}
            
            # Create a dummy vector for metadata-only filter
            zero_vector = [0.0] * EMBEDDING_DIMENSION
            
            # Query for matching IDs
            results = self.index.query(
                vector=zero_vector,
                top_k=100,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Extract IDs
            ids_to_delete = [match.id for match in results.matches]
            
            if not ids_to_delete:
                logger.info(f"No embeddings found for URL: {url}")
                return True
            
            # Delete embeddings
            self.index.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} embeddings for URL: {url}")
            return True
        except Exception as e:
            logger.error(f"Error deleting content from Pinecone: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise


# Singleton instance
logger.info("Creating PineconeService instance...")
pinecone_service = PineconeService()
logger.info(f"PineconeService initialized: {pinecone_service.is_initialized}") 