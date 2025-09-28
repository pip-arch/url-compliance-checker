from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

# Import services and models
from app.core.blacklist_manager import blacklist_manager
from app.models.report import URLCategory

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

class ExportFormat(str, Enum):
    csv = "csv"
    json = "json"
    txt = "txt"

@router.get("/")
async def get_blacklist_overview():
    """
    Get overview of the blacklist with analytics.
    """
    try:
        analytics = await blacklist_manager.get_blacklist_analytics()
        return {
            "status": "success",
            "data": analytics
        }
    except Exception as e:
        logger.error(f"Error retrieving blacklist analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve blacklist analytics: {str(e)}")

@router.get("/domains")
async def get_blacklisted_domains(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
):
    """
    Get list of blacklisted domains with their metadata.
    """
    try:
        blacklist = await blacklist_manager.get_blacklist()
        
        # Filter by confidence if specified
        if min_confidence > 0:
            blacklist = {
                domain: info for domain, info in blacklist.items() 
                if info.get("confidence", 0) >= min_confidence
            }
        
        # Sort by confidence (highest first)
        sorted_domains = sorted(
            blacklist.items(), 
            key=lambda x: x[1].get("confidence", 0), 
            reverse=True
        )
        
        # Apply pagination
        paginated = sorted_domains[offset:offset + limit]
        
        # Convert sets to lists for JSON serialization
        results = []
        for domain, info in paginated:
            domain_info = {
                "domain": domain,
                "urls": info.get("urls", []),
                "reasons": list(info.get("reasons", set())),
                "categories": list(info.get("categories", set())),
                "confidence": info.get("confidence", 0.0),
                "compliance_issues": list(info.get("compliance_issues", set())),
                "violation_count": info.get("violation_count", 1),
                "first_added": info.get("first_added", ""),
            }
            results.append(domain_info)
        
        return {
            "status": "success",
            "total": len(blacklist),
            "filtered": len(results),
            "limit": limit,
            "offset": offset,
            "data": results
        }
    except Exception as e:
        logger.error(f"Error retrieving blacklisted domains: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve blacklisted domains: {str(e)}")

@router.get("/domain/{domain}")
async def get_domain_reputation(domain: str):
    """
    Get detailed reputation data for a specific domain.
    """
    try:
        reputation = await blacklist_manager.get_domain_reputation(domain)
        return {
            "status": "success",
            "data": reputation
        }
    except Exception as e:
        logger.error(f"Error retrieving domain reputation for {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve domain reputation: {str(e)}")

@router.post("/domain/{domain}")
async def add_domain_to_blacklist(
    domain: str,
    reason: str = "Manual addition",
    confidence: float = 0.9,
    category: str = "blacklist",
    compliance_issues: Optional[List[str]] = None
):
    """
    Manually add a domain to the blacklist.
    """
    try:
        # Construct a dummy URL from the domain
        url = f"https://{domain}"
        
        # Add to blacklist
        result = await blacklist_manager.add_to_blacklist(
            url=url,
            reason=reason,
            confidence=confidence,
            category=category,
            compliance_issues=compliance_issues or ["Manual blacklisting"]
        )
        
        return {
            "status": "success",
            "newly_blacklisted": result,
            "domain": domain,
            "message": "Domain successfully added to blacklist" if result else "Domain was already blacklisted"
        }
    except Exception as e:
        logger.error(f"Error adding domain {domain} to blacklist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add domain to blacklist: {str(e)}")

@router.get("/export")
async def export_blacklist(
    format_type: ExportFormat = ExportFormat.csv,
    background_tasks: BackgroundTasks = None
):
    """
    Export the blacklist to a file in the specified format.
    """
    try:
        # Export in background if background_tasks provided
        if background_tasks:
            path_future = []
            
            async def export_and_save_path():
                path = await blacklist_manager.export_blacklist(format_type=format_type.value)
                path_future.append(path)
                logger.info(f"Blacklist exported to {path}")
            
            background_tasks.add_task(export_and_save_path)
            
            return {
                "status": "success",
                "message": f"Blacklist export started with format: {format_type.value}",
                "background": True
            }
        
        # Export synchronously otherwise
        output_path = await blacklist_manager.export_blacklist(format_type=format_type.value)
        
        return {
            "status": "success",
            "message": f"Blacklist exported successfully",
            "format": format_type.value,
            "file_path": output_path
        }
    except Exception as e:
        logger.error(f"Error exporting blacklist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export blacklist: {str(e)}") 