"""
Service for storing and managing failed URLs.
"""
import os
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.url import URL, URLStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
DATA_DIR = os.getenv("DATA_DIR", "./data")
FAILED_URLS_DB = os.getenv("FAILED_URLS_DB", "failed_urls.db")

class FailedURLService:
    """
    Service for storing and managing failed URLs for later review:
    1. Store failed URLs with error information
    2. Retrieve failed URLs for manual review
    3. Mark failed URLs as reviewed
    4. Export failed URLs to CSV
    """

    def __init__(self):
        """Initialize the failed URL service."""
        # Ensure data directory exists
        self.data_dir = Path(DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
        
        # Database path
        self.db_path = self.data_dir / FAILED_URLS_DB
        
        # Initialize database
        self._init_db()
        
        logger.info(f"FailedURLService initialized with database at: {self.db_path}")

    def _init_db(self):
        """Initialize the database with the required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create failed URLs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS failed_urls (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    error TEXT,
                    attempt_count INTEGER DEFAULT 1,
                    last_attempt_at TEXT,
                    created_at TEXT,
                    status TEXT DEFAULT 'failed',
                    metadata TEXT
                )
            ''')
            
            # Create failed URLs index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_failed_urls_batch_id ON failed_urls(batch_id)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Failed URLs database initialized")
        except Exception as e:
            logger.error(f"Error initializing failed URLs database: {str(e)}")
            raise

    async def store_failed_url(self, url_obj: URL) -> bool:
        """
        Store a failed URL in the database.
        If the URL already exists, increment the attempt count.
        
        Args:
            url_obj: The URL object that failed processing
            
        Returns:
            bool: True if the URL was stored successfully
        """
        try:
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if URL already exists
            cursor.execute("SELECT id, attempt_count FROM failed_urls WHERE url = ?", (url_obj.url,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry
                cursor.execute(
                    "UPDATE failed_urls SET attempt_count = ?, last_attempt_at = ?, error = ? WHERE id = ?",
                    (existing[1] + 1, now, url_obj.error, existing[0])
                )
                logger.info(f"Updated failed URL: {url_obj.url} (attempt {existing[1] + 1})")
            else:
                # Insert new entry
                metadata = json.dumps(url_obj.dict()) if hasattr(url_obj, "dict") else "{}"
                cursor.execute(
                    "INSERT INTO failed_urls (id, url, batch_id, error, last_attempt_at, created_at, status, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (url_obj.id, url_obj.url, url_obj.batch_id, url_obj.error, now, now, URLStatus.FAILED.value, metadata)
                )
                logger.info(f"Stored failed URL: {url_obj.url}")
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Error storing failed URL {url_obj.url}: {str(e)}")
            return False

    async def get_failed_urls(self, batch_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get failed URLs for review.
        
        Args:
            batch_id: Optional batch ID to filter by
            limit: Maximum number of URLs to return
            offset: Offset for pagination
            
        Returns:
            List of failed URL objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if batch_id:
                cursor.execute(
                    "SELECT * FROM failed_urls WHERE batch_id = ? ORDER BY last_attempt_at DESC LIMIT ? OFFSET ?",
                    (batch_id, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM failed_urls ORDER BY last_attempt_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries
            failed_urls = []
            for row in rows:
                url_data = dict(row)
                if "metadata" in url_data and url_data["metadata"]:
                    try:
                        url_data["metadata"] = json.loads(url_data["metadata"])
                    except:
                        url_data["metadata"] = {}
                failed_urls.append(url_data)
            
            logger.info(f"Retrieved {len(failed_urls)} failed URLs")
            return failed_urls
        except Exception as e:
            logger.error(f"Error retrieving failed URLs: {str(e)}")
            return []

    async def mark_as_reviewed(self, url_id: str, notes: Optional[str] = None) -> bool:
        """
        Mark a failed URL as reviewed.
        
        Args:
            url_id: The ID of the URL to mark as reviewed
            notes: Optional notes from the reviewer
            
        Returns:
            bool: True if the URL was marked as reviewed successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update status and add notes
            cursor.execute(
                "UPDATE failed_urls SET status = ?, metadata = json_set(metadata, '$.review_notes', ?) WHERE id = ?",
                ("reviewed", notes or "", url_id)
            )
            
            if cursor.rowcount == 0:
                logger.warning(f"Failed URL with ID {url_id} not found")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            logger.info(f"Marked failed URL {url_id} as reviewed")
            return True
        except Exception as e:
            logger.error(f"Error marking failed URL {url_id} as reviewed: {str(e)}")
            return False

    async def retry_failed_url(self, url_id: str) -> Dict[str, Any]:
        """
        Get a failed URL for retry.
        
        Args:
            url_id: The ID of the URL to retry
            
        Returns:
            Dict with URL information, or empty dict if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM failed_urls WHERE id = ?", (url_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning(f"Failed URL with ID {url_id} not found")
                return {}
            
            url_data = dict(row)
            if "metadata" in url_data and url_data["metadata"]:
                try:
                    url_data["metadata"] = json.loads(url_data["metadata"])
                except:
                    url_data["metadata"] = {}
            
            logger.info(f"Retrieved failed URL {url_id} for retry")
            return url_data
        except Exception as e:
            logger.error(f"Error retrieving failed URL {url_id} for retry: {str(e)}")
            return {}

    async def export_failed_urls(self, batch_id: Optional[str] = None, format: str = "json") -> str:
        """
        Export failed URLs to a file.
        
        Args:
            batch_id: Optional batch ID to filter by
            format: Export format (json or csv)
            
        Returns:
            str: Path to the exported file
        """
        try:
            # Get failed URLs
            failed_urls = await self.get_failed_urls(batch_id, limit=10000)
            
            if not failed_urls:
                logger.warning("No failed URLs to export")
                return ""
            
            # Create export file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_suffix = f"_{batch_id}" if batch_id else ""
            filename = f"failed_urls{batch_suffix}_{timestamp}.{format}"
            export_path = self.data_dir / filename
            
            if format == "json":
                with open(export_path, "w") as f:
                    json.dump(failed_urls, f, indent=2)
            elif format == "csv":
                import csv
                with open(export_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(["id", "url", "batch_id", "error", "attempt_count", "last_attempt_at", "status"])
                    # Write data
                    for url in failed_urls:
                        writer.writerow([
                            url.get("id", ""),
                            url.get("url", ""),
                            url.get("batch_id", ""),
                            url.get("error", ""),
                            url.get("attempt_count", 1),
                            url.get("last_attempt_at", ""),
                            url.get("status", "failed")
                        ])
            else:
                logger.error(f"Unsupported export format: {format}")
                return ""
            
            logger.info(f"Exported {len(failed_urls)} failed URLs to {export_path}")
            return str(export_path)
        except Exception as e:
            logger.error(f"Error exporting failed URLs: {str(e)}")
            return ""

# Create a singleton instance
failed_url_service = FailedURLService() 