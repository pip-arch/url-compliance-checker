import os
import logging
import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from urllib.parse import urlparse

# Import services
from app.services.ai import ai_service
from app.services.openai_service import openai_service
from app.services.database import database_service
from app.services.vector_db import pinecone_service
from app.models.url import URL, URLContent, URLContentMatch, URLStatus
from app.models.report import (
    URLCategory, URLReport, ComplianceReport, ReportStatus,
    ComplianceRuleMatch, AIAnalysisResult
)
from app.core.blacklist_manager import blacklist_manager
from app.core.blacklist_keywords import blacklist_keywords
from app.services.enrichment import enrichment_service
from app.services.domain_analyzer import domain_analyzer
from app.services.pattern_detector import pattern_detector
from app.services.quality_assurance import qa_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blacklist threshold configurations
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))  # Confidence threshold for AI results
MIN_RULE_MATCHES = int(os.getenv("MIN_RULE_MATCHES_FOR_BLACKLIST", "1"))  # Just one rule match is enough

# Fallback threshold - allow processing as long as at least 75% uses real LLM
FALLBACK_THRESHOLD = float(os.getenv("FALLBACK_THRESHOLD", "0.75"))  # Increased from 0.5 to 0.75 (75% fallbacks allowed)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # Maximum number of retries for API calls


class RuleSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisMethod(str, Enum):
    """Methods used for URL compliance analysis."""
    REAL_LLM = "real_llm"  # Using OpenRouter LLM
    OPENAI = "openai"      # Using OpenAI as first fallback
    FALLBACK = "fallback"  # Using blacklist keywords fallback


class ComplianceRule:
    """
    A rule for checking compliance in URL content.
    """
    def __init__(
        self,
        id: str,
        name: str,
        pattern: str,
        description: str = "",
        severity: RuleSeverity = RuleSeverity.MEDIUM
    ):
        self.id = id
        self.name = name
        self.pattern = pattern
        self.description = description
        self.severity = severity
        self.regex = re.compile(pattern, re.IGNORECASE)
    
    def check(self, text: str) -> List[Dict[str, Any]]:
        """
        Check if the rule matches the text.
        """
        matches = []
        for match in self.regex.finditer(text):
            start_pos = match.start()
            end_pos = match.end()
            
            # Get context around match (50 characters before and after)
            context_start = max(0, start_pos - 50)
            context_end = min(len(text), end_pos + 50)
            
            context = text[context_start:context_end]
            matched_text = text[start_pos:end_pos]
            
            matches.append({
                "rule_id": self.id,
                "rule_name": self.name,
                "rule_description": self.description,
                "severity": self.severity,
                "match_text": matched_text,
                "context": context,
            })
        
        return matches


