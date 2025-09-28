"""
Quality assurance service for validating analysis accuracy and calibrating confidence scores.
Performs random re-checks and tracks accuracy metrics.
"""
import os
import json
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from app.models.report import URLCategory
from app.services.database import database_service
from app.services.crawler import crawler_service

logger = logging.getLogger(__name__)


class QualityAssuranceService:
    """Service for quality assurance and confidence calibration."""
    
    def __init__(self):
        """Initialize the QA service."""
        self.qa_results_file = "data/qa/qa_results.json"
        self.confidence_calibration_file = "data/qa/confidence_calibration.json"
        self.recheck_percentage = 0.01  # 1% random recheck
        self.qa_history = defaultdict(list)
        self.confidence_calibration = {
            'blacklist': {'true_positives': 0, 'false_positives': 0, 'samples': []},
            'whitelist': {'true_positives': 0, 'false_positives': 0, 'samples': []},
            'review': {'escalated': 0, 'resolved': 0, 'samples': []}
        }
        self.accuracy_metrics = {
            'overall_accuracy': 0.0,
            'blacklist_precision': 0.0,
            'whitelist_precision': 0.0,
            'confidence_correlation': 0.0,
            'last_updated': None
        }
        self._load_qa_data()
    
    def _load_qa_data(self):
        """Load QA history and calibration data."""
        # Load QA results
        if os.path.exists(self.qa_results_file):
            try:
                with open(self.qa_results_file, 'r') as f:
                    data = json.load(f)
                    self.qa_history = defaultdict(list, data.get('qa_history', {}))
                    self.accuracy_metrics = data.get('accuracy_metrics', self.accuracy_metrics)
                logger.info(f"Loaded QA history with {sum(len(v) for v in self.qa_history.values())} checks")
            except Exception as e:
                logger.error(f"Failed to load QA results: {e}")
        
        # Load confidence calibration
        if os.path.exists(self.confidence_calibration_file):
            try:
                with open(self.confidence_calibration_file, 'r') as f:
                    self.confidence_calibration = json.load(f)
                logger.info("Loaded confidence calibration data")
            except Exception as e:
                logger.error(f"Failed to load confidence calibration: {e}")
    
    def _save_qa_data(self):
        """Save QA history and calibration data."""
        try:
            os.makedirs(os.path.dirname(self.qa_results_file), exist_ok=True)
            
            # Save QA results
            with open(self.qa_results_file, 'w') as f:
                json.dump({
                    'qa_history': dict(self.qa_history),
                    'accuracy_metrics': self.accuracy_metrics
                }, f, indent=2, default=str)
            
            # Save confidence calibration
            with open(self.confidence_calibration_file, 'w') as f:
                json.dump(self.confidence_calibration, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save QA data: {e}")
    
    async def should_recheck(self, url: str) -> bool:
        """Determine if a URL should be randomly rechecked."""
        # Always recheck if URL has been flagged
        if self._is_flagged_for_recheck(url):
            return True
        
        # Random recheck based on percentage
        return random.random() < self.recheck_percentage
    
    def _is_flagged_for_recheck(self, url: str) -> bool:
        """Check if URL has been flagged for recheck."""
        # Check if URL had conflicting results in the past
        if url in self.qa_history:
            checks = self.qa_history[url]
            if len(checks) >= 2:
                # Check for category changes
                categories = [check['category'] for check in checks[-3:]]
                if len(set(categories)) > 1:
                    return True
        return False
    
    async def perform_qa_check(self, url: str, original_category: URLCategory, 
                              original_confidence: float, original_method: str) -> Dict:
        """
        Perform a quality assurance check on a URL.
        
        Returns:
            Dict with QA results including consistency score
        """
        logger.info(f"Performing QA check on {url}")
        
        qa_result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'original_category': original_category.value,
            'original_confidence': original_confidence,
            'original_method': original_method,
            'recheck_category': None,
            'recheck_confidence': None,
            'recheck_method': None,
            'consistent': False,
            'confidence_delta': 0.0,
            'action': 'none'
        }
        
        try:
            # Re-crawl the URL
            content = await crawler_service.crawl_url(url, force_crawl=True)
            
            if not content or not content.full_text:
                qa_result['action'] = 'skip_no_content'
                return qa_result
            
            # Re-analyze with compliance checker
            # Import here to avoid circular import
            from app.core.compliance_checker import compliance_checker
            result = await compliance_checker.check_url_compliance(content)
            
            qa_result['recheck_category'] = result.category.value
            qa_result['recheck_confidence'] = getattr(result.ai_analysis, 'confidence', 0.0) if result.ai_analysis else 0.0
            qa_result['recheck_method'] = result.analysis_method
            
            # Check consistency
            qa_result['consistent'] = (
                qa_result['original_category'] == qa_result['recheck_category']
            )
            qa_result['confidence_delta'] = abs(
                qa_result['original_confidence'] - qa_result['recheck_confidence']
            )
            
            # Determine action based on results
            if not qa_result['consistent']:
                if qa_result['recheck_confidence'] > qa_result['original_confidence']:
                    qa_result['action'] = 'update_category'
                else:
                    qa_result['action'] = 'manual_review'
            elif qa_result['confidence_delta'] > 0.3:
                qa_result['action'] = 'calibrate_confidence'
            else:
                qa_result['action'] = 'confirmed'
            
            # Update QA history
            self.qa_history[url].append(qa_result)
            
            # Update calibration data
            await self._update_calibration(qa_result)
            
            # Save data
            self._save_qa_data()
            
        except Exception as e:
            logger.error(f"Error in QA check for {url}: {e}")
            qa_result['error'] = str(e)
            qa_result['action'] = 'error'
        
        return qa_result
    
    async def _update_calibration(self, qa_result: Dict):
        """Update confidence calibration based on QA results."""
        category = qa_result['original_category']
        
        if category in self.confidence_calibration:
            cal_data = self.confidence_calibration[category]
            
            # Add sample
            cal_data['samples'].append({
                'original_confidence': qa_result['original_confidence'],
                'recheck_confidence': qa_result['recheck_confidence'],
                'consistent': qa_result['consistent'],
                'timestamp': qa_result['timestamp']
            })
            
            # Keep only last 1000 samples
            if len(cal_data['samples']) > 1000:
                cal_data['samples'] = cal_data['samples'][-1000:]
            
            # Update metrics
            if qa_result['consistent']:
                cal_data['true_positives'] += 1
            else:
                cal_data['false_positives'] += 1
    
    def calculate_accuracy_metrics(self) -> Dict:
        """Calculate overall accuracy metrics from QA history."""
        total_checks = 0
        consistent_checks = 0
        category_accuracy = defaultdict(lambda: {'total': 0, 'correct': 0})
        confidence_errors = []
        
        # Analyze all QA checks
        for url, checks in self.qa_history.items():
            for check in checks:
                if 'error' not in check:
                    total_checks += 1
                    
                    if check['consistent']:
                        consistent_checks += 1
                        category_accuracy[check['original_category']]['correct'] += 1
                    
                    category_accuracy[check['original_category']]['total'] += 1
                    confidence_errors.append(check['confidence_delta'])
        
        # Calculate metrics
        if total_checks > 0:
            self.accuracy_metrics['overall_accuracy'] = consistent_checks / total_checks
            
            # Category-specific precision
            if category_accuracy['blacklist']['total'] > 0:
                self.accuracy_metrics['blacklist_precision'] = (
                    category_accuracy['blacklist']['correct'] / 
                    category_accuracy['blacklist']['total']
                )
            
            if category_accuracy['whitelist']['total'] > 0:
                self.accuracy_metrics['whitelist_precision'] = (
                    category_accuracy['whitelist']['correct'] / 
                    category_accuracy['whitelist']['total']
                )
            
            # Confidence correlation
            if confidence_errors:
                self.accuracy_metrics['confidence_correlation'] = 1.0 - np.mean(confidence_errors)
        
        self.accuracy_metrics['last_updated'] = datetime.now().isoformat()
        self.accuracy_metrics['total_qa_checks'] = total_checks
        
        return self.accuracy_metrics
    
    def get_confidence_adjustment(self, category: str, base_confidence: float) -> float:
        """
        Get adjusted confidence score based on calibration data.
        
        Returns:
            Adjusted confidence score
        """
        if category not in self.confidence_calibration:
            return base_confidence
        
        cal_data = self.confidence_calibration[category]
        
        # Calculate precision
        total = cal_data['true_positives'] + cal_data['false_positives']
        if total == 0:
            return base_confidence
        
        precision = cal_data['true_positives'] / total
        
        # Adjust confidence based on historical precision
        # If precision is low, reduce confidence
        # If precision is high, slightly increase confidence
        adjustment_factor = precision
        adjusted_confidence = base_confidence * (0.7 + 0.6 * adjustment_factor)
        
        # Ensure confidence stays in valid range
        return max(0.1, min(0.95, adjusted_confidence))
    
    async def generate_qa_report(self) -> Dict:
        """Generate a comprehensive QA report."""
        # Update metrics
        self.calculate_accuracy_metrics()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'accuracy_metrics': self.accuracy_metrics,
            'category_performance': {},
            'recent_inconsistencies': [],
            'confidence_calibration_summary': {},
            'recommendations': []
        }
        
        # Category performance
        for category in ['blacklist', 'whitelist', 'review']:
            if category in self.confidence_calibration:
                cal_data = self.confidence_calibration[category]
                total = cal_data['true_positives'] + cal_data['false_positives']
                
                report['category_performance'][category] = {
                    'total_checks': total,
                    'true_positives': cal_data['true_positives'],
                    'false_positives': cal_data['false_positives'],
                    'precision': cal_data['true_positives'] / total if total > 0 else 0
                }
        
        # Recent inconsistencies
        all_checks = []
        for url, checks in self.qa_history.items():
            all_checks.extend(checks)
        
        # Sort by timestamp and get recent inconsistent ones
        all_checks.sort(key=lambda x: x['timestamp'], reverse=True)
        inconsistent = [c for c in all_checks[:100] if not c.get('consistent', True)]
        report['recent_inconsistencies'] = inconsistent[:10]
        
        # Confidence calibration summary
        for category, cal_data in self.confidence_calibration.items():
            if cal_data['samples']:
                recent_samples = cal_data['samples'][-100:]
                avg_original = np.mean([s['original_confidence'] for s in recent_samples])
                avg_recheck = np.mean([s['recheck_confidence'] for s in recent_samples])
                
                report['confidence_calibration_summary'][category] = {
                    'average_original_confidence': avg_original,
                    'average_recheck_confidence': avg_recheck,
                    'confidence_drift': avg_recheck - avg_original,
                    'sample_size': len(recent_samples)
                }
        
        # Generate recommendations
        if self.accuracy_metrics['overall_accuracy'] < 0.85:
            report['recommendations'].append(
                "Overall accuracy is below 85%. Consider reviewing analysis rules and thresholds."
            )
        
        if self.accuracy_metrics['blacklist_precision'] < 0.9:
            report['recommendations'].append(
                "Blacklist precision is low. Review blacklist criteria and consider stricter thresholds."
            )
        
        for category, summary in report['confidence_calibration_summary'].items():
            if abs(summary['confidence_drift']) > 0.1:
                report['recommendations'].append(
                    f"{category.capitalize()} confidence scores are drifting by {summary['confidence_drift']:.2f}. "
                    f"Consider recalibrating the model."
                )
        
        return report
    
    async def validate_batch_results(self, batch_id: str, sample_size: int = 10) -> Dict:
        """
        Validate a sample of results from a batch.
        
        Args:
            batch_id: The batch ID to validate
            sample_size: Number of URLs to sample for validation
            
        Returns:
            Validation results
        """
        validation_results = {
            'batch_id': batch_id,
            'timestamp': datetime.now().isoformat(),
            'sample_size': sample_size,
            'checks': [],
            'consistency_rate': 0.0,
            'average_confidence_delta': 0.0
        }
        
        try:
            # Get URLs from batch
            urls = await database_service.get_urls_by_batch(batch_id, limit=1000)
            
            # Sample URLs for validation
            if len(urls) <= sample_size:
                sample_urls = urls
            else:
                sample_urls = random.sample(urls, sample_size)
            
            validation_results['actual_sample_size'] = len(sample_urls)
            
            # Validate each sampled URL
            for url in sample_urls:
                # Get original report
                url_report = await database_service.get_url_report_by_url_id(url.id)
                
                if url_report:
                    qa_result = await self.perform_qa_check(
                        url.url,
                        url_report.category,
                        getattr(url_report.ai_analysis, 'confidence', 0.5) if url_report.ai_analysis else 0.5,
                        url_report.analysis_method
                    )
                    validation_results['checks'].append(qa_result)
            
            # Calculate summary metrics
            if validation_results['checks']:
                consistent_count = sum(1 for c in validation_results['checks'] if c['consistent'])
                validation_results['consistency_rate'] = consistent_count / len(validation_results['checks'])
                
                confidence_deltas = [c['confidence_delta'] for c in validation_results['checks']]
                validation_results['average_confidence_delta'] = np.mean(confidence_deltas)
            
        except Exception as e:
            logger.error(f"Error validating batch {batch_id}: {e}")
            validation_results['error'] = str(e)
        
        return validation_results


# Singleton instance
qa_service = QualityAssuranceService() 