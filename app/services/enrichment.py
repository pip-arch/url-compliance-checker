"""
Enrichment service for adding supplementary data to URLs.
Provides screenshots, domain info, SSL checks, and more.
"""
import os
import ssl
import socket
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import whois
import dns.resolver
from playwright.async_api import async_playwright
import aiohttp
import certifi
from PIL import Image
import io

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Service for enriching URLs with additional data."""
    
    def __init__(self):
        """Initialize the enrichment service."""
        self.screenshot_dir = "data/outputs/screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.playwright = None
        self.browser = None
        
    async def initialize(self):
        """Initialize Playwright for screenshots."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Enrichment service initialized with Playwright")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def enrich_url(self, url: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich a URL with additional data.
        
        Returns:
            Dict containing:
            - screenshot_path: Path to screenshot
            - domain_info: WHOIS data, DNS records
            - ssl_info: SSL certificate details
            - technology_stack: Detected technologies
            - performance_metrics: Load time, size
            - security_headers: Security header analysis
        """
        enrichment_data = {
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screenshot_path": None,
            "domain_info": {},
            "ssl_info": {},
            "technology_stack": [],
            "performance_metrics": {},
            "security_headers": {},
            "visual_analysis": {}
        }
        
        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Run enrichment tasks concurrently
        tasks = [
            self._capture_screenshot(url),
            self._get_domain_info(domain),
            self._check_ssl(domain),
            self._analyze_security_headers(url),
            self._detect_technologies(url, content)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        if not isinstance(results[0], Exception):
            enrichment_data["screenshot_path"] = results[0]
            enrichment_data["visual_analysis"] = await self._analyze_screenshot(results[0])
        
        if not isinstance(results[1], Exception):
            enrichment_data["domain_info"] = results[1]
        
        if not isinstance(results[2], Exception):
            enrichment_data["ssl_info"] = results[2]
        
        if not isinstance(results[3], Exception):
            enrichment_data["security_headers"] = results[3]
        
        if not isinstance(results[4], Exception):
            enrichment_data["technology_stack"] = results[4]
        
        return enrichment_data
    
    async def _capture_screenshot(self, url: str) -> Optional[str]:
        """Capture a screenshot of the URL."""
        if not self.browser:
            await self.initialize()
        
        if not self.browser:
            logger.warning("Browser not available for screenshots")
            return None
        
        try:
            page = await self.browser.new_page()
            
            # Set viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate with timeout
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit for dynamic content
            await asyncio.sleep(2)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = urlparse(url).netloc.replace(".", "_")
            filename = f"{domain}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Take screenshot
            await page.screenshot(path=filepath, full_page=True)
            
            await page.close()
            
            logger.info(f"Screenshot captured for {url}: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot for {url}: {e}")
            return None
    
    async def _get_domain_info(self, domain: str) -> Dict[str, Any]:
        """Get domain information including WHOIS and DNS records."""
        domain_info = {
            "whois": {},
            "dns": {},
            "age_days": None,
            "registrar": None,
            "name_servers": []
        }
        
        try:
            # WHOIS lookup
            w = whois.whois(domain)
            if w:
                domain_info["whois"] = {
                    "registrar": w.registrar,
                    "creation_date": str(w.creation_date) if w.creation_date else None,
                    "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                    "name_servers": w.name_servers if w.name_servers else []
                }
                
                # Calculate domain age
                if w.creation_date:
                    if isinstance(w.creation_date, list):
                        creation_date = w.creation_date[0]
                    else:
                        creation_date = w.creation_date
                    
                    if hasattr(creation_date, 'date'):
                        age = datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)
                        domain_info["age_days"] = age.days
                
                domain_info["registrar"] = w.registrar
                domain_info["name_servers"] = w.name_servers if w.name_servers else []
        except Exception as e:
            logger.warning(f"WHOIS lookup failed for {domain}: {e}")
        
        try:
            # DNS lookups
            resolver = dns.resolver.Resolver()
            
            # A records
            try:
                a_records = resolver.resolve(domain, 'A')
                domain_info["dns"]["a_records"] = [str(r) for r in a_records]
            except:
                pass
            
            # MX records
            try:
                mx_records = resolver.resolve(domain, 'MX')
                domain_info["dns"]["mx_records"] = [f"{r.preference} {r.exchange}" for r in mx_records]
            except:
                pass
            
            # TXT records
            try:
                txt_records = resolver.resolve(domain, 'TXT')
                domain_info["dns"]["txt_records"] = [str(r) for r in txt_records]
            except:
                pass
                
        except Exception as e:
            logger.warning(f"DNS lookup failed for {domain}: {e}")
        
        return domain_info
    
    async def _check_ssl(self, domain: str) -> Dict[str, Any]:
        """Check SSL certificate information."""
        ssl_info = {
            "valid": False,
            "issuer": None,
            "subject": None,
            "not_before": None,
            "not_after": None,
            "days_remaining": None,
            "san": [],
            "issues": []
        }
        
        try:
            # Create SSL context
            context = ssl.create_default_context(cafile=certifi.where())
            
            # Connect and get certificate
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    ssl_info["valid"] = True
                    ssl_info["issuer"] = dict(x[0] for x in cert['issuer'])
                    ssl_info["subject"] = dict(x[0] for x in cert['subject'])
                    
                    # Parse dates
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    
                    ssl_info["not_before"] = not_before.isoformat()
                    ssl_info["not_after"] = not_after.isoformat()
                    
                    # Calculate days remaining
                    days_remaining = (not_after - datetime.now()).days
                    ssl_info["days_remaining"] = days_remaining
                    
                    if days_remaining < 30:
                        ssl_info["issues"].append(f"Certificate expires in {days_remaining} days")
                    
                    # Subject Alternative Names
                    if 'subjectAltName' in cert:
                        ssl_info["san"] = [x[1] for x in cert['subjectAltName']]
                    
        except ssl.SSLError as e:
            ssl_info["valid"] = False
            ssl_info["issues"].append(f"SSL Error: {str(e)}")
        except Exception as e:
            ssl_info["valid"] = False
            ssl_info["issues"].append(f"Connection Error: {str(e)}")
        
        return ssl_info
    
    async def _analyze_security_headers(self, url: str) -> Dict[str, Any]:
        """Analyze security headers of the URL."""
        security_headers = {
            "score": 0,
            "headers_present": [],
            "headers_missing": [],
            "issues": []
        }
        
        important_headers = {
            "Strict-Transport-Security": "HSTS",
            "X-Content-Type-Options": "X-Content-Type-Options",
            "X-Frame-Options": "X-Frame-Options",
            "Content-Security-Policy": "CSP",
            "X-XSS-Protection": "XSS Protection",
            "Referrer-Policy": "Referrer Policy"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=10) as response:
                    headers = response.headers
                    
                    # Check for important security headers
                    for header, name in important_headers.items():
                        if header in headers:
                            security_headers["headers_present"].append(name)
                            security_headers["score"] += 1
                        else:
                            security_headers["headers_missing"].append(name)
                            security_headers["issues"].append(f"Missing {name} header")
                    
                    # Calculate score percentage
                    security_headers["score"] = (security_headers["score"] / len(important_headers)) * 100
                    
        except Exception as e:
            logger.warning(f"Failed to analyze security headers for {url}: {e}")
            security_headers["issues"].append(f"Analysis failed: {str(e)}")
        
        return security_headers
    
    async def _detect_technologies(self, url: str, content: Optional[str] = None) -> List[str]:
        """Detect technologies used by the website."""
        technologies = []
        
        try:
            # Simple technology detection based on headers and content
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    headers = response.headers
                    
                    # Server detection
                    if 'Server' in headers:
                        technologies.append(f"Server: {headers['Server']}")
                    
                    # Powered by
                    if 'X-Powered-By' in headers:
                        technologies.append(f"Powered by: {headers['X-Powered-By']}")
                    
                    # Content analysis if available
                    if content:
                        # WordPress
                        if 'wp-content' in content or 'wordpress' in content.lower():
                            technologies.append("CMS: WordPress")
                        
                        # React
                        if 'react' in content.lower() or '_react' in content:
                            technologies.append("Framework: React")
                        
                        # Angular
                        if 'ng-' in content or 'angular' in content.lower():
                            technologies.append("Framework: Angular")
                        
                        # jQuery
                        if 'jquery' in content.lower():
                            technologies.append("Library: jQuery")
                        
                        # Bootstrap
                        if 'bootstrap' in content.lower():
                            technologies.append("Framework: Bootstrap")
                        
                        # Google Analytics
                        if 'google-analytics.com' in content or 'gtag(' in content:
                            technologies.append("Analytics: Google Analytics")
                        
        except Exception as e:
            logger.warning(f"Failed to detect technologies for {url}: {e}")
        
        return technologies
    
    async def _analyze_screenshot(self, screenshot_path: Optional[str]) -> Dict[str, Any]:
        """Analyze screenshot for visual elements."""
        if not screenshot_path or not os.path.exists(screenshot_path):
            return {}
        
        visual_analysis = {
            "has_logo": False,
            "dominant_colors": [],
            "image_dimensions": None,
            "file_size_kb": 0
        }
        
        try:
            # Get file size
            visual_analysis["file_size_kb"] = os.path.getsize(screenshot_path) / 1024
            
            # Open and analyze image
            with Image.open(screenshot_path) as img:
                visual_analysis["image_dimensions"] = f"{img.width}x{img.height}"
                
                # Get dominant colors (simplified)
                img_small = img.resize((150, 150))
                colors = img_small.getcolors(maxcolors=10000)
                if colors:
                    # Sort by frequency and get top 5
                    sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:5]
                    visual_analysis["dominant_colors"] = [
                        f"rgb{color[1][:3]}" for color in sorted_colors
                    ]
                
        except Exception as e:
            logger.warning(f"Failed to analyze screenshot {screenshot_path}: {e}")
        
        return visual_analysis


# Singleton instance
enrichment_service = EnrichmentService() 