class ComplianceChecker:
    """
    Main class for checking compliance in URL content:
    1. Apply predefined compliance rules
    2. Use AI analysis for context evaluation (with fallback when needed)
    3. Categorize URLs as blacklist, whitelist, or review
    4. Automatically update blacklist for non-compliant domains
    """
    
    def __init__(self):
        """Initialize compliance checker with services."""
        self.ai_service = ai_service
        self.openai_service = openai_service
        self.db = database_service
        self.vector_db = pinecone_service
        self.blacklist_manager = blacklist_manager
        self.blacklist_keywords = blacklist_keywords
        
        # Load compliance rules
        self.rules = self._load_rules()
        logger.info(f"Compliance checker initialized with {len(self.rules)} rules")
        
        # Track analysis methods used
        self.analysis_stats = {
            "total": 0,
            "real_llm": 0,
            "openai": 0,
            "fallback": 0,
            "blacklisted": 0,
            "whitelisted": 0,
            "review": 0
        }
        
        # Batch-specific tracking
        self.current_batch_stats = {}
    
    def _load_rules(self) -> List[ComplianceRule]:
        """
        Load compliance rules from a predefined set.
        Later this can be loaded from a database or configuration file.
        """
        rules = [
            ComplianceRule(
                id="MISLEADING_INFO",
                name="Misleading Information",
                pattern=r"(guaranteed profit|100% success|risk[-\s]free trading|no loss|always profitable|never lose|certain return)",
                description="Claims that suggest guaranteed profits or risk-free trading",
                severity=RuleSeverity.HIGH
            ),
            ComplianceRule(
                id="UNAUTHORIZED_OFFER",
                name="Unauthorized Offer",
                pattern=r"(special offer|exclusive bonus|deposit bonus|trading bonus|free money|promotion code|special deal)",
                description="Unauthorized offers or bonuses that may violate regulations",
                severity=RuleSeverity.MEDIUM
            ),
            ComplianceRule(
                id="FALSE_REPRESENTATION",
                name="False Representation",
                pattern=r"(official partner|endorsed by|approved by|regulated by|certified by|authorized dealer|official broker)",
                description="False claims about partnerships or regulatory approval",
                severity=RuleSeverity.HIGH
            ),
            ComplianceRule(
                id="REGULATORY_ISSUES",
                name="Regulatory Issues",
                pattern=r"(unregulated|offshore|tax[-\s]free|evade taxes|circumvent regulations|bypass restrictions|avoid compliance)",
                description="Content suggesting regulatory evasion or non-compliance",
                severity=RuleSeverity.CRITICAL
            ),
            ComplianceRule(
                id="INAPPROPRIATE_MARKETING",
                name="Inappropriate Marketing",
                pattern=r"(get rich|quick money|easy money|fast cash|overnight success|become millionaire|trading secrets)",
                description="Inappropriate marketing tactics",
                severity=RuleSeverity.MEDIUM
            ),
            # New Financial Services Specific Rules
            ComplianceRule(
                id="INVESTMENT_GUARANTEES",
                name="Investment Guarantees",
                pattern=r"(guaranteed investment|secure investment|risk-free investment|safe haven|assured returns|protected capital)",
                description="Claims about guaranteed investment returns or safety",
                severity=RuleSeverity.HIGH
            ),
            ComplianceRule(
                id="LEVERAGE_MISREPRESENTATION",
                name="Leverage Misrepresentation",
                pattern=r"(unlimited leverage|no margin call|no stop out|trade without limits|infinite margin)",
                description="Misrepresentation of leverage or margin trading conditions",
                severity=RuleSeverity.HIGH
            ),
            ComplianceRule(
                id="UNREALISTIC_RETURNS",
                name="Unrealistic Returns",
                pattern=r"(\d{2,}% (per|a) (day|week|month)|double your money|triple your investment|1000% profit|exponential growth)",
                description="Claims about unrealistic investment returns",
                severity=RuleSeverity.HIGH
            ),
            ComplianceRule(
                id="REGULATED_PRODUCTS_MISUSE",
                name="Regulated Products Misuse",
                pattern=r"(no KYC|anonymous trading|hidden accounts|secret trading|bypass verification)",
                description="Suggestions of bypassing regulations for trading",
                severity=RuleSeverity.CRITICAL
            ),
            ComplianceRule(
                id="NO_RISK_DISCLOSURE",
                name="No Risk Disclosure",
                pattern=r"(no risk disclosure|hidden fees|undisclosed commissions|secret costs|hidden charges)",
                description="Lack of proper risk disclosure or hidden fees",
                severity=RuleSeverity.HIGH
            ),
        ]
        return rules
    
    async def check_url_compliance(self, url_content: URLContent, batch_id: Optional[str] = None) -> URLReport:
        """
        Check URL compliance using rules and AI analysis.
        Now includes enrichment, pattern detection, and domain tracking.
        """
        logger.info(f"Checking compliance for URL: {url_content.url}")
        
        # Check for pattern violations first
        detected_patterns = await pattern_detector.detect_patterns(url_content.full_text)
        if detected_patterns:
            logger.info(f"Detected {len(detected_patterns)} violation patterns in {url_content.url}")
        
        # Check rule-based compliance
        rule_matches = self._check_rules(url_content)
        
        # Perform AI analysis
        ai_result = await self._analyze_with_ai(url_content, batch_id)
        
        # Determine category based on rule matches and AI analysis
        category = self._determine_category(rule_matches, ai_result)
        
        # Log final categorization decision
        logger.info("-"*80)
        logger.info(f"📊 FINAL CATEGORIZATION for URL: {url_content.url}")
        logger.info(f"   Category: {category.value}")
        logger.info(f"   Analysis Method: {self.current_batch_stats.get(batch_id, {}).get('last_method', 'unknown')}")
        logger.info(f"   Rule Matches: {len(rule_matches)}")
        if rule_matches:
            for match in rule_matches[:3]:  # Show first 3 rule matches
                logger.info(f"     - {match.rule_name}: {match.match_text[:50]}...")
        logger.info(f"   AI Result: {'Available' if ai_result else 'None'}")
        if ai_result:
            logger.info(f"   AI Confidence: {ai_result.confidence:.2f}")
            logger.info(f"   AI Explanation: {ai_result.explanation[:100]}...")
        logger.info("-"*80)
        
        # Track domain violations
        confidence = ai_result.confidence if ai_result else 0.5
        await domain_analyzer.track_url_result(url_content.url, category, confidence)
        
        # Learn from violations
        if category == URLCategory.BLACKLIST and ai_result:
            # Determine violation type from AI analysis
            violation_type = 'general_violation'
            if ai_result.compliance_issues:
                # Map compliance issues to violation types
                for issue in ai_result.compliance_issues:
                    issue_str = str(issue).lower()
                    if 'misleading' in issue_str:
                        violation_type = 'misleading_claim'
                        break
                    elif 'unauthorized' in issue_str:
                        violation_type = 'unauthorized_offer'
                        break
                    elif 'false' in issue_str:
                        violation_type = 'false_representation'
                        break
            
            await pattern_detector.learn_from_violation(
                url_content.full_text[:1000],  # First 1000 chars
                violation_type,
                confidence
            )
        
        # Check if QA is needed
        if await qa_service.should_recheck(url_content.url):
            # Schedule QA check (async, don't wait)
            asyncio.create_task(qa_service.perform_qa_check(
                url_content.url,
                category,
                confidence,
                self.current_batch_stats.get(batch_id, {}).get('last_method', 'unknown')
            ))
        
        # Get adjusted confidence from QA service
        if ai_result:
            ai_result.confidence = qa_service.get_confidence_adjustment(
                category.value,
                ai_result.confidence
            )
        
        # Create URL report
        report = URLReport(
            url_id=url_content.url,
            url=url_content.url,
            category=category,
            rule_matches=rule_matches,
            ai_analysis=ai_result,
            analysis_method=self.current_batch_stats.get(batch_id, {}).get('last_method', 'real_llm')
        )
        
        # Add pattern detection info to report if available
        if detected_patterns:
            if not report.ai_analysis:
                report.ai_analysis = AIAnalysisResult(
                    model="pattern_detector",
                    category=category,
                    confidence=detected_patterns[0]['confidence'],
                    explanation=f"Detected violation patterns: {', '.join(p['violation_type'] for p in detected_patterns[:3])}",
                    compliance_issues=[p['violation_type'] for p in detected_patterns]
                )
            else:
                # Add pattern info to existing AI analysis
                report.ai_analysis.compliance_issues.extend([
                    f"Pattern: {p['violation_type']}" for p in detected_patterns[:3]
                ])
        
        # Enrich URL data (async, don't wait for results)
        if category == URLCategory.BLACKLIST or category == URLCategory.REVIEW:
            asyncio.create_task(self._enrich_url_async(url_content.url, url_content.full_text))
        
        return report
    
    def _check_rules(self, url_content: URLContent) -> List[ComplianceRuleMatch]:
        """
        Check compliance for a URL content using predefined rules.
        """
        rule_matches = []
        for mention in url_content.mentions:
            full_context = mention.context_before + mention.text + mention.context_after
            
            for rule in self.rules:
                matches = rule.check(full_context)
                for match in matches:
                    rule_match = ComplianceRuleMatch(**match)
                    rule_matches.append(rule_match)
        
        return rule_matches
    
    async def _analyze_with_ai(self, url_content: URLContent, batch_id: Optional[str] = None) -> Optional[AIAnalysisResult]:
        """
        Perform AI analysis for a URL content.
        """
        # First check if URL is already blacklisted
        is_blacklisted, blacklist_info = await self.blacklist_manager.is_blacklisted(url_content.url)
        if is_blacklisted:
            logger.info(f"URL {url_content.url} is from a blacklisted domain. Skipping analysis.")
            return None
        
        if not url_content.mentions:
            # Skip URLs without content or mentions
            return None
        
        # Try to perform AI analysis with multiple fallback options
        batch_id = batch_id or "default"
        
        # Initialize batch stats if this is a new batch
        if batch_id not in self.current_batch_stats:
            self.current_batch_stats[batch_id] = {
                "total": 0,
                "real_llm": 0, 
                "openai": 0,
                "fallback": 0
            }
            
        # Increment total count for batch
        self.current_batch_stats[batch_id]["total"] += 1
        self.analysis_stats["total"] += 1
        
        # Decide whether to use real LLM or fallback based on current stats
        use_fallback = False
        
        # Only consider fallback if we've processed enough URLs in this batch to have meaningful stats
        if self.current_batch_stats[batch_id]["total"] > 10:
            # Calculate current fallback percentage for this batch
            if self.current_batch_stats[batch_id]["total"] > 0:
                current_fallback_pct = self.current_batch_stats[batch_id]["fallback"] / self.current_batch_stats[batch_id]["total"]
                
                # If fallback usage is approaching threshold, try to use real LLM
                if current_fallback_pct < FALLBACK_THRESHOLD:
                    use_fallback = False
                else:
                    # We're at/over threshold, check if processing should be paused
                    if current_fallback_pct > FALLBACK_THRESHOLD:
                        logger.warning(f"Fallback usage ({current_fallback_pct:.1%}) exceeds threshold ({FALLBACK_THRESHOLD:.1%}) for batch {batch_id}")
                        raise RuntimeError(f"Fallback threshold exceeded: {current_fallback_pct:.1%} > {FALLBACK_THRESHOLD:.1%}. Processing paused.")
        
        # Now try the appropriate analysis method
        analysis_method = AnalysisMethod.REAL_LLM
        ai_result = None
        
        try:
            if not use_fallback:
                # First try OpenRouter LLM analysis
                try:
                    ai_result = await self.ai_service.analyze_content(url_content)
                    # If we get here, OpenRouter LLM was successful
                    analysis_method = AnalysisMethod.REAL_LLM
                    self.current_batch_stats[batch_id]["real_llm"] += 1
                    self.analysis_stats["real_llm"] += 1
                    logger.info(f"✅ Successfully analyzed URL {url_content.url} using OpenRouter LLM")
                except Exception as e:
                    # OpenRouter failed, try OpenAI as second option
                    logger.warning(f"⚠️  OpenRouter LLM analysis failed for URL {url_content.url}: {str(e)}")
                    
                    # Try OpenAI
                    try:
                        logger.info(f"🔄 Trying OpenAI analysis for URL {url_content.url}")
                        ai_result = await self.openai_service.analyze_content(url_content)
                        # If we get here, OpenAI was successful
                        analysis_method = AnalysisMethod.OPENAI
                        self.current_batch_stats[batch_id]["openai"] += 1
                        self.analysis_stats["openai"] += 1
                        logger.info(f"✅ Successfully analyzed URL {url_content.url} using OpenAI")
                        
                        # Log OpenAI result
                        logger.info("="*80)
                        logger.info(f"🤖 OPENAI ANALYSIS RESULT for URL: {url_content.url}")
                        logger.info(f"   Category: {ai_result.category.value}")
                        logger.info(f"   Confidence: {ai_result.confidence:.2f}")
                        logger.info(f"   Explanation: {ai_result.explanation}")
                        if ai_result.compliance_issues:
                            logger.info(f"   Compliance Issues: {', '.join(str(issue) for issue in ai_result.compliance_issues)}")
                        else:
                            logger.info("   Compliance Issues: None found")
                        logger.info("="*80)
                    except Exception as openai_error:
                        # OpenAI failed, try keyword fallback as last resort
                        logger.warning(f"⚠️  OpenAI analysis also failed for URL {url_content.url}: {str(openai_error)}")
                        
                        # Check if using fallback would exceed threshold
                        if self.current_batch_stats[batch_id]["total"] > 0:
                            projected_fallback = (self.current_batch_stats[batch_id]["fallback"] + 1) / self.current_batch_stats[batch_id]["total"]
                            if projected_fallback > FALLBACK_THRESHOLD:
                                logger.warning(f"Fallback would exceed threshold ({projected_fallback:.1%} > {FALLBACK_THRESHOLD:.1%}), but continuing with fallback")
                                # We'll proceed with fallback analysis anyway since we'd rather classify with keywords than fail
                        
                        # Use keyword fallback as last resort
                        try:
                            ai_result = self.blacklist_keywords.analyze_content(url_content)
                            analysis_method = AnalysisMethod.FALLBACK
                            self.current_batch_stats[batch_id]["fallback"] += 1
                            self.analysis_stats["fallback"] += 1
                            self.ai_service.increment_fallback_count()
                            logger.info(f"📋 Used blacklist keywords fallback for URL {url_content.url}")
                            
                            # Log fallback result
                            logger.info("="*80)
                            logger.info(f"🔍 KEYWORD FALLBACK ANALYSIS RESULT for URL: {url_content.url}")
                            logger.info(f"   Category: {ai_result.category.value}")
                            logger.info(f"   Confidence: {ai_result.confidence:.2f}")
                            logger.info(f"   Explanation: {ai_result.explanation}")
                            if ai_result.compliance_issues:
                                logger.info(f"   Compliance Issues: {', '.join(str(issue) for issue in ai_result.compliance_issues)}")
                            else:
                                logger.info("   Compliance Issues: None found")
                            logger.info("="*80)
                        except Exception as fallback_error:
                            logger.error(f"Keyword fallback analysis also failed for URL {url_content.url}: {str(fallback_error)}")
                            # If all methods fail, return None for AI result
                            ai_result = None
                            analysis_method = AnalysisMethod.FALLBACK
                            raise RuntimeError(f"All analysis methods failed: OpenRouter: {str(e)}, OpenAI: {str(openai_error)}, Fallback: {str(fallback_error)}")
            else:
                # Direct fallback use case
                ai_result = self.blacklist_keywords.analyze_content(url_content)
                analysis_method = AnalysisMethod.FALLBACK
                self.current_batch_stats[batch_id]["fallback"] += 1
                self.analysis_stats["fallback"] += 1
                self.ai_service.increment_fallback_count()
                logger.info(f"Used blacklist keywords fallback for URL {url_content.url} (direct fallback)")
                
        except Exception as e:
            logger.error(f"All analysis methods failed for URL {url_content.url}: {str(e)}")
            # If all methods fail, use rule-based categorization only
            ai_result = None
        
        return ai_result
    
    def _determine_category(
        self, 
        rule_matches: List[ComplianceRuleMatch], 
        ai_result: Optional[AIAnalysisResult]
    ) -> URLCategory:
        """
        Determine the final category for a URL based on rule matches and AI analysis.
        
        The algorithm is:
        1. If high-priority rule matches, always blacklist
        2. If AI suggests blacklist, always blacklist
        3. If there are rule matches and no AI analysis or AI is uncertain, blacklist
        4. If AI suggests whitelist and no rule matches, whitelist
        5. Otherwise, mark for review
        """
        # Check for high-priority rules (BLACKLIST regardless of AI analysis)
        high_priority_matches = [match for match in rule_matches if match.rule_id.startswith("HIGH")]
        if high_priority_matches:
            logger.info(f"Blacklisting URL due to high-priority rule match: {high_priority_matches[0].rule_id}")
            return URLCategory.BLACKLIST
            
        # Check for regular rule matches (still important, but consider AI analysis too)
        if rule_matches:
            # If no AI analysis is available, blacklist based on rules
            if not ai_result:
                logger.info(f"Blacklisting URL due to rule matches without AI analysis")
                return URLCategory.BLACKLIST
                
        # CONSIDER AI ANALYSIS IF AVAILABLE
        if ai_result:
            # Any AI result suggesting blacklist should be blacklisted regardless of confidence
            if ai_result.category == URLCategory.BLACKLIST:
                return URLCategory.BLACKLIST
                
            # If AI suggests review but has identified compliance issues, blacklist it
            if ai_result.category == URLCategory.REVIEW and ai_result.compliance_issues:
                return URLCategory.BLACKLIST
            
            # Check for negative reviews in the explanation or content
            explanation = ai_result.explanation.lower() if ai_result.explanation else ""
            
            negative_keywords = [
                "negative review", "scam", "terrible", "awful", "poor service", 
                "unreliable", "bad experience", "not recommended", "avoid",
                "recommend against", "negative opinion", "complaint", "dissatisfied",
                "poor customer service", "bad reviews", "critical review"
            ]
            
            # Look for negative keywords in the explanation
            if any(keyword in explanation for keyword in negative_keywords):
                logger.info(f"Blacklisting URL due to negative review: found negative keywords in explanation")
                return URLCategory.BLACKLIST
            
            # Also check compliance issues for negative sentiment
            for issue in ai_result.compliance_issues:
                # Handle both string and dictionary formats for compliance issues
                issue_text = ""
                if isinstance(issue, str):
                    issue_text = issue.lower()
                elif isinstance(issue, dict):
                    # Extract text from dictionary - common keys like "issue", "text", "description"
                    for key in ["issue", "text", "description", "reason"]:
                        if key in issue and isinstance(issue[key], str):
                            issue_text += issue[key].lower() + " "
                    issue_text = issue_text.strip()
                
                if issue_text and any(keyword in issue_text for keyword in negative_keywords):
                    logger.info(f"Blacklisting URL due to negative review: found negative keywords in compliance issues")
                    return URLCategory.BLACKLIST
                
            # Only whitelist if AI explicitly says it's safe and there are no rule matches
            if ai_result.category == URLCategory.WHITELIST and not rule_matches:
                return URLCategory.WHITELIST
                
        # By default, if we have any rule matches at all, blacklist the URL (conservative)
        if rule_matches:
            logger.info(f"Blacklisting URL due to rule matches with inconclusive AI analysis")
            return URLCategory.BLACKLIST
            
        # If we get here and have AI analysis, use its category (likely REVIEW)
        if ai_result:
            return ai_result.category
        
        # If we get here, we have no rule matches and no AI analysis, so mark for review
        return URLCategory.REVIEW
    
    async def generate_report(self, urls: List[URL], batch_id: str) -> ComplianceReport:
        """
        Generate a compliance report for a batch of URLs.
        """
        logger.info(f"Generating compliance report for batch {batch_id}")
        
        # Initialize report
        report = ComplianceReport(
            id=f"report-{batch_id}",
            batch_id=batch_id,
            status=ReportStatus.PROCESSING,
            total_urls=len(urls),
            processed_urls=0,
            url_reports=[]
        )
        
        # Process each URL
        for url in urls:
            try:
                # Check if URL is already classified
                if url.status != URLStatus.PROCESSED or not hasattr(url, "content") or not url.content:
                    continue
                
                # Process URL content
                url_report = await self.check_url_compliance(url.content, batch_id)
                
                # Add URL report to the compliance report
                report.url_reports.append(url_report)
                report.processed_urls += 1
                
                # Update statistics based on category
                if url_report.category == URLCategory.BLACKLIST:
                    report.blacklist_count += 1
                elif url_report.category == URLCategory.WHITELIST:
                    report.whitelist_count += 1
                elif url_report.category == URLCategory.REVIEW:
                    report.review_count += 1
                
                # Update analysis method stats
                analysis_method = url_report.analysis_method
                if analysis_method == "real_llm":
                    report.real_llm_count += 1
                elif analysis_method == "openai":
                    report.openai_count += 1
                elif analysis_method == "fallback":
                    report.fallback_count += 1
                
                # Log batch analysis progress
                if report.processed_urls % 10 == 0 or report.processed_urls == len(urls):
                    logger.info(f"Batch {batch_id} analysis stats: "
                               f"{report.real_llm_count}/{report.processed_urls} real LLM "
                               f"({report.real_llm_count/report.processed_urls*100:.1f}%), "
                               f"{report.openai_count}/{report.processed_urls} OpenAI "
                               f"({report.openai_count/report.processed_urls*100:.1f}%), "
                               f"{report.fallback_count}/{report.processed_urls} fallback "
                               f"({report.fallback_count/report.processed_urls*100:.1f}%)")
            except Exception as e:
                logger.error(f"Error processing URL {url.url}: {str(e)}")
                # Continue processing other URLs
                continue
        
        # Update report status
        report.status = ReportStatus.COMPLETED
        
        # Log summary
        logger.info(f"Compliance report {report.id} stats: "
                   f"{report.blacklist_count} blacklisted, "
                   f"{report.whitelist_count} whitelisted, "
                   f"{report.review_count} for review | "
                   f"Analysis methods: {report.real_llm_count} real LLM "
                   f"({report.real_llm_count/report.processed_urls*100:.1f}%), "
                   f"{report.openai_count} OpenAI "
                   f"({report.openai_count/report.processed_urls*100:.1f}%), "
                   f"{report.fallback_count} fallback "
                   f"({report.fallback_count/report.processed_urls*100:.1f}%)")
        
        # Export blacklist - disabled to prevent creating too many files
        # await self.blacklist_manager.export_blacklist("csv")
        # await self.blacklist_manager.export_blacklist("txt")
        # await self.blacklist_manager.export_blacklist("json")
        
        return report
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get overall analysis statistics."""
        total = self.analysis_stats["total"]
        real_pct = (self.analysis_stats["real_llm"] / total * 100) if total > 0 else 0
        openai_pct = (self.analysis_stats["openai"] / total * 100) if total > 0 else 0
        fallback_pct = (self.analysis_stats["fallback"] / total * 100) if total > 0 else 0
        
        return {
            "total_analyzed": total,
            "real_llm": self.analysis_stats["real_llm"],
            "openai": self.analysis_stats["openai"],
            "fallback": self.analysis_stats["fallback"],
            "real_llm_percentage": real_pct,
            "openai_percentage": openai_pct,
            "fallback_percentage": fallback_pct,
            "blacklisted": self.analysis_stats["blacklisted"],
            "whitelisted": self.analysis_stats["whitelisted"],
            "review": self.analysis_stats["review"],
            "batch_stats": self.current_batch_stats
        }
    
    async def _enrich_url_async(self, url: str, content: str):
        """Asynchronously enrich URL data."""
        try:
            enrichment_data = await enrichment_service.enrich_url(url, content)
            
            # Save enrichment data
            enrichment_file = f"data/outputs/enrichment/{urlparse(url).netloc.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(enrichment_file), exist_ok=True)
            
            with open(enrichment_file, 'w') as f:
                json.dump(enrichment_data, f, indent=2)
            
            logger.info(f"Enrichment data saved for {url}")
            
        except Exception as e:
            logger.error(f"Failed to enrich URL {url}: {e}")


# Singleton instance
compliance_checker = ComplianceChecker()


async def check_url(url: URL) -> URLReport:
    """
    Check compliance for a single URL. This function is called by the API endpoint.
    """
    return await compliance_checker.check_url_compliance(url.content, url.batch_id)


async def generate_report(urls: List[URL], batch_id: str) -> ComplianceReport:
    """
    Generate a compliance report for a batch of URLs. This function is called by the API endpoint.
    """
    return await compliance_checker.generate_report(urls, batch_id) 