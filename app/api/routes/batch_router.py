"""
API routes for batch processing of URLs.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from app.models.url import URLBatchCreate, URLBatchResponse, URLStatus
from app.core.batch_processor import batch_processor
from app.services.failed_url_service import failed_url_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# In-memory storage for batch status (in a real app, this would be in a database)
batch_status = {}

class BatchProcessRequest(BaseModel):
    """Request model for batch processing."""
    urls: List[str]
    description: Optional[str] = None
    max_concurrent_requests: Optional[int] = None
    

class FailedURLsRequest(BaseModel):
    """Request model for retrieving failed URLs."""
    batch_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class RetryURLRequest(BaseModel):
    """Request model for retrying a failed URL."""
    url_id: str


class MarkReviewedRequest(BaseModel):
    """Request model for marking a failed URL as reviewed."""
    url_id: str
    notes: Optional[str] = None


@router.post("/process", response_model=URLBatchResponse)
async def process_batch(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a batch of URLs.
    The processing will happen in the background.
    """
    logger.info(f"Received request to process {len(request.urls)} URLs")
    
    # Generate batch ID
    batch_id = str(uuid.uuid4())
    
    # Set initial batch status
    batch_status[batch_id] = {
        "status": URLStatus.PENDING,
        "url_count": len(request.urls),
        "processed_count": 0,
        "description": request.description
    }
    
    # Start batch processing in the background
    background_tasks.add_task(
        _process_batch_task,
        batch_id=batch_id,
        urls=request.urls,
        max_concurrent_requests=request.max_concurrent_requests
    )
    
    return URLBatchResponse(
        batch_id=batch_id,
        message=f"Processing {len(request.urls)} URLs in the background",
        status=URLStatus.PENDING
    )


@router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status of a batch processing task."""
    if batch_id not in batch_status:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    return batch_status[batch_id]


@router.post("/failed-urls")
async def get_failed_urls(request: FailedURLsRequest):
    """Get failed URLs for review."""
    failed_urls = await failed_url_service.get_failed_urls(
        batch_id=request.batch_id,
        limit=request.limit,
        offset=request.offset
    )
    
    return {
        "count": len(failed_urls),
        "failed_urls": failed_urls
    }


@router.post("/retry")
async def retry_url(
    request: RetryURLRequest,
    background_tasks: BackgroundTasks
):
    """Retry a failed URL."""
    url_data = await failed_url_service.retry_failed_url(request.url_id)
    
    if not url_data:
        raise HTTPException(status_code=404, detail=f"Failed URL {request.url_id} not found")
    
    # Generate new batch ID for retrying
    retry_batch_id = str(uuid.uuid4())
    
    # Start batch processing for just this URL
    background_tasks.add_task(
        _process_batch_task,
        batch_id=retry_batch_id,
        urls=[url_data["url"]]
    )
    
    return {
        "message": f"Retrying URL {url_data['url']}",
        "batch_id": retry_batch_id,
        "url_id": request.url_id
    }


@router.post("/mark-reviewed")
async def mark_as_reviewed(request: MarkReviewedRequest):
    """Mark a failed URL as reviewed."""
    success = await failed_url_service.mark_as_reviewed(
        url_id=request.url_id,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Failed URL {request.url_id} not found")
    
    return {
        "message": f"URL {request.url_id} marked as reviewed"
    }


@router.get("/export-failed/{batch_id}")
async def export_failed_urls(
    batch_id: str,
    format: str = Query("json", regex="^(json|csv)$")
):
    """Export failed URLs to a file."""
    export_path = await failed_url_service.export_failed_urls(
        batch_id=batch_id,
        format=format
    )
    
    if not export_path:
        raise HTTPException(status_code=404, detail=f"No failed URLs found for batch {batch_id}")
    
    return {
        "message": f"Failed URLs exported to {export_path}",
        "export_path": export_path,
        "format": format
    }


async def _process_batch_task(batch_id: str, urls: List[str], max_concurrent_requests: Optional[int] = None):
    """Background task for processing a batch of URLs."""
    logger.info(f"Starting background task for batch {batch_id} with {len(urls)} URLs")
    
    # Update batch status
    batch_status[batch_id] = {
        **batch_status.get(batch_id, {}),
        "status": URLStatus.PROCESSING,
        "url_count": len(urls),
        "start_time": str(datetime.now())
    }
    
    # Process the batch
    try:
        stats = await batch_processor.process_batch(batch_id, urls)
        
        # Update batch status with results
        batch_status[batch_id] = {
            **batch_status[batch_id],
            "status": URLStatus.PROCESSED,
            "processed_count": stats["processed"],
            "successful_count": stats["successful"],
            "failed_count": stats["failed"],
            "skipped_count": stats["skipped"],
            "filtered_count": stats["filtered"],
            "filter_reasons": stats["filter_reasons"],
            "duration_seconds": stats["duration_seconds"],
            "urls_per_second": stats["urls_per_second"],
            "end_time": str(stats["end_time"]),
            "failed_url_count": len(stats["failed_urls"])
        }
        
        logger.info(f"Batch {batch_id} processing completed successfully")
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")
        
        # Update batch status with error
        batch_status[batch_id] = {
            **batch_status[batch_id],
            "status": URLStatus.FAILED,
            "error": str(e)
        } 