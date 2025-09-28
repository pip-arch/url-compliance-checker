"""
Service for error handling and categorization.
Includes domain circuit breaker pattern implementation to prevent repeated failures.
"""
import os
import re
import json
import logging
import time
import sqlite3
from pathlib import Path
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from app.models.url import ErrorCategory, CircuitBreakerStatus, DomainCircuitBreaker
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
DATA_DIR = os.getenv("DATA_DIR", "./data")
CIRCUIT_BREAKER_DB = os.getenv("CIRCUIT_BREAKER_DB", "circuit_breakers.db")
FAILURE_THRESHOLD = int(os.getenv("DOMAIN_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "3600"))  # 1 hour
DEFAULT_MAX_RETRIES = int(os.getenv("DEFAULT_MAX_RETRIES", "3"))

# Maximum number of retries by error category
RETRY_CONFIG = {
    ErrorCategory.CONNECTION_ERROR: 3,
    ErrorCategory.DNS_ERROR: 2,
    ErrorCategory.SSL_ERROR: 1,
    ErrorCategory.TIMEOUT: 3,
    ErrorCategory.SERVER_ERROR: 3,
    ErrorCategory.CLIENT_ERROR: 1,
    ErrorCategory.REDIRECT_ERROR: 1,
    ErrorCategory.CONTENT_EMPTY: 1,
    ErrorCategory.CONTENT_TOO_LARGE: 0,  # Don't retry content too large
    ErrorCategory.PARSING_ERROR: 1,
    ErrorCategory.MEMORY_ERROR: 0,  # Don't retry memory errors
    ErrorCategory.CPU_ERROR: 0,     # Don't retry CPU errors
    ErrorCategory.API_ERROR: 2,
    ErrorCategory.API_QUOTA_EXCEEDED: 0,  # Don't retry quota errors
    ErrorCategory.RATE_LIMITED: 3,
    ErrorCategory.UNKNOWN: 1
}

# Error pattern matching for categorization
ERROR_PATTERNS = [
    # Network errors
    (r"connection.*refused|connection.*error|failed to establish connection", ErrorCategory.CONNECTION_ERROR),
    (r"name.*not.*resolved|dns.*error|could not resolve host", ErrorCategory.DNS_ERROR),
    (r"ssl.*error|certificate.*error|ssl handshake", ErrorCategory.SSL_ERROR),
    (r"timeout|timed out|deadline exceeded", ErrorCategory.TIMEOUT),
    
    # HTTP errors
    (r"500|502|503|504|internal server error", ErrorCategory.SERVER_ERROR),
    (r"40[0-9]|client error|forbidden|not found|unauthorized", ErrorCategory.CLIENT_ERROR),
    (r"too many redirects|redirect.*loop|maximum.*redirects", ErrorCategory.REDIRECT_ERROR),
    
    # Content errors
    (r"no.*content|empty.*response|content.*empty", ErrorCategory.CONTENT_EMPTY),
    (r"content.*too.*large|response.*too.*big|payload.*too.*large", ErrorCategory.CONTENT_TOO_LARGE),
    (r"parsing.*error|invalid.*html|malformed", ErrorCategory.PARSING_ERROR),
    
    # Resource errors
    (r"memory.*error|out.*of.*memory|allocation.*failed", ErrorCategory.MEMORY_ERROR),
    (r"cpu.*limit|processor.*overload", ErrorCategory.CPU_ERROR),
    
    # API errors
    (r"api.*error|api.*exception", ErrorCategory.API_ERROR),
    (r"quota.*exceeded|usage.*limit|too many requests", ErrorCategory.API_QUOTA_EXCEEDED),
    
    # Rate limiting
    (r"rate.*limit|throttl|429", ErrorCategory.RATE_LIMITED),
]

class ErrorHandlerService:
    """
    Service for error handling:
    1. Categorize errors for better handling
    2. Implement circuit breaker pattern for domains with repeated failures
    3. Provide retry recommendation based on error category
    4. Track error statistics
    """

    def __init__(self):
        """Initialize the error handler service."""
        # Ensure data directory exists
        self.data_dir = Path(DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
        
        # Database path
        self.db_path = self.data_dir / CIRCUIT_BREAKER_DB
        
        # Initialize database
        self._init_db()
        
        # In-memory cache of open circuit breakers
        self.open_circuit_breakers: Set[str] = set()
        # Last check time for circuit breakers
        self.last_circuit_breaker_refresh = datetime.now()
        
        # Error statistics
        self.error_stats: Dict[str, int] = {}
        
        logger.info(f"ErrorHandlerService initialized with database at: {self.db_path}")
        logger.info(f"Circuit breaker threshold: {FAILURE_THRESHOLD} failures")
        logger.info(f"Circuit breaker timeout: {CIRCUIT_BREAKER_TIMEOUT} seconds")

    def _init_db(self):
        """Initialize the database with the required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create circuit breakers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS circuit_breakers (
                    domain TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    failure_count INTEGER DEFAULT 0,
                    failure_threshold INTEGER DEFAULT 5,
                    last_failure_time TEXT,
                    reset_timeout INTEGER DEFAULT 3600,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Create error statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_stats (
                    category TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    last_occurrence TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Error handler database initialized")
        except Exception as e:
            logger.error(f"Error initializing error handler database: {str(e)}")
            raise

    def categorize_error(self, error_message: str) -> ErrorCategory:
        """
        Categorize an error based on pattern matching.
        
        Args:
            error_message: The error message to categorize
            
        Returns:
            ErrorCategory: The categorized error
        """
        if not error_message:
            return ErrorCategory.UNKNOWN
        
        # Convert to lowercase for case-insensitive matching
        error_lower = error_message.lower()
        
        # Check each pattern
        for pattern, category in ERROR_PATTERNS:
            if re.search(pattern, error_lower):
                # Update error statistics
                self._update_error_stats(category)
                return category
        
        # If no pattern matches, return UNKNOWN
        self._update_error_stats(ErrorCategory.UNKNOWN)
        return ErrorCategory.UNKNOWN

    def should_retry(self, error_category: ErrorCategory, retry_count: int) -> bool:
        """
        Determine if a request should be retried based on error category and retry count.
        
        Args:
            error_category: The categorized error
            retry_count: Number of retries already attempted
            
        Returns:
            bool: True if the request should be retried
        """
        max_retries = RETRY_CONFIG.get(error_category, DEFAULT_MAX_RETRIES)
        return retry_count < max_retries

    def circuit_breaker_check(self, domain: str) -> bool:
        """
        Check if a domain should be allowed through the circuit breaker.
        
        Args:
            domain: The domain to check
            
        Returns:
            bool: True if the request should be allowed, False if blocked
        """
        # Refresh circuit breaker cache if needed
        self._refresh_circuit_breakers()
        
        # Normalize domain (remove www prefix)
        normalized_domain = self._normalize_domain(domain)
        
        # Check if domain is in circuit breaker list
        if normalized_domain in self.open_circuit_breakers:
            logger.warning(f"Circuit breaker open for domain: {domain}")
            return False
        
        return True

    def record_failure(self, url: str, error: str) -> bool:
        """
        Record a failure for a domain and update circuit breaker if needed.
        
        Args:
            url: The URL that failed
            error: The error message
            
        Returns:
            bool: True if the circuit breaker was triggered (opened)
        """
        # Extract and normalize domain
        domain = self._get_domain_from_url(url)
        if not domain:
            return False
        
        try:
            # Get current circuit breaker status
            circuit_breaker = self._get_circuit_breaker(domain)
            
            # Create new circuit breaker if it doesn't exist
            if not circuit_breaker:
                circuit_breaker = DomainCircuitBreaker(
                    domain=domain,
                    status=CircuitBreakerStatus.CLOSED,
                    failure_count=0,
                    failure_threshold=FAILURE_THRESHOLD,
                    reset_timeout=CIRCUIT_BREAKER_TIMEOUT,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            
            # Increment failure count
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure_time = datetime.now()
            circuit_breaker.updated_at = datetime.now()
            
            # Check if threshold is reached
            circuit_breaker_triggered = False
            if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                circuit_breaker.status = CircuitBreakerStatus.OPEN
                self.open_circuit_breakers.add(domain)
                circuit_breaker_triggered = True
                logger.warning(f"Circuit breaker opened for domain {domain} after {circuit_breaker.failure_count} failures")
            
            # Save circuit breaker
            self._save_circuit_breaker(circuit_breaker)
            
            return circuit_breaker_triggered
        except Exception as e:
            logger.error(f"Error recording failure for domain {domain}: {str(e)}")
            return False

    def reset_circuit_breaker(self, domain: str) -> bool:
        """
        Reset circuit breaker for a domain.
        
        Args:
            domain: The domain to reset
            
        Returns:
            bool: True if the circuit breaker was reset
        """
        # Normalize domain
        domain = self._normalize_domain(domain)
        
        try:
            # Get current circuit breaker
            circuit_breaker = self._get_circuit_breaker(domain)
            if not circuit_breaker:
                return False
            
            # Reset circuit breaker
            circuit_breaker.status = CircuitBreakerStatus.CLOSED
            circuit_breaker.failure_count = 0
            circuit_breaker.updated_at = datetime.now()
            
            # Save circuit breaker
            self._save_circuit_breaker(circuit_breaker)
            
            # Remove from in-memory cache
            if domain in self.open_circuit_breakers:
                self.open_circuit_breakers.remove(domain)
                
            logger.info(f"Circuit breaker reset for domain: {domain}")
            return True
        except Exception as e:
            logger.error(f"Error resetting circuit breaker for domain {domain}: {str(e)}")
            return False

    def _refresh_circuit_breakers(self):
        """Refresh the in-memory cache of open circuit breakers."""
        # Only refresh once per minute
        now = datetime.now()
        if (now - self.last_circuit_breaker_refresh).total_seconds() < 60:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all open circuit breakers
            cursor.execute(
                "SELECT domain, last_failure_time, reset_timeout FROM circuit_breakers WHERE status = ?",
                (CircuitBreakerStatus.OPEN.value,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            # Reset in-memory cache
            self.open_circuit_breakers = set()
            
            # Check each open circuit breaker
            for row in rows:
                domain = row["domain"]
                last_failure_time = datetime.fromisoformat(row["last_failure_time"]) if row["last_failure_time"] else None
                reset_timeout = row["reset_timeout"]
                
                # Check if circuit breaker should be automatically reset
                if last_failure_time and (now - last_failure_time).total_seconds() > reset_timeout:
                    logger.info(f"Auto-resetting circuit breaker for domain {domain}")
                    self.reset_circuit_breaker(domain)
                else:
                    self.open_circuit_breakers.add(domain)
            
            logger.debug(f"Refreshed circuit breakers, {len(self.open_circuit_breakers)} domains are blocked")
            self.last_circuit_breaker_refresh = now
        except Exception as e:
            logger.error(f"Error refreshing circuit breakers: {str(e)}")

    def _get_circuit_breaker(self, domain: str) -> Optional[DomainCircuitBreaker]:
        """Get circuit breaker for a domain."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM circuit_breakers WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
                
            return DomainCircuitBreaker(
                domain=row["domain"],
                status=CircuitBreakerStatus(row["status"]),
                failure_count=row["failure_count"],
                failure_threshold=row["failure_threshold"],
                last_failure_time=datetime.fromisoformat(row["last_failure_time"]) if row["last_failure_time"] else None,
                reset_timeout=row["reset_timeout"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            )
        except Exception as e:
            logger.error(f"Error getting circuit breaker for domain {domain}: {str(e)}")
            return None

    def _save_circuit_breaker(self, circuit_breaker: DomainCircuitBreaker) -> bool:
        """Save circuit breaker to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if circuit breaker already exists
            cursor.execute("SELECT domain FROM circuit_breakers WHERE domain = ?", (circuit_breaker.domain,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing circuit breaker
                cursor.execute(
                    "UPDATE circuit_breakers SET status = ?, failure_count = ?, failure_threshold = ?, last_failure_time = ?, reset_timeout = ?, updated_at = ? WHERE domain = ?",
                    (
                        circuit_breaker.status.value,
                        circuit_breaker.failure_count,
                        circuit_breaker.failure_threshold,
                        circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
                        circuit_breaker.reset_timeout,
                        datetime.now().isoformat(),
                        circuit_breaker.domain
                    )
                )
            else:
                # Insert new circuit breaker
                cursor.execute(
                    "INSERT INTO circuit_breakers (domain, status, failure_count, failure_threshold, last_failure_time, reset_timeout, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        circuit_breaker.domain,
                        circuit_breaker.status.value,
                        circuit_breaker.failure_count,
                        circuit_breaker.failure_threshold,
                        circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
                        circuit_breaker.reset_timeout,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Error saving circuit breaker for domain {circuit_breaker.domain}: {str(e)}")
            return False

    def _update_error_stats(self, category: ErrorCategory):
        """Update error statistics."""
        category_value = category.value
        
        # Update in-memory stats
        if category_value in self.error_stats:
            self.error_stats[category_value] += 1
        else:
            self.error_stats[category_value] = 1
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if category exists
            cursor.execute("SELECT category FROM error_stats WHERE category = ?", (category_value,))
            existing = cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if existing:
                # Update existing category
                cursor.execute(
                    "UPDATE error_stats SET count = count + 1, last_occurrence = ? WHERE category = ?",
                    (now, category_value)
                )
            else:
                # Insert new category
                cursor.execute(
                    "INSERT INTO error_stats (category, count, last_occurrence) VALUES (?, ?, ?)",
                    (category_value, 1, now)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating error stats for category {category_value}: {str(e)}")

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT category, count, last_occurrence FROM error_stats ORDER BY count DESC")
            rows = cursor.fetchall()
            
            stats = {
                "categories": {},
                "total_errors": 0
            }
            
            for row in rows:
                category = row["category"]
                count = row["count"]
                last_occurrence = row["last_occurrence"]
                
                stats["categories"][category] = {
                    "count": count,
                    "last_occurrence": last_occurrence
                }
                
                stats["total_errors"] += count
            
            cursor.execute("SELECT COUNT(*) as count FROM circuit_breakers WHERE status = ?", (CircuitBreakerStatus.OPEN.value,))
            open_count = cursor.fetchone()["count"]
            stats["open_circuit_breakers"] = open_count
            
            conn.close()
            
            return stats
        except Exception as e:
            logger.error(f"Error getting error stats: {str(e)}")
            return {"categories": {}, "total_errors": 0, "open_circuit_breakers": 0}

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL and normalize it."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return self._normalize_domain(domain)
        except:
            return ""

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain by removing www prefix."""
        if domain.startswith("www."):
            return domain[4:]
        return domain

# Create a singleton instance
error_handler = ErrorHandlerService() 