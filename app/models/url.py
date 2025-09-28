from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class URLStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FILTERED = "filtered"
    RETRY = "retry"


class URLFilterReason(str, Enum):
    OWN_DOMAIN = "own_domain"
    REGULATOR = "regulator"
    NO_MENTION = "no_mention"
    INVALID_URL = "invalid_url"
    RESOURCE_LIMIT = "resource_limit"
    BLOCKED = "blocked"
    BLACKLISTED = "blacklisted"
    OTHER = "other"


class ErrorCategory(str, Enum):
    """Categorization of errors for better handling and retry strategies."""
    # Network errors
    CONNECTION_ERROR = "connection_error"  # Connection refused, timeout, etc.
    DNS_ERROR = "dns_error"  # DNS resolution failed
    SSL_ERROR = "ssl_error"  # SSL certificate errors
    TIMEOUT = "timeout"  # Request timed out
    
    # HTTP status errors
    SERVER_ERROR = "server_error"  # 5xx status codes
    CLIENT_ERROR = "client_error"  # 4xx status codes
    REDIRECT_ERROR = "redirect_error"  # Too many redirects or redirect loop
    
    # Content errors
    CONTENT_EMPTY = "content_empty"  # No content found
    CONTENT_TOO_LARGE = "content_too_large"  # Content too large to process
    PARSING_ERROR = "parsing_error"  # Error parsing content
    
    # Resource errors
    MEMORY_ERROR = "memory_error"  # Out of memory
    CPU_ERROR = "cpu_error"  # CPU overloaded
    
    # API errors
    API_ERROR = "api_error"  # Error from external API
    API_QUOTA_EXCEEDED = "api_quota_exceeded"  # API quota exceeded
    
    # Rate limiting
    RATE_LIMITED = "rate_limited"  # Rate limited by target server
    
    # Other
    UNKNOWN = "unknown"  # Unknown error


class CircuitBreakerStatus(str, Enum):
    """Status of domain circuit breaker for preventing repeated failures."""
    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Circuit breaker triggered, no requests allowed
    HALF_OPEN = "half_open"  # Testing if requests can be allowed again


class URLContentMatch(BaseModel):
    """Match of keywords in URL content."""
    text: str
    position: int
    context_before: str
    context_after: str
    embedding_id: Optional[str] = None


class URLContent(BaseModel):
    """Content extracted from a URL."""
    url: str
    title: Optional[str] = None
    full_text: Optional[str] = None
    crawled_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}
    mentions: List[URLContentMatch] = []


class URL(BaseModel):
    """Single URL record."""
    id: str
    url: str
    batch_id: str
    status: URLStatus = URLStatus.PENDING
    filter_reason: Optional[URLFilterReason] = None
    error_category: Optional[ErrorCategory] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    content: Optional[URLContent] = None
    error: Optional[str] = None
    domain: Optional[str] = None


class URLBatch(BaseModel):
    """Batch of URLs uploaded for processing."""
    id: str
    description: Optional[str] = None
    filename: Optional[str] = None
    url_count: int
    processed_count: int = 0
    status: URLStatus = URLStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class URLBatchCreate(BaseModel):
    """Request model for creating a URL batch."""
    description: Optional[str] = None
    urls: List[str]


class URLBatchResponse(BaseModel):
    """Response model for URL batch operations."""
    batch_id: str
    message: str
    status: URLStatus


class DomainCircuitBreaker(BaseModel):
    """Circuit breaker for domains with repeated failures."""
    domain: str
    status: CircuitBreakerStatus = CircuitBreakerStatus.CLOSED
    failure_count: int = 0
    failure_threshold: int = 5
    last_failure_time: Optional[datetime] = None
    reset_timeout: int = 3600  # seconds (1 hour)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now) 