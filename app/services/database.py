"""
Database service for storing and retrieving URL data.
"""
import os
import logging
import sqlite3
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import asyncio

from app.models.url import URL, URLBatch, URLContent, URLContentMatch, URLStatus, URLFilterReason
from app.models.report import (
    ComplianceReport, URLReport, ComplianceRuleMatch, 
    AIAnalysisResult, ReportStatus, URLCategory
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database path from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/url_checker.db")
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_PATH = DATABASE_URL.replace("sqlite:///", "")
else:
    logger.warning(f"Unsupported database URL: {DATABASE_URL}, falling back to SQLite")
    DATABASE_PATH = "./data/url_checker.db"


class DatabaseService:
    """
    Service for interacting with the SQLite database:
    1. Store and retrieve URL data
    2. Store and retrieve URL batch data
    3. Store and retrieve compliance reports
    """
    
    def __init__(self):
        """Initialize database connection."""
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure the database file and parent directory exist."""
        db_dir = os.path.dirname(DATABASE_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection (thread-safe)."""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL query."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def _execute_many(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """Execute a SQL query with multiple parameter sets."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor
    
    def _fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row from a SQL query."""
        cursor = self._execute_query(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def _fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from a SQL query."""
        cursor = self._execute_query(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def save_batch(self, batch: URLBatch) -> str:
        """Save a URL batch to the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._save_batch, batch)
        except Exception as e:
            logger.error(f"Error in save_batch: {e}", exc_info=True)
            raise
    
    def _save_batch(self, batch: URLBatch) -> str:
        """Synchronous implementation of save_batch."""
        query = """
        INSERT INTO url_batches (id, description, filename, url_count, processed_count, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            description = excluded.description,
            filename = excluded.filename,
            url_count = excluded.url_count,
            processed_count = excluded.processed_count,
            status = excluded.status,
            updated_at = excluded.updated_at
        """
        params = (
            batch.id,
            batch.description,
            batch.filename,
            batch.url_count,
            batch.processed_count,
            batch.status.value,
            batch.created_at.isoformat(),
            datetime.now().isoformat()
        )
        self._execute_query(query, params)
        return batch.id
    
    async def get_batch(self, batch_id: str) -> Optional[URLBatch]:
        """Get a URL batch from the database."""
        try:
            loop = asyncio.get_event_loop()
            batch_data = await loop.run_in_executor(None, self._fetch_one, 
                "SELECT * FROM url_batches WHERE id = ?", (batch_id,))
            if batch_data is None:
                return None
            return URLBatch(
                id=batch_data["id"],
                description=batch_data["description"],
                filename=batch_data["filename"],
                url_count=batch_data["url_count"],
                processed_count=batch_data["processed_count"],
                status=URLStatus(batch_data["status"]),
                created_at=datetime.fromisoformat(batch_data["created_at"]),
                updated_at=datetime.fromisoformat(batch_data["updated_at"])
            )
        except Exception as e:
            logger.error(f"Error in get_batch: {e}", exc_info=True)
            raise
    
    async def get_all_batches(self, limit: int = 100, offset: int = 0) -> List[URLBatch]:
        """Get all URL batches from the database."""
        try:
            loop = asyncio.get_event_loop()
            batches_data = await loop.run_in_executor(None, self._fetch_all,
                "SELECT * FROM url_batches ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                (limit, offset))
            return [URLBatch(
                id=batch_data["id"],
                description=batch_data["description"],
                filename=batch_data["filename"],
                url_count=batch_data["url_count"],
                processed_count=batch_data["processed_count"],
                status=URLStatus(batch_data["status"]),
                created_at=datetime.fromisoformat(batch_data["created_at"]),
                updated_at=datetime.fromisoformat(batch_data["updated_at"])
            ) for batch_data in batches_data]
        except Exception as e:
            logger.error(f"Error in get_all_batches: {e}", exc_info=True)
            raise
    
    async def update_batch(self, batch: URLBatch) -> None:
        """Update a URL batch in the database."""
        try:
            await self.save_batch(batch)
        except Exception as e:
            logger.error(f"Error in update_batch: {e}", exc_info=True)
            raise
    
    async def delete_batch(self, batch_id: str) -> bool:
        """Delete a URL batch from the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._delete_batch, batch_id)
        except Exception as e:
            logger.error(f"Error in delete_batch: {e}", exc_info=True)
            raise
    
    def _delete_batch(self, batch_id: str) -> bool:
        """Synchronous implementation of delete_batch."""
        # First delete all URLs in the batch
        self._execute_query("DELETE FROM urls WHERE batch_id = ?", (batch_id,))
        
        # Then delete the batch
        cursor = self._execute_query("DELETE FROM url_batches WHERE id = ?", (batch_id,))
        return cursor.rowcount > 0
    
    async def save_url(self, url: URL) -> str:
        """Save a URL to the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._save_url, url)
        except Exception as e:
            logger.error(f"Error in save_url: {e}", exc_info=True)
            raise
    
    def _save_url(self, url: URL) -> str:
        """Synchronous implementation of save_url."""
        query = """
        INSERT INTO urls (id, url, batch_id, status, filter_reason, created_at, updated_at, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            url = excluded.url,
            batch_id = excluded.batch_id,
            status = excluded.status,
            filter_reason = excluded.filter_reason,
            updated_at = excluded.updated_at,
            error = excluded.error
        """
        params = (
            url.id,
            url.url,
            url.batch_id,
            url.status.value,
            url.filter_reason.value if url.filter_reason else None,
            url.created_at.isoformat(),
            datetime.now().isoformat(),
            url.error
        )
        self._execute_query(query, params)
        
        # If URL has content, save it
        if url.content:
            self._save_url_content(url.id, url.content)
        
        return url.id
    
    def _save_url_content(self, url_id: str, content: URLContent) -> None:
        """Save URL content to the database."""
        # Save main content
        query = """
        INSERT INTO url_contents (url_id, title, full_text, crawled_at, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(url_id) DO UPDATE SET
            title = excluded.title,
            full_text = excluded.full_text,
            crawled_at = excluded.crawled_at,
            metadata = excluded.metadata
        """
        params = (
            url_id,
            content.title,
            content.full_text,
            content.crawled_at.isoformat(),
            json.dumps(content.metadata) if content.metadata else None
        )
        self._execute_query(query, params)
        
        # Save content matches
        if content.mentions:
            # First delete existing matches
            self._execute_query("DELETE FROM url_content_matches WHERE url_id = ?", (url_id,))
            
            # Then insert new matches
            query = """
            INSERT INTO url_content_matches 
            (url_id, text, position, context_before, context_after, embedding_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params_list = [
                (
                    url_id,
                    match.text,
                    match.position,
                    match.context_before,
                    match.context_after,
                    match.embedding_id
                )
                for match in content.mentions
            ]
            self._execute_many(query, params_list)
    
    async def get_url(self, url_id: str) -> Optional[URL]:
        """Get a URL from the database."""
        try:
            loop = asyncio.get_event_loop()
            url_data = await loop.run_in_executor(None, self._fetch_one,
                "SELECT * FROM urls WHERE id = ?", (url_id,))
            if url_data is None:
                return None
            url = URL(
                id=url_data["id"],
                url=url_data["url"],
                batch_id=url_data["batch_id"],
                status=URLStatus(url_data["status"]),
                filter_reason=None if url_data["filter_reason"] is None else URLFilterReason(url_data["filter_reason"]),
                created_at=datetime.fromisoformat(url_data["created_at"]),
                updated_at=datetime.fromisoformat(url_data["updated_at"]),
                error=url_data["error"]
            )
            content_data = await loop.run_in_executor(None, self._fetch_one,
                "SELECT * FROM url_contents WHERE url_id = ?", (url_id,))
            if content_data:
                matches = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM url_content_matches WHERE url_id = ?", (url_id,))
                url.content = URLContent(
                    url=url.url,
                    title=content_data["title"],
                    full_text=content_data["full_text"],
                    crawled_at=datetime.fromisoformat(content_data["crawled_at"]),
                    metadata=json.loads(content_data["metadata"]) if content_data["metadata"] else {},
                    mentions=[
                        URLContentMatch(
                            text=match["text"],
                            position=match["position"],
                            context_before=match["context_before"],
                            context_after=match["context_after"],
                            embedding_id=match["embedding_id"]
                        )
                        for match in matches
                    ]
                )
            return url
        except Exception as e:
            logger.error(f"Error in get_url: {e}", exc_info=True)
            raise
    
    async def get_urls_by_batch(self, batch_id: str, limit: int = 100, offset: int = 0) -> List[URL]:
        """Get all URLs for a batch from the database."""
        logger = logging.getLogger(__name__)
        try:
            loop = asyncio.get_event_loop()
            urls_data = await loop.run_in_executor(None, self._fetch_all,
                "SELECT * FROM urls WHERE batch_id = ? ORDER BY created_at LIMIT ? OFFSET ?", 
                (batch_id, limit, offset))
            
            urls = []
            for url_data in urls_data:
                url = URL(
                    id=url_data["id"],
                    url=url_data["url"],
                    batch_id=url_data["batch_id"],
                    status=URLStatus(url_data["status"]),
                    filter_reason=None if url_data["filter_reason"] is None else URLFilterReason(url_data["filter_reason"]),
                    created_at=datetime.fromisoformat(url_data["created_at"]),
                    updated_at=datetime.fromisoformat(url_data["updated_at"]),
                    error=url_data["error"]
                )
                urls.append(url)
            
            return urls
        except Exception as e:
            logger.error(f"Error in get_urls_by_batch for batch {batch_id}: {e}", exc_info=True)
            raise
    
    async def get_processed_urls_by_batch(self, batch_id: str) -> List[URL]:
        """Get all processed URLs for a batch from the database."""
        loop = asyncio.get_event_loop()
        urls_data = await loop.run_in_executor(None, self._fetch_all,
            "SELECT * FROM urls WHERE batch_id = ? AND status = ? ORDER BY created_at", 
            (batch_id, URLStatus.PROCESSED.value))
        
        urls = []
        for url_data in urls_data:
            url = await self.get_url(url_data["id"])
            if url:
                urls.append(url)
        
        return urls
    
    async def update_url(self, url: URL) -> None:
        """Update a URL in the database."""
        try:
            await self.save_url(url)
        except Exception as e:
            logger.error(f"Error in update_url: {e}", exc_info=True)
            raise
    
    async def delete_url(self, url_id: str) -> bool:
        """Delete a URL from the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._delete_url, url_id)
        except Exception as e:
            logger.error(f"Error in delete_url: {e}", exc_info=True)
            raise
    
    def _delete_url(self, url_id: str) -> bool:
        """Synchronous implementation of delete_url."""
        # Delete content matches
        self._execute_query("DELETE FROM url_content_matches WHERE url_id = ?", (url_id,))
        
        # Delete content
        self._execute_query("DELETE FROM url_contents WHERE url_id = ?", (url_id,))
        
        # Delete URL
        cursor = self._execute_query("DELETE FROM urls WHERE id = ?", (url_id,))
        return cursor.rowcount > 0
    
    async def save_report(self, report: ComplianceReport) -> str:
        """Save a compliance report to the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._save_report, report)
        except Exception as e:
            logger.error(f"Error in save_report: {e}", exc_info=True)
            raise
    
    def _save_report(self, report: ComplianceReport) -> str:
        """Synchronous implementation of save_report."""
        query = """
        INSERT INTO compliance_reports 
        (id, batch_id, status, blacklist_count, whitelist_count, review_count, 
         total_urls, processed_urls, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            batch_id = excluded.batch_id,
            status = excluded.status,
            blacklist_count = excluded.blacklist_count,
            whitelist_count = excluded.whitelist_count,
            review_count = excluded.review_count,
            total_urls = excluded.total_urls,
            processed_urls = excluded.processed_urls,
            updated_at = excluded.updated_at
        """
        params = (
            report.id,
            report.batch_id,
            report.status.value,
            report.blacklist_count,
            report.whitelist_count,
            report.review_count,
            report.total_urls,
            report.processed_urls,
            report.created_at.isoformat(),
            datetime.now().isoformat()
        )
        self._execute_query(query, params)
        return report.id
    
    async def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get a compliance report from the database."""
        try:
            loop = asyncio.get_event_loop()
            report_data = await loop.run_in_executor(None, self._fetch_one,
                "SELECT * FROM compliance_reports WHERE id = ?", (report_id,))
            if report_data is None:
                return None
            return ComplianceReport(
                id=report_data["id"],
                batch_id=report_data["batch_id"],
                status=ReportStatus(report_data["status"]),
                blacklist_count=report_data["blacklist_count"],
                whitelist_count=report_data["whitelist_count"],
                review_count=report_data["review_count"],
                total_urls=report_data["total_urls"],
                processed_urls=report_data["processed_urls"],
                created_at=datetime.fromisoformat(report_data["created_at"]),
                updated_at=datetime.fromisoformat(report_data["updated_at"])
            )
        except Exception as e:
            logger.error(f"Error in get_report: {e}", exc_info=True)
            raise
    
    async def get_reports(self, limit: int = 100, offset: int = 0) -> List[ComplianceReport]:
        """Get all compliance reports from the database."""
        try:
            loop = asyncio.get_event_loop()
            reports_data = await loop.run_in_executor(None, self._fetch_all,
                "SELECT * FROM compliance_reports ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                (limit, offset))
            return [ComplianceReport(
                id=report_data["id"],
                batch_id=report_data["batch_id"],
                status=ReportStatus(report_data["status"]),
                blacklist_count=report_data["blacklist_count"],
                whitelist_count=report_data["whitelist_count"],
                review_count=report_data["review_count"],
                total_urls=report_data["total_urls"],
                processed_urls=report_data["processed_urls"],
                created_at=datetime.fromisoformat(report_data["created_at"]),
                updated_at=datetime.fromisoformat(report_data["updated_at"])
            ) for report_data in reports_data]
        except Exception as e:
            logger.error(f"Error in get_reports: {e}", exc_info=True)
            raise
    
    async def save_url_report(self, report_id: str, url_report: URLReport) -> int:
        """Save a URL report to the database."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._save_url_report, report_id, url_report)
        except Exception as e:
            logger.error(f"Error in save_url_report: {e}", exc_info=True)
            raise
    
    def _save_url_report(self, report_id: str, url_report: URLReport) -> int:
        """Synchronous implementation of save_url_report."""
        # Insert URL report
        query = """
        INSERT INTO url_reports (url_id, report_id, url, category, created_at)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (
            url_report.url_id,
            report_id,
            url_report.url,
            url_report.category.value,
            url_report.created_at.isoformat()
        )
        cursor = self._execute_query(query, params)
        url_report_id = cursor.lastrowid
        
        # Insert rule matches
        if url_report.rule_matches:
            query = """
            INSERT INTO rule_matches 
            (url_report_id, rule_id, rule_name, rule_description, severity, match_text, context, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params_list = [
                (
                    url_report_id,
                    match.rule_id,
                    match.rule_name,
                    match.rule_description,
                    match.severity,
                    match.match_text,
                    match.context,
                    match.confidence
                )
                for match in url_report.rule_matches
            ]
            self._execute_many(query, params_list)
        
        # Insert AI analysis
        if url_report.ai_analysis:
            query = """
            INSERT INTO ai_analysis_results 
            (url_report_id, model, category, confidence, explanation, compliance_issues, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                url_report_id,
                url_report.ai_analysis.model,
                url_report.ai_analysis.category.value,
                url_report.ai_analysis.confidence,
                url_report.ai_analysis.explanation,
                json.dumps(url_report.ai_analysis.compliance_issues),
                json.dumps(url_report.ai_analysis.raw_response) if url_report.ai_analysis.raw_response else None
            )
            self._execute_query(query, params)
        
        return url_report_id
    
    async def get_url_reports(self, report_id: str, category: Optional[URLCategory] = None, 
                              limit: int = 100, offset: int = 0) -> List[URLReport]:
        """Get URL reports for a compliance report from the database."""
        try:
            loop = asyncio.get_event_loop()
            if category:
                url_reports_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM url_reports WHERE report_id = ? AND category = ? LIMIT ? OFFSET ?", 
                    (report_id, category.value, limit, offset))
            else:
                url_reports_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM url_reports WHERE report_id = ? LIMIT ? OFFSET ?", 
                    (report_id, limit, offset))
            url_reports = []
            for url_report_data in url_reports_data:
                url_report_id = url_report_data["id"]
                rule_matches_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM rule_matches WHERE url_report_id = ?", (url_report_id,))
                rule_matches = [ComplianceRuleMatch(
                    rule_id=match["rule_id"],
                    rule_name=match["rule_name"],
                    rule_description=match["rule_description"],
                    severity=match["severity"],
                    match_text=match["match_text"],
                    context=match["context"],
                    confidence=match["confidence"],
                    match_position=match.get("match_position", 0),
                    context_before=match.get("context_before", ""),
                    context_after=match.get("context_after", "")
                ) for match in rule_matches_data]
                ai_analysis_data = await loop.run_in_executor(None, self._fetch_one,
                    "SELECT * FROM ai_analysis_results WHERE url_report_id = ?", (url_report_id,))
                ai_analysis = None
                if ai_analysis_data:
                    ai_analysis = AIAnalysisResult(
                        model=ai_analysis_data["model"],
                        category=URLCategory(ai_analysis_data["category"]),
                        confidence=ai_analysis_data["confidence"],
                        explanation=ai_analysis_data["explanation"],
                        compliance_issues=json.loads(ai_analysis_data["compliance_issues"]),
                        raw_response=json.loads(ai_analysis_data["raw_response"]) if ai_analysis_data["raw_response"] else None
                    )
                url_report = URLReport(
                    url_id=url_report_data["url_id"],
                    url=url_report_data["url"],
                    category=URLCategory(url_report_data["category"]),
                    rule_matches=rule_matches,
                    ai_analysis=ai_analysis,
                    created_at=datetime.fromisoformat(url_report_data["created_at"])
                )
                url_reports.append(url_report)
            return url_reports
        except Exception as e:
            logger.error(f"Error in get_url_reports: {e}", exc_info=True)
            raise
    
    async def get_all_url_reports(self, category: Optional[URLCategory] = None, 
                                  limit: int = 1000, offset: int = 0) -> List[URLReport]:
        """Get all URL reports from the database, optionally filtered by category."""
        try:
            loop = asyncio.get_event_loop()
            if category:
                url_reports_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM url_reports WHERE category = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                    (category.value, limit, offset))
            else:
                url_reports_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM url_reports ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                    (limit, offset))
            
            url_reports = []
            for url_report_data in url_reports_data:
                url_report_id = url_report_data["id"]
                
                # Get rule matches
                rule_matches_data = await loop.run_in_executor(None, self._fetch_all,
                    "SELECT * FROM rule_matches WHERE url_report_id = ?", (url_report_id,))
                rule_matches = [ComplianceRuleMatch(
                    rule_id=match["rule_id"],
                    rule_name=match["rule_name"],
                    rule_description=match["rule_description"],
                    severity=match["severity"],
                    match_text=match["match_text"],
                    context=match["context"],
                    confidence=match["confidence"],
                    match_position=match.get("match_position", 0),
                    context_before=match.get("context_before", ""),
                    context_after=match.get("context_after", "")
                ) for match in rule_matches_data]
                
                # Get AI analysis
                ai_analysis_data = await loop.run_in_executor(None, self._fetch_one,
                    "SELECT * FROM ai_analysis_results WHERE url_report_id = ?", (url_report_id,))
                ai_analysis = None
                if ai_analysis_data:
                    ai_analysis = AIAnalysisResult(
                        model=ai_analysis_data["model"],
                        category=URLCategory(ai_analysis_data["category"]),
                        confidence=ai_analysis_data["confidence"],
                        explanation=ai_analysis_data["explanation"],
                        compliance_issues=json.loads(ai_analysis_data["compliance_issues"]),
                        raw_response=json.loads(ai_analysis_data["raw_response"]) if ai_analysis_data["raw_response"] else None
                    )
                
                # Get analysis method from URL if available
                url_data = await loop.run_in_executor(None, self._fetch_one,
                    "SELECT * FROM urls WHERE id = ?", (url_report_data["url_id"],))
                
                # Determine analysis method
                analysis_method = "unknown"
                if url_data and url_data.get("analysis_method"):
                    analysis_method = url_data["analysis_method"]
                elif ai_analysis:
                    # Try to infer from model name
                    if "openrouter" in ai_analysis.model.lower() or "llama" in ai_analysis.model.lower():
                        analysis_method = "real_llm"
                    elif "openai" in ai_analysis.model.lower() or "gpt" in ai_analysis.model.lower():
                        analysis_method = "openai"
                    else:
                        analysis_method = "fallback"
                
                url_report = URLReport(
                    url_id=url_report_data["url_id"],
                    url=url_report_data["url"],
                    category=URLCategory(url_report_data["category"]),
                    rule_matches=rule_matches,
                    ai_analysis=ai_analysis,
                    created_at=datetime.fromisoformat(url_report_data["created_at"]),
                    analysis_method=analysis_method
                )
                url_reports.append(url_report)
            
            return url_reports
        except Exception as e:
            logger.error(f"Error in get_all_url_reports: {e}", exc_info=True)
            raise
            
    async def get_url_report_by_url_id(self, url_id: str) -> Optional[URLReport]:
        """Get URL report for a specific URL ID."""
        try:
            loop = asyncio.get_event_loop()
            # Get the latest URL report for this URL ID
            url_report_data = await loop.run_in_executor(None, self._fetch_one,
                "SELECT * FROM url_reports WHERE url_id = ? ORDER BY created_at DESC LIMIT 1", 
                (url_id,))
            
            if not url_report_data:
                return None
                
            url_report_id = url_report_data["id"]
            
            # Get rule matches
            rule_matches_data = await loop.run_in_executor(None, self._fetch_all,
                "SELECT * FROM rule_matches WHERE url_report_id = ?", (url_report_id,))
            rule_matches = [ComplianceRuleMatch(
                rule_id=match["rule_id"],
                rule_name=match["rule_name"],
                rule_description=match["rule_description"],
                severity=match["severity"],
                match_text=match["match_text"],
                context=match["context"],
                confidence=match["confidence"],
                match_position=match.get("match_position", 0),
                context_before=match.get("context_before", ""),
                context_after=match.get("context_after", "")
            ) for match in rule_matches_data]
            
            # Get AI analysis
            ai_analysis_data = await loop.run_in_executor(None, self._fetch_one,
                "SELECT * FROM ai_analysis_results WHERE url_report_id = ?", (url_report_id,))
            ai_analysis = None
            if ai_analysis_data:
                ai_analysis = AIAnalysisResult(
                    model=ai_analysis_data["model"],
                    category=URLCategory(ai_analysis_data["category"]),
                    confidence=ai_analysis_data["confidence"],
                    explanation=ai_analysis_data["explanation"],
                    compliance_issues=json.loads(ai_analysis_data["compliance_issues"]),
                    raw_response=json.loads(ai_analysis_data["raw_response"]) if ai_analysis_data["raw_response"] else None
                )
            
            # Create and return URL report
            return URLReport(
                url_id=url_report_data["url_id"],
                url=url_report_data["url"],
                category=URLCategory(url_report_data["category"]),
                rule_matches=rule_matches,
                ai_analysis=ai_analysis,
                created_at=datetime.fromisoformat(url_report_data["created_at"])
            )
        except Exception as e:
            logger.error(f"Error in get_url_report_by_url_id: {e}", exc_info=True)
            return None

    async def update_report(self, report: ComplianceReport) -> None:
        """Update a compliance report in the database."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._update_report, report)
        except Exception as e:
            logger.error(f"Error in update_report: {e}", exc_info=True)
            raise

    def _update_report(self, report: ComplianceReport) -> None:
        """Synchronous implementation of update_report."""
        query = """
        UPDATE compliance_reports
        SET
            status = ?,
            blacklist_count = ?,
            whitelist_count = ?,
            review_count = ?,
            total_urls = ?,
            processed_urls = ?,
            updated_at = ?
        WHERE id = ?
        """
        params = (
            report.status.value,
            report.blacklist_count,
            report.whitelist_count,
            report.review_count,
            report.total_urls,
            report.processed_urls,
            report.updated_at.isoformat(),
            report.id
        )
        self._execute_query(query, params)


# Singleton instance
database_service = DatabaseService() 