from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime


class ReportStatus(str, Enum):
    """Status of a compliance report."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PAUSED = "paused"  # When processing is paused due to exceeding fallback threshold
    FAILED = "failed"


class URLCategory(str, Enum):
    """Category of a URL after compliance analysis."""
    BLACKLIST = "blacklist"
    WHITELIST = "whitelist"
    REVIEW = "review"
    UNKNOWN = "unknown"


class ComplianceRuleMatch(BaseModel):
    """Match of a compliance rule in URL content."""
    rule_id: str
    rule_name: str
    rule_description: Optional[str] = None
    severity: str
    match_text: str
    context: str
    confidence: float = 1.0
    match_position: int
    context_before: str = ""
    context_after: str = ""


class AIAnalysisResult(BaseModel):
    """Result of AI analysis for a URL."""
    model: str
    category: URLCategory
    confidence: float
    explanation: str
    compliance_issues: List[Union[str, Dict[str, Any]]] = []
    raw_response: Optional[Dict[str, Any]] = None


class URLReport(BaseModel):
    """Report for a single URL after compliance analysis."""
    url_id: str
    url: str
    category: URLCategory
    rule_matches: List[ComplianceRuleMatch] = []
    ai_analysis: Optional[AIAnalysisResult] = None
    blacklist_info: Optional[Dict[str, Any]] = None
    analysis_method: str = "real_llm"  # "real_llm" or "fallback"
    created_at: datetime = Field(default_factory=datetime.now)


class ComplianceReport(BaseModel):
    """Overall compliance report for a batch of URLs."""
    id: str
    batch_id: str
    status: ReportStatus = ReportStatus.PENDING
    blacklist_count: int = 0
    whitelist_count: int = 0
    review_count: int = 0
    total_urls: int
    processed_urls: int = 0
    url_reports: List[URLReport] = []
    real_llm_count: int = 0
    openai_count: int = 0
    fallback_count: int = 0
    analysis_stats: Dict[str, Any] = Field(default_factory=lambda: {
        "real_llm": 0, 
        "fallback": 0, 
        "real_llm_percentage": 0.0,
        "fallback_percentage": 0.0
    })
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReportSummary(BaseModel):
    """Summary of a compliance report."""
    id: str
    batch_id: str
    status: ReportStatus
    blacklist_count: int
    whitelist_count: int
    review_count: int
    total_urls: int
    processed_urls: int
    created_at: datetime
    updated_at: datetime


class ReportCreate(BaseModel):
    """Request model for creating a compliance report."""
    batch_id: str


class ReportResponse(BaseModel):
    """Response model for report operations."""
    report_id: str
    message: str
    status: ReportStatus 