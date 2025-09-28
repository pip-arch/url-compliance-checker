#!/usr/bin/env python3
"""
Fix script for Firecrawl API integration issues.
This script checks and fixes common issues with Firecrawl API integration.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/logs/firecrawl_fix.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Check for required file paths first
def check_file_paths():
    """Check if required file paths exist in the codebase."""
    critical_paths = [
        "app/core/url_processor.py",
        "app/services/crawlers/firecrawl_service.py",
    ]
    
    missing_files = []
    for path in critical_paths:
        if not os.path.exists(path):
            missing_files.append(path)
    
    if missing_files:
        logger.warning(f"Missing critical files: {', '.join(missing_files)}")
        return False
    
    return True

def find_firecrawl_code():
    """Find occurrences of Firecrawl API in the codebase."""
    import glob
    
    firecrawl_files = []
    
    # Look for Python files that might contain Firecrawl API calls
    patterns = [
        "app/**/*.py",
        "scripts/**/*.py",
    ]
    
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "firecrawl" in content.lower() or "FirecrawlApp" in content or "api.firecrawl.dev" in content:
                    firecrawl_files.append(file_path)
    
    return firecrawl_files

def check_env_file():
    """Check if .env file has Firecrawl API key."""
    env_file = ".env"
    if not os.path.exists(env_file):
        logger.warning(f"{env_file} file not found.")
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "FIRECRAWL_API_KEY" not in content:
        logger.warning("FIRECRAWL_API_KEY not found in .env file.")
        return False
    
    # Check if API key is empty
    import re
    match = re.search(r'FIRECRAWL_API_KEY=([^\n]*)', content)
    if match and not match.group(1).strip():
        logger.warning("FIRECRAWL_API_KEY is empty in .env file.")
        return False
    
    return True

def fix_env_file():
    """Add Firecrawl API key placeholder to .env file if not present."""
    env_file = ".env"
    
    # Create .env file if it doesn't exist
    if not os.path.exists(env_file):
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("# URL-checker environment variables\n\n")
    
    # Read current content
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add Firecrawl API key if not present
    if "FIRECRAWL_API_KEY" not in content:
        with open(env_file, 'a', encoding='utf-8') as f:
            f.write("\n# Firecrawl API configuration\n")
            f.write("FIRECRAWL_API_KEY=\n")
            f.write("FIRECRAWL_API_URL=https://api.firecrawl.dev/v1/scrape\n")
            f.write("FIRECRAWL_TIMEOUT=30\n")
            f.write("USE_MOCK_PERCENTAGE=0\n")
        
        logger.info("Added Firecrawl API configuration to .env file.")
    
    return True

def check_firecrawl_service(path="app/services/crawlers/firecrawl_service.py"):
    """Check if Firecrawl service file exists and has proper authentication."""
    if not os.path.exists(path):
        logger.warning(f"Firecrawl service file not found at {path}")
        return False
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # Check for Bearer token
    if "Bearer" not in content:
        issues.append("Bearer token authentication not found")
    
    # Check for proper error handling
    if "MAX_RETRY_COUNT" not in content:
        issues.append("Retry logic not found")
    
    # Check for timeout handling
    if "FIRECRAWL_TIMEOUT" not in content:
        issues.append("Timeout handling not found")
    
    if issues:
        logger.warning(f"Issues found in Firecrawl service: {', '.join(issues)}")
        return False
    
    return True

def create_firecrawl_service(path="app/services/crawlers/firecrawl_service.py"):
    """Create or update Firecrawl service file with proper implementation."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    service_code = """#!/usr/bin/env python3
\"\"\"
Firecrawl API service for web crawling with JavaScript support.
This service handles authentication, request formatting, and response parsing.
\"\"\"

