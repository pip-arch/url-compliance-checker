from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from enum import Enum

# Import services and models
from app.models.report import ComplianceReport, ReportStatus, URLCategory
from app.core.compliance_checker import generate_report
from app.services.database import database_service

router = APIRouter()

class ListType(str, Enum):
    blacklist = "blacklist"
    whitelist = "whitelist"
    review = "review"

@router.get("/")
async def list_reports(
    batch_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all compliance reports, optionally filtered by batch ID.
    """
    # Get reports from database
    reports = await database_service.get_reports(limit, offset)
    
    # Filter by batch ID if provided
    if batch_id:
        reports = [r for r in reports if r.batch_id == batch_id]
    
    return {
        "reports": [report.dict() for report in reports],
        "total": len(reports),
        "limit": limit,
        "offset": offset
    }

@router.get("/{report_id}")
async def get_report(report_id: str):
    """
    Get a specific compliance report.
    """
    report = await database_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    return report.dict()

@router.get("/{report_id}/urls")
async def get_report_urls(
    report_id: str,
    list_type: Optional[ListType] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get URLs in a specific report, optionally filtered by list type (blacklist, whitelist, review).
    """
    # Check if report exists
    report = await database_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    # Get URL reports
    category = URLCategory[list_type] if list_type else None
    url_reports = await database_service.get_url_reports(report_id, category, limit, offset)
    
    return {
        "report_id": report_id,
        "list_type": list_type,
        "urls": [url_report.dict() for url_report in url_reports],
        "total": len(url_reports),
        "limit": limit,
        "offset": offset
    }

@router.post("/generate")
async def create_report(background_tasks: BackgroundTasks, batch_id: str):
    """
    Generate a compliance report for a specific URL batch.
    """
    # Check if batch exists
    batch = await database_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    # Check if batch processing is complete
    if batch.status != "processed":
        raise HTTPException(
            status_code=400, 
            detail=f"Batch {batch_id} is not fully processed yet (status: {batch.status})"
        )
    
    # Create report ID
    report_id = f"report-{batch_id}"
    
    # Check if report already exists
    existing_report = await database_service.get_report(report_id)
    if existing_report and existing_report.status == ReportStatus.COMPLETED:
        return {
            "message": f"Report for batch {batch_id} already exists",
            "report_id": report_id,
            "status": existing_report.status
        }
    
    # Create initial report record
    report = ComplianceReport(
        id=report_id,
        batch_id=batch_id,
        status=ReportStatus.PENDING,
        total_urls=batch.url_count,
        processed_urls=0
    )
    await database_service.save_report(report)
    
    # Get processed URLs
    urls = await database_service.get_processed_urls_by_batch(batch_id)
    
    # Generate report in the background
    background_tasks.add_task(generate_report, urls, batch_id)
    
    return {
        "message": f"Report generation started for batch {batch_id}",
        "report_id": report_id,
        "status": "pending"
    }

@router.get("/download/{report_id}")
async def download_report(report_id: str, format: str = "csv"):
    """
    Download a compliance report in a specific format (csv, json, pdf).
    """
    # Check if report exists
    report = await database_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    # Check if format is supported
    if format not in ["csv", "json", "pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    # Check if report is complete
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Report {report_id} is not completed yet (status: {report.status})"
        )
    
    # This part will be implemented later to generate actual reports in different formats
    return {
        "message": f"Report {report_id} download in {format} format is not implemented yet",
        "report_id": report_id,
        "format": format
    }

@router.get("/analysis_stats")
async def get_analysis_stats():
    """
    Get statistics about real LLM vs fallback analysis methods used.
    """
    try:
        stats = compliance_checker.get_analysis_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving analysis stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis stats: {str(e)}") 