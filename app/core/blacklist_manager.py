"""
Blacklist manager for URL Checker application.
Handles blacklisting of domains and URLs, including reading, writing, and updating
blacklist files with enhanced metadata.
"""
import os
import csv
import logging
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

# Blacklist file paths
DEFAULT_BLACKLIST_DIR = "data/tmp"
CONSOLIDATED_BLACKLIST_FILE = os.path.join(DEFAULT_BLACKLIST_DIR, "blacklist_consolidated.csv")

# Blacklist threshold configuration
DEFAULT_BLACKLIST_THRESHOLD = int(os.getenv("BLACKLIST_THRESHOLD", "1"))  # Lower threshold to 1 by default
BLACKLIST_CONFIDENCE_THRESHOLD = float(os.getenv("BLACKLIST_CONFIDENCE_THRESHOLD", "0.7"))  # Confidence threshold

class BlacklistManager:
    """
    Manager for domain blacklisting operations:
    1. Read blacklisted domains from file
    2. Check if a domain is blacklisted
    3. Add domains to blacklist with detailed metadata
    4. Export blacklist in various formats
    5. Track domain reputation history
    """
    
    def __init__(self, blacklist_file: str = CONSOLIDATED_BLACKLIST_FILE):
        """Initialize blacklist manager."""
        self.blacklist_file = blacklist_file
        self.blacklist_dir = os.path.dirname(blacklist_file)
        self.blacklisted_domains: Set[str] = set()
        self.domain_issues: Dict[str, Dict[str, any]] = {}
        # New: Track domain reputation history
        self.domain_history: Dict[str, List[Dict[str, any]]] = {}
        self.lock = asyncio.Lock()  # For thread-safe operations
        
        # Create directories if they don't exist
        os.makedirs(self.blacklist_dir, exist_ok=True)
        
        # Create blacklist file if it doesn't exist
        if not os.path.exists(self.blacklist_file):
            self._create_blacklist_file()
        
        # Load blacklisted domains
        self._load_blacklisted_domains()
    
    def _create_blacklist_file(self):
        """Create a new blacklist file with headers."""
        with open(self.blacklist_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "URL",
                "Main Domain",
                "Reason",
                "Confidence",
                "Category",
                "Compliance Issues",
                "Batch ID",
                "Timestamp"
            ])
        logger.info(f"Created new blacklist file: {self.blacklist_file}")
    
    def _load_blacklisted_domains(self):
        """Load blacklisted domains from file."""
        try:
            with open(self.blacklist_file, "r", newline="") as f:
                reader = csv.DictReader(f)
                
                # Check if file is empty or has old format
                if not reader.fieldnames or len(reader.fieldnames) < 3:
                    logger.warning(f"Blacklist file has invalid format, recreating: {self.blacklist_file}")
                    self._create_blacklist_file()
                    return
                
                for row in reader:
                    if "Main Domain" in row and row["Main Domain"]:
                        domain = row["Main Domain"].lower()
                        self.blacklisted_domains.add(domain)
                        
                        # Store domain issues
                        if domain not in self.domain_issues:
                            self.domain_issues[domain] = {
                                "urls": [],
                                "reasons": set(),
                                "categories": set(),
                                "confidence": 0.0,
                                "batch_ids": set(),
                                "compliance_issues": set(),
                                "first_added": datetime.now().isoformat(),
                                "violation_count": 0
                            }
                        
                        # Update domain issues
                        if "URL" in row and row["URL"]:
                            self.domain_issues[domain]["urls"].append(row["URL"])
                        if "Reason" in row and row["Reason"]:
                            self.domain_issues[domain]["reasons"].add(row["Reason"])
                        if "Category" in row and row["Category"]:
                            self.domain_issues[domain]["categories"].add(row["Category"])
                        if "Confidence" in row and row["Confidence"]:
                            try:
                                confidence = float(row["Confidence"])
                                if confidence > self.domain_issues[domain]["confidence"]:
                                    self.domain_issues[domain]["confidence"] = confidence
                            except ValueError:
                                pass
                        if "Batch ID" in row and row["Batch ID"]:
                            self.domain_issues[domain]["batch_ids"].add(row["Batch ID"])
                        if "Compliance Issues" in row and row["Compliance Issues"]:
                            # Split comma-separated issues
                            issues = [issue.strip() for issue in row["Compliance Issues"].split(",")]
                            self.domain_issues[domain]["compliance_issues"].update(issues)
                
                logger.info(f"Loaded {len(self.blacklisted_domains)} blacklisted domains from {self.blacklist_file}")
        except FileNotFoundError:
            logger.warning(f"Blacklist file not found, creating new file: {self.blacklist_file}")
            self._create_blacklist_file()
        except Exception as e:
            logger.error(f"Error loading blacklisted domains: {str(e)}")
    
    async def is_blacklisted(self, url: str) -> Tuple[bool, Optional[Dict[str, any]]]:
        """
        Check if a URL's domain is blacklisted.
        Returns a tuple of (is_blacklisted, domain_info).
        """
        domain = self._extract_domain(url)
        async with self.lock:
            is_blacklisted = domain in self.blacklisted_domains
            domain_info = self.domain_issues.get(domain) if is_blacklisted else None
            return is_blacklisted, domain_info
    
    async def add_to_blacklist(
        self,
        url: str,
        reason: str,
        confidence: float = 0.0,
        category: str = "",
        compliance_issues: List[str] = None,
        batch_id: str = ""
    ) -> bool:
        """
        Add a domain to the blacklist with enhanced metadata.
        Returns True if domain was newly blacklisted, False if it was already blacklisted.
        """
        domain = self._extract_domain(url)
        
        async with self.lock:
            # Check if domain is already blacklisted
            already_blacklisted = domain in self.blacklisted_domains
            
            # Add to blacklisted domains
            self.blacklisted_domains.add(domain)
            
            # Initialize domain issues if not exists
            if domain not in self.domain_issues:
                self.domain_issues[domain] = {
                    "urls": [],
                    "reasons": set(),
                    "categories": set(),
                    "confidence": 0.0,
                    "batch_ids": set(),
                    "compliance_issues": set(),
                    "first_added": datetime.now().isoformat(),
                    "violation_count": 0
                }
            
            # Update domain issues
            issues = self.domain_issues[domain]
            issues["urls"].append(url)
            issues["reasons"].add(reason)
            if category:
                issues["categories"].add(category)
            if confidence > issues["confidence"]:
                issues["confidence"] = confidence
            if batch_id:
                issues["batch_ids"].add(batch_id)
            if compliance_issues:
                issues["compliance_issues"].update(compliance_issues)
                
            # Track violation count
            issues["violation_count"] += 1
            
            # Add to domain history
            if domain not in self.domain_history:
                self.domain_history[domain] = []
                
            # Add history entry
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "reason": reason,
                "confidence": confidence,
                "category": category,
                "compliance_issues": compliance_issues or [],
                "batch_id": batch_id
            }
            self.domain_history[domain].append(history_entry)
            
            # Append to blacklist file
            self._append_to_blacklist_file(
                url=url,
                domain=domain,
                reason=reason,
                confidence=confidence,
                category=category,
                compliance_issues=compliance_issues or [],
                batch_id=batch_id
            )
            
            if not already_blacklisted:
                logger.info(f"Added new domain to blacklist: {domain} (reason: {reason})")
            else:
                logger.info(f"Updated existing blacklisted domain: {domain} (reason: {reason})")
            
            return not already_blacklisted
    
    async def get_blacklist(self) -> Dict[str, Dict[str, any]]:
        """Get the complete blacklist with domain issues."""
        async with self.lock:
            return self.domain_issues.copy()
    
    async def export_blacklist(self, format_type: str = "csv", output_file: str = None) -> str:
        """
        Export the blacklist in various formats (csv, json, txt).
        Returns the path to the exported file.
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.blacklist_dir, f"blacklist_export_{timestamp}.{format_type}")
        
        async with self.lock:
            if format_type == "csv":
                await self._export_csv(output_file)
            elif format_type == "json":
                await self._export_json(output_file)
            elif format_type == "txt":
                await self._export_txt(output_file)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            logger.info(f"Exported blacklist to {output_file}")
            return output_file
    
    async def _export_csv(self, output_file: str):
        """Export blacklist to CSV format."""
        import csv
        
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Domain",
                "URLs",
                "Reasons",
                "Categories",
                "Confidence",
                "Compliance Issues",
                "Batch IDs",
                "First Added"
            ])
            
            for domain, issues in self.domain_issues.items():
                writer.writerow([
                    domain,
                    "; ".join(issues["urls"]),
                    "; ".join(issues["reasons"]),
                    "; ".join(issues["categories"]),
                    issues["confidence"],
                    "; ".join(issues["compliance_issues"]),
                    "; ".join(issues["batch_ids"]),
                    datetime.now().isoformat()  # Placeholder for first added timestamp
                ])
    
    async def _export_json(self, output_file: str):
        """Export blacklist to JSON format."""
        import json
        
        # Convert sets to lists for JSON serialization
        json_data = {}
        for domain, issues in self.domain_issues.items():
            # Add reputation history for each domain
            domain_history = self.domain_history.get(domain, [])
            
            json_data[domain] = {
                "urls": issues["urls"],
                "reasons": list(issues["reasons"]),
                "categories": list(issues["categories"]),
                "confidence": issues["confidence"],
                "compliance_issues": list(issues["compliance_issues"]),
                "batch_ids": list(issues["batch_ids"]),
                "first_added": issues.get("first_added", datetime.now().isoformat()),
                "violation_count": issues.get("violation_count", 1),
                "history": domain_history
            }
        
        with open(output_file, "w") as f:
            json.dump(json_data, f, indent=2)
    
    async def _export_txt(self, output_file: str):
        """Export blacklist to plain text format (just domains)."""
        with open(output_file, "w") as f:
            for domain in sorted(self.blacklisted_domains):
                f.write(f"{domain}\n")
    
    def _append_to_blacklist_file(
        self,
        url: str,
        domain: str,
        reason: str,
        confidence: float,
        category: str,
        compliance_issues: List[str],
        batch_id: str
    ):
        """Append a new entry to the blacklist file."""
        timestamp = datetime.now().isoformat()
        
        try:
            # Write to consolidated blacklist file
            with open(self.blacklist_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    url,
                    domain,
                    reason,
                    confidence,
                    category,
                    ",".join(compliance_issues),
                    batch_id,
                    timestamp
                ])
                
            # Add explicit logging similar to direct_analysis script
            logger.info(f"Blacklisted URL: {url} (domain: {domain}, reason: {reason[:30]}...)")
            logger.info(f"Added URL to blacklist: {url} -> {self.blacklist_file}")
            
        except Exception as e:
            logger.error(f"Error writing to blacklist file: {e}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract main domain from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            
            return domain
        except Exception as e:
            logger.error(f"Error extracting domain from URL {url}: {str(e)}")
            # Return original netloc as fallback
            return urlparse(url).netloc.lower()

    async def get_domain_reputation(self, domain: str) -> Dict[str, any]:
        """
        Get detailed reputation analytics for a specific domain.
        Includes violation history, confidence trend, and issue types.
        """
        domain = self._extract_domain(domain)
        
        async with self.lock:
            result = {
                "domain": domain,
                "is_blacklisted": domain in self.blacklisted_domains,
                "violation_count": 0,
                "first_detected": None,
                "last_detected": None,
                "confidence_trend": [],
                "common_issues": [],
                "related_urls": []
            }
            
            # Return basic info if domain not in our records
            if domain not in self.domain_history:
                return result
                
            # Process history data
            history = self.domain_history[domain]
            result["violation_count"] = len(history)
            result["first_detected"] = history[0]["timestamp"] if history else None
            result["last_detected"] = history[-1]["timestamp"] if history else None
            
            # Extract confidence trend
            result["confidence_trend"] = [
                {"timestamp": entry["timestamp"], "confidence": entry["confidence"]}
                for entry in history
            ]
            
            # Count issue types
            issue_counts = {}
            urls = set()
            
            for entry in history:
                urls.add(entry["url"])
                for issue in entry["compliance_issues"]:
                    issue_type = issue.split(":")[0] if ":" in issue else issue
                    issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            
            # Get top 5 common issues
            result["common_issues"] = [
                {"issue": issue, "count": count}
                for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Add related URLs
            result["related_urls"] = list(urls)
            
            return result
    
    async def get_blacklist_analytics(self) -> Dict[str, any]:
        """
        Get analytics about the blacklist, including:
        - Total domains blacklisted
        - Top violation types
        - Recent additions
        - Domains by confidence level
        """
        async with self.lock:
            # Count violation types across all domains
            violation_types = {}
            domains_by_confidence = {
                "high": [],    # 0.8-1.0
                "medium": [],  # 0.5-0.8
                "low": []      # 0.0-0.5
            }
            
            recent_additions = []
            
            for domain, issues in self.domain_issues.items():
                # Categorize by confidence
                confidence = issues.get("confidence", 0)
                if confidence >= 0.8:
                    domains_by_confidence["high"].append(domain)
                elif confidence >= 0.5:
                    domains_by_confidence["medium"].append(domain)
                else:
                    domains_by_confidence["low"].append(domain)
                
                # Count violation types
                for issue in issues.get("compliance_issues", []):
                    issue_type = issue.split(":")[0] if ":" in issue else issue
                    violation_types[issue_type] = violation_types.get(issue_type, 0) + 1
                
                # Add to recent additions if added in the last 7 days
                first_added = issues.get("first_added")
                if first_added:
                    try:
                        added_date = datetime.fromisoformat(first_added)
                        if (datetime.now() - added_date).days <= 7:
                            recent_additions.append({
                                "domain": domain,
                                "added_date": first_added,
                                "violation_count": issues.get("violation_count", 1),
                                "confidence": confidence
                            })
                    except (ValueError, TypeError):
                        pass
            
            # Sort recent additions by date
            recent_additions.sort(key=lambda x: x["added_date"], reverse=True)
            
            return {
                "total_blacklisted": len(self.blacklisted_domains),
                "top_violations": [
                    {"type": vtype, "count": count}
                    for vtype, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True)[:10]
                ],
                "domains_by_confidence": {
                    "high": len(domains_by_confidence["high"]),
                    "medium": len(domains_by_confidence["medium"]),
                    "low": len(domains_by_confidence["low"])
                },
                "recent_additions": recent_additions[:20]  # Only return the 20 most recent
            }


# Singleton instance
blacklist_manager = BlacklistManager(CONSOLIDATED_BLACKLIST_FILE) 