import os
import json
import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class FirecrawlService:
    \"\"\"Service for interacting with the Firecrawl API.\"\"\"
    
    def __init__(self):
        \"\"\"Initialize the Firecrawl service.\"\"\"
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
        self.timeout = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRY_COUNT", "3"))
        
        # Validate API key
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY environment variable not set. Firecrawl API will not work.")
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        \"\"\"
        Scrape a URL using Firecrawl API.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the response data or error information
        \"\"\"
        if not self.api_key:
            logger.error("Cannot scrape URL: FIRECRAWL_API_KEY not set")
            return {
                "success": False,
                "error": "API key not configured",
                "error_type": "configuration"
            }
        
        # Set up request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["markdown", "html"],
            "timeout": self.timeout * 1000  # Convert to milliseconds
        }
        
        # Initialize retry counter
        retry_count = 0
        
        while retry_count <= self.max_retries:
            if retry_count > 0:
                # Calculate backoff time (exponential backoff)
                backoff_time = 2 ** retry_count
                logger.info(f"Retrying request ({retry_count}/{self.max_retries}) after {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            
            try:
                async with aiohttp.ClientSession() as session:
                    start_time = datetime.now()
                    
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout + 5  # Add 5 seconds buffer
                    ) as response:
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        # Read response
                        response_text = await response.text()
                        status_code = response.status
                        
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse Firecrawl response as JSON. Status: {status_code}")
                            
                            # Only retry on server errors or timeout
                            if status_code >= 500 or status_code == 408:
                                retry_count += 1
                                continue
                                
                            return {
                                "success": False,
                                "status_code": status_code,
                                "duration": duration,
                                "error": "Invalid JSON response",
                                "error_type": "parsing"
                            }
                        
                        # Check if successful
                        if status_code == 200 and response_json.get("success", False):
                            logger.info(f"Firecrawl request successful: {url} (Duration: {duration:.2f}s)")
                            
                            # Add duration and status code to response
                            response_json["duration"] = duration
                            response_json["status_code"] = status_code
                            
                            return response_json
                        
                        # Handle rate limiting
                        if status_code == 429:
                            logger.warning(f"Firecrawl rate limit hit for {url}. Retrying...")
                            retry_count += 1
                            continue
                        
                        # Handle server errors
                        if status_code >= 500:
                            logger.warning(f"Firecrawl server error ({status_code}) for {url}. Retrying...")
                            retry_count += 1
                            continue
                        
                        # Handle other errors (client errors, etc.)
                        logger.error(f"Firecrawl request failed: {url}, Status: {status_code}")
                        return {
                            "success": False,
                            "status_code": status_code,
                            "duration": duration,
                            "error": response_json.get("error", "Unknown error"),
                            "error_type": "api_error"
                        }
                        
            except aiohttp.ClientError as e:
                logger.error(f"Firecrawl connection error for {url}: {str(e)}")
                retry_count += 1
                continue
                
            except asyncio.TimeoutError:
                logger.error(f"Firecrawl request timed out for {url} after {self.timeout} seconds")
                retry_count += 1
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error during Firecrawl request for {url}: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": "unexpected"
                }
        
        # If we get here, we've exhausted all retries
        logger.error(f"Failed to scrape {url} after {self.max_retries} retries")
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} retries",
            "error_type": "max_retries"
        }
    
    async def extract_content(self, url: str) -> Dict[str, Union[bool, str, Dict[str, Any]]]:
        \"\"\"
        Extract content from a URL using Firecrawl API.
        This is a convenience method that returns a simplified response.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the extracted content or error information
        \"\"\"
        response = await self.scrape_url(url)
        
        if not response.get("success", False):
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "url": url
            }
        
        data = response.get("data", {})
        markdown = data.get("markdown", "")
        html = data.get("html", "")
        metadata = data.get("metadata", {})
        
        return {
            "success": True,
            "url": url,
            "markdown": markdown,
            "html": html,
            "metadata": metadata,
            "duration": response.get("duration", 0)
        }
