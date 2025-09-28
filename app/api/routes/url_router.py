from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import csv
import io
import uuid
from datetime import datetime
import logging

# Import processor and models
from app.core.url_processor import process_urls
from app.models.url import URLBatch, URLStatus
from app.services.database import database_service

router = APIRouter()

@router.post("/upload")
async def upload_urls(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
):
    """
    Upload a CSV file containing URLs for compliance checking.
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    # Read and validate CSV content
    try:
        contents = await file.read()
        file_content = io.StringIO(contents.decode("utf-8"))
        csv_reader = csv.reader(file_content)
        urls = [row[0] for row in csv_reader if row]  # Assuming first column contains URLs
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")
    
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs found in the CSV file")
    
    # Create a unique batch ID for this upload
    batch_id = str(uuid.uuid4())
    
    # Store batch metadata
    batch = URLBatch(
        id=batch_id,
        description=description,
        filename=file.filename,
        url_count=len(urls),
        processed_count=0,
        status=URLStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await database_service.save_batch(batch)
    
    # Process the URLs in the background
    background_tasks.add_task(process_urls, urls, batch_id)
    
    return {
        "message": f"Successfully uploaded {len(urls)} URLs for processing",
        "batch_id": batch_id,
        "status": "pending"
    }

@router.get("/batches")
async def list_batches(limit: int = 100, offset: int = 0):
    """
    List all URL batches that have been uploaded.
    """
    batches = await database_service.get_all_batches(limit, offset)
    return {"batches": [batch.dict() for batch in batches]}

@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str):
    """
    Get information about a specific URL batch.
    """
    batch = await database_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    return batch.dict()

@router.get("/batches/{batch_id}/urls")
async def get_batch_urls(batch_id: str, limit: int = 100, offset: int = 0):
    """
    Get all URLs in a specific batch.
    """
    logger = logging.getLogger(__name__)
    # Check if batch exists
    batch = await database_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    try:
        # Get URLs for batch
        urls = await database_service.get_urls_by_batch(batch_id, limit, offset)
        return {
            "batch_id": batch_id,
            "urls": [url.dict() for url in urls],
            "total": batch.url_count,
            "processed": batch.processed_count
        }
    except Exception as e:
        logger.error(f"Error fetching URLs for batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str):
    """
    Delete a specific URL batch.
    """
    # Check if batch exists
    batch = await database_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    # Delete batch
    success = await database_service.delete_batch(batch_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete batch {batch_id}")
    
    return {"message": f"Batch {batch_id} deleted"} 