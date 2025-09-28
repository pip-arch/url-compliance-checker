"""
Domain analyzer service for intelligent bulk domain processing.
Tracks domain violations and triggers bulk analysis for problematic domains.
"""
import os
import logging
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse
import json

from app.models.report import URLCategory
from app.services.database import database_service
from app.services.crawler import crawler_service
from app.core.blacklist_manager import blacklist_manager

logger = logging.getLogger(__name__)


class DomainAnalyzer:
    """Service for analyzing domains with multiple violations."""
    
    def __init__(self):
        """Initialize the domain analyzer."""
        self.domain_violations = defaultdict(lambda: {
            'blacklist_count': 0,
            'review_count': 0,
            'total_count': 0,
            'urls': [],
            'first_seen': None,
            'last_seen': None,
            'auto_blacklisted': False
        })
        self.violation_threshold = 2  # Trigger bulk analysis after 2 violations
        self.bulk_analysis_queue = asyncio.Queue()
        self.analysis_results_file = "data/outputs/domain_analysis_results.json"
        self._load_domain_history()
    
    def _load_domain_history(self):
        """Load domain violation history from file."""
        if os.path.exists(self.analysis_results_file):
            try:
                with open(self.analysis_results_file, 'r') as f:
                    history = json.load(f)
                    for domain, data in history.items():
                        self.domain_violations[domain] = data
                logger.info(f"Loaded domain history for {len(self.domain_violations)} domains")
            except Exception as e:
                logger.error(f"Failed to load domain history: {e}")
    
    def _save_domain_history(self):
        """Save domain violation history to file."""
        try:
            os.makedirs(os.path.dirname(self.analysis_results_file), exist_ok=True)
            with open(self.analysis_results_file, 'w') as f:
                json.dump(dict(self.domain_violations), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save domain history: {e}")
    
    async def track_url_result(self, url: str, category: URLCategory, confidence: float = 0.0):
        """
        Track a URL analysis result and trigger domain analysis if needed.
        
        Args:
            url: The analyzed URL
            category: The category assigned to the URL
            confidence: Confidence score of the analysis
        """
        domain = self._extract_domain(url)
        if not domain:
            return
        
        # Update domain statistics
        domain_data = self.domain_violations[domain]
        domain_data['total_count'] += 1
        domain_data['urls'].append({
            'url': url,
            'category': category.value if hasattr(category, 'value') else str(category),
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 URLs per domain
        if len(domain_data['urls']) > 100:
            domain_data['urls'] = domain_data['urls'][-100:]
        
        # Update timestamps
        now = datetime.now().isoformat()
        if not domain_data['first_seen']:
            domain_data['first_seen'] = now
        domain_data['last_seen'] = now
        
        # Update category counts
        if category == URLCategory.BLACKLIST:
            domain_data['blacklist_count'] += 1
        elif category == URLCategory.REVIEW:
            domain_data['review_count'] += 1
        
        # Check if domain needs bulk analysis
        violation_count = domain_data['blacklist_count'] + (domain_data['review_count'] * 0.5)
        
        if violation_count >= self.violation_threshold and not domain_data['auto_blacklisted']:
            logger.warning(f"Domain {domain} has {violation_count} violations. Triggering bulk analysis.")
            await self.bulk_analysis_queue.put(domain)
        
        # Save updated history
        self._save_domain_history()
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract main domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Extract main domain (remove subdomains)
            parts = domain.split('.')
            if len(parts) > 2:
                # Keep last two parts (domain.tld)
                return '.'.join(parts[-2:])
            return domain
        except:
            return None
    
    async def analyze_domain(self, domain: str) -> Dict:
        """
        Perform comprehensive analysis of a domain.
        
        Returns:
            Dict with analysis results including:
            - should_blacklist: Whether to blacklist entire domain
            - sample_urls: Sample URLs analyzed
            - violation_rate: Percentage of URLs that are problematic
            - common_issues: Most common compliance issues
        """
        logger.info(f"Starting comprehensive analysis of domain: {domain}")
        
        analysis_result = {
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'should_blacklist': False,
            'violation_rate': 0.0,
            'total_urls_checked': 0,
            'blacklist_count': 0,
            'whitelist_count': 0,
            'review_count': 0,
            'sample_urls': [],
            'common_issues': [],
            'recommendation': '',
            'confidence': 0.0
        }
        
        try:
            # Get more URLs from this domain
            domain_urls = await self._discover_domain_urls(domain)
            
            if not domain_urls:
                logger.warning(f"No additional URLs found for domain {domain}")
                # Base decision on existing data
                domain_data = self.domain_violations[domain]
                violation_rate = (domain_data['blacklist_count'] + domain_data['review_count'] * 0.5) / max(domain_data['total_count'], 1)
                analysis_result['violation_rate'] = violation_rate
                analysis_result['should_blacklist'] = violation_rate > 0.7
                analysis_result['recommendation'] = self._get_recommendation(violation_rate)
                return analysis_result
            
            # Analyze sample of URLs
            sample_size = min(len(domain_urls), 10)  # Analyze up to 10 URLs
            sample_urls = domain_urls[:sample_size]
            
            logger.info(f"Analyzing {sample_size} sample URLs from {domain}")
            
            # Analyze each URL
            # Import here to avoid circular import
            from app.core.compliance_checker import compliance_checker
            
            for url in sample_urls:
                try:
                    # Crawl URL
                    content = await crawler_service.crawl_url(url)
                    if content and content.full_text:
                        # Analyze content
                        result = await compliance_checker.check_url_compliance(content)
                        
                        analysis_result['total_urls_checked'] += 1
                        
                        if result.category == URLCategory.BLACKLIST:
                            analysis_result['blacklist_count'] += 1
                        elif result.category == URLCategory.WHITELIST:
                            analysis_result['whitelist_count'] += 1
                        else:
                            analysis_result['review_count'] += 1
                        
                        # Track sample URL
                        analysis_result['sample_urls'].append({
                            'url': url,
                            'category': result.category.value,
                            'confidence': getattr(result.ai_analysis, 'confidence', 0.0) if result.ai_analysis else 0.0,
                            'issues': getattr(result.ai_analysis, 'compliance_issues', []) if result.ai_analysis else []
                        })
                        
                        # Collect common issues
                        if result.ai_analysis and result.ai_analysis.compliance_issues:
                            analysis_result['common_issues'].extend(result.ai_analysis.compliance_issues)
                
                except Exception as e:
                    logger.error(f"Failed to analyze URL {url}: {e}")
            
            # Calculate violation rate
            if analysis_result['total_urls_checked'] > 0:
                violation_rate = (analysis_result['blacklist_count'] + analysis_result['review_count'] * 0.5) / analysis_result['total_urls_checked']
                analysis_result['violation_rate'] = violation_rate
                
                # Decision logic
                if violation_rate > 0.7:
                    analysis_result['should_blacklist'] = True
                    analysis_result['confidence'] = min(violation_rate, 0.95)
                elif violation_rate > 0.5:
                    analysis_result['should_blacklist'] = False
                    analysis_result['confidence'] = 0.6
                else:
                    analysis_result['should_blacklist'] = False
                    analysis_result['confidence'] = 0.8
                
                analysis_result['recommendation'] = self._get_recommendation(violation_rate)
            
            # Find most common issues
            if analysis_result['common_issues']:
                issue_counts = defaultdict(int)
                for issue in analysis_result['common_issues']:
                    issue_counts[str(issue)] += 1
                
                # Get top 3 most common issues
                sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                analysis_result['common_issues'] = [issue for issue, count in sorted_issues]
            
            # Update domain data
            if analysis_result['should_blacklist']:
                self.domain_violations[domain]['auto_blacklisted'] = True
                # Add to blacklist
                await self._blacklist_domain(domain, analysis_result)
            
            self._save_domain_history()
            
        except Exception as e:
            logger.error(f"Failed to analyze domain {domain}: {e}")
            analysis_result['error'] = str(e)
        
        return analysis_result
    
    async def _discover_domain_urls(self, domain: str) -> List[str]:
        """Discover more URLs from a domain using various methods."""
        urls = set()
        
        # 1. Check robots.txt
        robots_url = f"https://{domain}/robots.txt"
        try:
            content = await crawler_service.crawl_url(robots_url)
            if content and content.full_text:
                # Extract URLs from robots.txt
                for line in content.full_text.split('\n'):
                    if line.startswith('Sitemap:'):
                        urls.add(line.replace('Sitemap:', '').strip())
        except:
            pass
        
        # 2. Check common pages
        common_paths = [
            '/', '/about', '/contact', '/services', '/products',
            '/blog', '/news', '/privacy', '/terms', '/faq'
        ]
        
        for path in common_paths:
            urls.add(f"https://{domain}{path}")
            urls.add(f"http://{domain}{path}")
        
        # 3. Get URLs from existing violations
        if domain in self.domain_violations:
            for url_data in self.domain_violations[domain]['urls']:
                urls.add(url_data['url'])
        
        return list(urls)
    
    def _get_recommendation(self, violation_rate: float) -> str:
        """Get recommendation based on violation rate."""
        if violation_rate > 0.8:
            return "BLACKLIST DOMAIN - Very high violation rate. Strong evidence of non-compliance."
        elif violation_rate > 0.6:
            return "HIGH RISK - Significant violations detected. Manual review recommended."
        elif violation_rate > 0.4:
            return "MODERATE RISK - Some violations detected. Monitor closely."
        elif violation_rate > 0.2:
            return "LOW RISK - Few violations. Continue monitoring."
        else:
            return "MINIMAL RISK - Domain appears largely compliant."
    
    async def _blacklist_domain(self, domain: str, analysis_result: Dict):
        """Add domain to blacklist with analysis results."""
        try:
            # Add to blacklist manager
            blacklist_manager.blacklisted_domains.add(domain)
            
            # Log the action
            logger.warning(f"AUTO-BLACKLISTED DOMAIN: {domain} (violation rate: {analysis_result['violation_rate']:.2%})")
            
            # Save to domain blacklist file
            domain_blacklist_file = "data/outputs/blacklisted_domains.csv"
            os.makedirs(os.path.dirname(domain_blacklist_file), exist_ok=True)
            
            import csv
            file_exists = os.path.exists(domain_blacklist_file)
            
            with open(domain_blacklist_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Domain', 'Violation Rate', 'URLs Checked', 'Blacklist Count', 
                                   'Review Count', 'Recommendation', 'Timestamp'])
                
                writer.writerow([
                    domain,
                    f"{analysis_result['violation_rate']:.2%}",
                    analysis_result['total_urls_checked'],
                    analysis_result['blacklist_count'],
                    analysis_result['review_count'],
                    analysis_result['recommendation'],
                    analysis_result['timestamp']
                ])
            
        except Exception as e:
            logger.error(f"Failed to blacklist domain {domain}: {e}")
    
    async def process_bulk_analysis_queue(self):
        """Process domains in the bulk analysis queue."""
        while True:
            try:
                # Get domain from queue
                domain = await self.bulk_analysis_queue.get()
                
                # Analyze domain
                logger.info(f"Processing bulk analysis for domain: {domain}")
                analysis_result = await self.analyze_domain(domain)
                
                # Save analysis result
                analysis_file = f"data/outputs/domain_analysis/{domain.replace('.', '_')}_analysis.json"
                os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
                
                with open(analysis_file, 'w') as f:
                    json.dump(analysis_result, f, indent=2)
                
                logger.info(f"Completed analysis for {domain}. Should blacklist: {analysis_result['should_blacklist']}")
                
            except Exception as e:
                logger.error(f"Error in bulk analysis queue: {e}")
            
            # Small delay between analyses
            await asyncio.sleep(1)
    
    def get_domain_statistics(self) -> Dict:
        """Get statistics about tracked domains."""
        stats = {
            'total_domains': len(self.domain_violations),
            'auto_blacklisted_domains': 0,
            'high_risk_domains': 0,
            'domains_by_violation_count': defaultdict(int),
            'top_violating_domains': []
        }
        
        # Calculate statistics
        for domain, data in self.domain_violations.items():
            if data['auto_blacklisted']:
                stats['auto_blacklisted_domains'] += 1
            
            violation_count = data['blacklist_count'] + data['review_count']
            if violation_count >= self.violation_threshold:
                stats['high_risk_domains'] += 1
            
            stats['domains_by_violation_count'][violation_count] += 1
        
        # Get top violating domains
        sorted_domains = sorted(
            self.domain_violations.items(),
            key=lambda x: x[1]['blacklist_count'] + x[1]['review_count'],
            reverse=True
        )[:10]
        
        stats['top_violating_domains'] = [
            {
                'domain': domain,
                'violations': data['blacklist_count'] + data['review_count'],
                'blacklist_count': data['blacklist_count'],
                'review_count': data['review_count'],
                'auto_blacklisted': data['auto_blacklisted']
            }
            for domain, data in sorted_domains
        ]
        
        return stats


# Singleton instance
domain_analyzer = DomainAnalyzer() 