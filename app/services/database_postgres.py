"""PostgreSQL-compatible database service using SQLAlchemy."""
import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text, pool
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from dotenv import load_dotenv

from app.models.url import URL, URLBatch, URLContent, URLContentMatch, URLStatus, URLFilterReason
from app.models.report import ComplianceReport, URLReport, ReportStatus, URLCategory

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL.startswith("postgresql://"):
    logger.error(f"Invalid PostgreSQL URL: {DATABASE_URL[:50]}...")
    raise ValueError(f"Invalid PostgreSQL URL. Please check your .env file.")

class DatabaseService:
    """PostgreSQL-compatible database service."""
    
    def __init__(self):
        """Initialize database connection."""
        # Create engine with connection pooling
        self.engine: Engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,  # Test connections before using
            echo=False  # Set to True for SQL debugging
        )
        logger.info(f"Initialized PostgreSQL database service")
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    
    async def save_batch(self, batch: URLBatch) -> str:
        """Save a URL batch to the database."""
        with self.get_connection() as conn:
            query = text("""
                INSERT INTO processing_batches (id, description, filename, url_count, processed_count, status, created_at, updated_at)
                VALUES (:id, :description, :filename, :url_count, :processed_count, :status, :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                    description = EXCLUDED.description,
                    filename = EXCLUDED.filename,
                    url_count = EXCLUDED.url_count,
                    processed_count = EXCLUDED.processed_count,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """)
            
            conn.execute(query, {
                'id': batch.id,
                'description': batch.description,
                'filename': batch.filename,
                'url_count': batch.url_count,
                'processed_count': batch.processed_count,
                'status': batch.status.value,
                'created_at': batch.created_at,
                'updated_at': datetime.now()
            })
            conn.commit()
        return batch.id
    
    async def save_url(self, url: URL) -> str:
        """Save a URL to the database."""
        with self.get_connection() as conn:
            # Save to url_processing_queue
            query = text("""
                INSERT INTO url_processing_queue (url, domain, main_domain, source_file, priority, status, retry_count, created_at, updated_at)
                VALUES (:url, :domain, :main_domain, :source_file, :priority, :status, :retry_count, :created_at, :updated_at)
                ON CONFLICT(url) DO UPDATE SET
                    status = EXCLUDED.status,
                    retry_count = EXCLUDED.retry_count,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url.url)
            domain = parsed.netloc
            main_domain = '.'.join(domain.split('.')[-2:]) if '.' in domain else domain
            
            result = conn.execute(query, {
                'url': url.url,
                'domain': domain,
                'main_domain': main_domain,
                'source_file': url.batch_id,
                'priority': 1,
                'status': url.status.value,
                'retry_count': 0,
                'created_at': url.created_at,
                'updated_at': datetime.now()
            })
            conn.commit()
            
            # Get the ID
            row = result.fetchone()
            if row:
                return str(row[0])
            return url.id
    
    async def get_url(self, url_id: str) -> Optional[URL]:
        """Get a URL from the database."""
        with self.get_connection() as conn:
            query = text("SELECT * FROM url_processing_queue WHERE id = :id")
            result = conn.execute(query, {'id': url_id})
            row = result.fetchone()
            
            if not row:
                return None
                
            return URL(
                id=str(row['id']),
                url=row['url'],
                batch_id=row['source_file'],
                status=URLStatus(row['status']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_batch(self, batch_id: str) -> Optional[URLBatch]:
        """Get a batch from the database."""
        with self.get_connection() as conn:
            query = text("SELECT * FROM processing_batches WHERE id = :id")
            result = conn.execute(query, {'id': batch_id})
            row = result.fetchone()
            
            if not row:
                return None
                
            return URLBatch(
                id=row['id'],
                description=row['description'],
                filename=row['filename'],
                url_count=row['url_count'],
                processed_count=row['processed_count'],
                status=URLStatus(row['status']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def update_batch(self, batch: URLBatch) -> None:
        """Update a batch in the database."""
        await self.save_batch(batch)
    
    async def save_blacklisted_url(self, url: str, reason: str, batch_id: str) -> None:
        """Save a blacklisted URL to the database."""
        with self.get_connection() as conn:
            # Update url_processing_queue
            query = text("""
                UPDATE url_processing_queue 
                SET status = 'blacklisted'
                WHERE url = :url
            """)
            conn.execute(query, {'url': url})
            
            # You can also create a separate blacklist table if needed
            conn.commit()
    
    # Minimal implementations for compatibility
    async def get_all_batches(self, limit: int = 100, offset: int = 0) -> List[URLBatch]:
        """Get all batches."""
        return []
    
    async def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch."""
        return True
    
    async def get_urls_by_batch(self, batch_id: str, limit: int = 100, offset: int = 0) -> List[URL]:
        """Get URLs by batch."""
        return []
    
    async def get_processed_urls_by_batch(self, batch_id: str) -> List[URL]:
        """Get processed URLs by batch."""
        return []
    
    async def update_url(self, url: URL) -> None:
        """Update a URL."""
        await self.save_url(url)
    
    async def delete_url(self, url_id: str) -> bool:
        """Delete a URL."""
        return True
    
    async def save_report(self, report: ComplianceReport) -> str:
        """Save a report."""
        return report.id
    
    async def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get a report."""
        return None
    
    async def get_reports(self, limit: int = 100, offset: int = 0) -> List[ComplianceReport]:
        """Get reports."""
        return []
    
    async def save_url_report(self, report_id: str, url_report: URLReport) -> int:
        """Save URL report."""
        return 1
    
    async def get_url_reports(self, report_id: str, category: Optional[URLCategory] = None, 
                              limit: int = 100, offset: int = 0) -> List[URLReport]:
        """Get URL reports."""
        return []
    
    async def get_all_url_reports(self, category: Optional[URLCategory] = None, 
                                  limit: int = 1000, offset: int = 0) -> List[URLReport]:
        """Get all URL reports."""
        return []
    
    async def get_url_report_by_url_id(self, url_id: str) -> Optional[URLReport]:
        """Get URL report by URL ID."""
        return None
    
    async def update_report(self, report: ComplianceReport) -> None:
        """Update a report."""
        pass 