"""
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(service_code)
    
    logger.info(f"Created/updated Firecrawl service at {path}")
    return True

def fix_url_processor(path="app/core/url_processor.py"):
    """Check and fix URL processor to properly use Firecrawl service."""
    if not os.path.exists(path):
        logger.warning(f"URL processor file not found at {path}")
        return False
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if we need to fix the import
    firecrawl_import_missing = "from app.services.crawlers.firecrawl_service import FirecrawlService" not in content
    
    if firecrawl_import_missing:
        logger.warning("Firecrawl service import not found in URL processor")
        # We would need to check and modify the URL processor, but this is complex and risky
        # It's better to generate a diagnostic report
        return False
    
    return True

async def test_end_to_end(url="https://example.com"):
    """Test end-to-end Firecrawl integration."""
    # This would import the actual app code and test it
    # However, this is complex and might require more context about the codebase
    # For now, let's just use our test script
    
    # Run the diagnostic script
    test_script = "scripts/diagnostic/test_firecrawl_connection.py"
    if os.path.exists(test_script):
        logger.info(f"Running Firecrawl test script with URL: {url}")
        import subprocess
        result = subprocess.run([sys.executable, test_script, "--url", url], capture_output=True, text=True)
        
        logger.info(f"Test script exit code: {result.returncode}")
        logger.info(f"Test script output:\n{result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"Test script errors:\n{result.stderr}")
            return False
        
        return True
    else:
        logger.warning(f"Test script not found at {test_script}")
        return False

def generate_report(issues, firecrawl_files):
    """Generate a report of issues and fixes."""
    report = []
    report.append("\n" + "="*80)
    report.append("FIRECRAWL INTEGRATION DIAGNOSTIC REPORT")
    report.append("="*80 + "\n")
    
    # Issues summary
    if issues:
        report.append("ISSUES FOUND:")
        for issue in issues:
            report.append(f"- {issue}")
    else:
        report.append("✅ No issues found!")
    
    report.append("\nFIRECRAWL FILES FOUND:")
    if firecrawl_files:
        for file in firecrawl_files:
            report.append(f"- {file}")
    else:
        report.append("- No Firecrawl-related files found.")
    
    report.append("\nRECOMMENDED ACTIONS:")
    if issues:
        report.append("1. Add FIRECRAWL_API_KEY to your .env file")
        report.append("2. Run the diagnostic script: python scripts/diagnostic/test_firecrawl_connection.py")
        report.append("3. Check Firecrawl service implementation")
    else:
        report.append("1. Run the diagnostic script to verify everything works")
        report.append("2. Update your API key if needed")
    
    report.append("\n" + "="*80)
    
    return "\n".join(report)

async def main():
    """Run the Firecrawl fixing script."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Fix Firecrawl API integration issues')
    parser.add_argument('--fix', action='store_true', help='Apply fixes automatically')
    parser.add_argument('--test', action='store_true', help='Run test after fixing')
    parser.add_argument('--test-url', default="https://example.com", help='URL to use for testing')
    args = parser.parse_args()
    
    # Make the directory for logs if it doesn't exist
    os.makedirs("data/logs", exist_ok=True)
    
    logger.info("Starting Firecrawl integration diagnosis")
    
    # List to collect issues
    issues = []
    
    # Step 1: Check file paths
    if not check_file_paths():
        issues.append("Missing critical files")
    
    # Step 2: Find Firecrawl code
    firecrawl_files = find_firecrawl_code()
    if not firecrawl_files:
        issues.append("No Firecrawl-related code found in codebase")
    
    # Step 3: Check .env file
    if not check_env_file():
        issues.append("Firecrawl API key not configured in .env file")
        if args.fix:
            fix_env_file()
    
    # Step 4: Check Firecrawl service
    if not check_firecrawl_service():
        issues.append("Firecrawl service has issues or is missing")
        if args.fix:
            create_firecrawl_service()
    
    # Step 5: Check URL processor
    if not fix_url_processor():
        issues.append("URL processor may need manual review for Firecrawl integration")
    
    # Step 6: Test if requested
    if args.test:
        logger.info(f"Testing Firecrawl integration with URL: {args.test_url}")
        if not await test_end_to_end(args.test_url):
            issues.append("End-to-end test failed")
    
    # Generate and print report
    report = generate_report(issues, firecrawl_files)
    print(report)
    
    if issues and not args.fix:
        logger.info("Run with --fix to automatically fix issues")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 