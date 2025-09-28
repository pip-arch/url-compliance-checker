"""
Blacklist Keywords Fallback Mechanism

This module provides a fallback for AI analysis when the OpenRouter service is unavailable.
It uses a predefined set of keywords from an Excel file to identify potentially non-compliant URLs.
"""
import os
import logging
import re
from typing import List, Dict, Any, Set, Optional
import pandas as pd

from app.models.url import URLContent
from app.models.report import AIAnalysisResult, URLCategory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to blacklist keywords file
BLACKLIST_KEYWORDS_FILE = os.path.join(os.getcwd(), "data/inputs/blacklist_keywords/Blacklist keywords.csv")


class BlacklistKeywords:
    """
    Class for analyzing URL content using blacklist keywords.
    This serves as a fallback mechanism when the AI service is unavailable.
    """
    
    def __init__(self):
        """Initialize blacklist keywords."""
        self.keywords = self._load_keywords()
        
    def _load_keywords(self) -> Dict[str, List[str]]:
        """Load blacklist keywords from Excel file."""
        try:
            if not os.path.exists(BLACKLIST_KEYWORDS_FILE):
                logger.error(f"Blacklist keywords file not found at: {BLACKLIST_KEYWORDS_FILE}")
                return {}
            
            # Read CSV file
            df = pd.read_csv(BLACKLIST_KEYWORDS_FILE)
            
            # Initialize categories
            keywords = {
                "misleading_info": [],
                "unauthorized_offer": [],
                "false_representation": [],
                "regulatory_issues": [],
                "inappropriate_marketing": [],
                "investment_guarantees": [],
                "leverage_misrepresentation": [],
                "unrealistic_returns": [],
                "regulated_products_misuse": [],
                "no_risk_disclosure": []
            }
            
            # Process each column
            for column in df.columns:
                # Skip empty columns or non-string column names
                if not isinstance(column, str) or not column.strip():
                    continue
                
                # Normalize column name
                normalized_col = column.lower().strip()
                
                # Map column to category
                category = None
                if "mislead" in normalized_col:
                    category = "misleading_info"
                elif "unauthor" in normalized_col or "bonus" in normalized_col or "offer" in normalized_col:
                    category = "unauthorized_offer"
                elif "false" in normalized_col or "represent" in normalized_col:
                    category = "false_representation"
                elif "regulat" in normalized_col:
                    category = "regulatory_issues"
                elif "market" in normalized_col:
                    category = "inappropriate_marketing"
                elif "guarantee" in normalized_col or "invest" in normalized_col:
                    category = "investment_guarantees"
                elif "leverage" in normalized_col:
                    category = "leverage_misrepresentation"
                elif "return" in normalized_col or "profit" in normalized_col:
                    category = "unrealistic_returns"
                elif "product" in normalized_col or "misuse" in normalized_col:
                    category = "regulated_products_misuse"
                elif "risk" in normalized_col or "disclosure" in normalized_col:
                    category = "no_risk_disclosure"
                else:
                    # If no match, put in misleading info as default
                    category = "misleading_info"
                
                # Extract non-empty values from column
                values = [str(val).strip().lower() for val in df[column].dropna() if str(val).strip()]
                keywords[category].extend(values)
            
            # Log summary
            total_keywords = sum(len(words) for words in keywords.values())
            if total_keywords == 0:
                logger.error("No keywords loaded from blacklist file. Fallback will not work properly.")
            else:
                logger.info(f"Loaded {total_keywords} blacklist keywords across {len(keywords)} categories")
                for category, words in keywords.items():
                    logger.debug(f"  {category}: {len(words)} keywords")
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error loading blacklist keywords: {str(e)}")
            return {}
    
    def analyze_content(self, url_content: URLContent) -> AIAnalysisResult:
        """
        Analyze URL content using blacklist keywords.
        This is a simplified version of the AI analysis that uses keyword matching.
        """
        if not self.keywords:
            logger.error("No blacklist keywords available. Cannot perform fallback analysis.")
            raise RuntimeError("Blacklist keywords not available for fallback analysis")
        
        # Extract text from content
        text = url_content.title or ""
        if url_content.mentions:
            for mention in url_content.mentions:
                text += " " + mention.context_before + " " + mention.text + " " + mention.context_after
        
        text = text.lower()
        
        # Find matches for each category
        matches: Dict[str, List[str]] = {category: [] for category in self.keywords.keys()}
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                # Use word boundary to match whole words
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches[category].append(keyword)
        
        # Count matches by category
        critical_categories = ["regulatory_issues", "regulated_products_misuse"]
        high_categories = ["misleading_info", "false_representation", "investment_guarantees", 
                          "leverage_misrepresentation", "unrealistic_returns", "no_risk_disclosure"]
        medium_categories = ["unauthorized_offer", "inappropriate_marketing"]
        
        critical_count = sum(len(matches[cat]) for cat in critical_categories)
        high_count = sum(len(matches[cat]) for cat in high_categories)
        medium_count = sum(len(matches[cat]) for cat in medium_categories)
        
        total_matches = critical_count + high_count + medium_count
        
        # Determine category based on matches
        compliance_issues = []
        category = URLCategory.WHITELIST
        confidence = 0.7  # Default confidence
        
        if critical_count > 0 or high_count >= 2 or (high_count >= 1 and medium_count >= 2) or medium_count >= 4:
            category = URLCategory.BLACKLIST
            confidence = min(0.9, 0.7 + (critical_count * 0.05) + (high_count * 0.03) + (medium_count * 0.01))
            
            # Add compliance issues
            for cat_name, found_keywords in matches.items():
                if found_keywords:
                    readable_category = cat_name.replace("_", " ").title()
                    compliance_issues.append(f"{readable_category}: {', '.join(found_keywords[:3])}")
        
        elif high_count == 1 or medium_count >= 2:
            category = URLCategory.REVIEW
            confidence = 0.65
            
            # Add compliance issues
            for cat_name, found_keywords in matches.items():
                if found_keywords:
                    readable_category = cat_name.replace("_", " ").title()
                    compliance_issues.append(f"{readable_category}: {', '.join(found_keywords[:3])}")
        
        # Generate explanation
        explanation = self._generate_explanation(category, total_matches, critical_count, high_count, medium_count)
        
        return AIAnalysisResult(
            model="blacklist-keywords-fallback",
            category=category,
            confidence=confidence,
            explanation=explanation,
            compliance_issues=compliance_issues[:5],  # Limit to 5 issues
            raw_response={"matches": matches, "match_counts": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "total": total_matches
            }}
        )
    
    def _generate_explanation(self, category: URLCategory, total_matches: int, 
                             critical_count: int, high_count: int, medium_count: int) -> str:
        """Generate explanation based on category and match counts."""
        if category == URLCategory.BLACKLIST:
            if critical_count > 0:
                return f"FALLBACK: Found {critical_count} critical compliance issues that require blacklisting"
            elif high_count >= 2:
                return f"FALLBACK: Found {high_count} high-severity compliance issues that require blacklisting"
            else:
                return f"FALLBACK: Found {total_matches} compliance issues ({high_count} high, {medium_count} medium) that require blacklisting"
        
        elif category == URLCategory.REVIEW:
            return f"FALLBACK: Found potential compliance issues ({high_count} high, {medium_count} medium) that require review"
        
        else:
            return "FALLBACK: No significant compliance issues detected"


# Singleton instance
blacklist_keywords = BlacklistKeywords() 