import os
import csv
import uuid
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from app.api.routes.report_router import router as report_router
from app.api.routes.url_router import router as url_router
from app.api.routes.batch_router import router as batch_router
from app.api.routes.blacklist_router import router as blacklist_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="URL Checker",
    description="A compliance monitoring application for websites mentioning Admiral Markets",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates and static files
templates_dir = os.path.join(os.path.dirname(__file__), "ui", "templates")
static_dir = os.path.join(os.path.dirname(__file__), "ui", "static")

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(report_router, prefix="/api/reports", tags=["reports"])
app.include_router(url_router, prefix="/api/urls", tags=["urls"])
app.include_router(batch_router, prefix="/api/batches", tags=["batches"])
app.include_router(blacklist_router, prefix="/api/blacklist", tags=["blacklist"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main UI page."""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(content=f"<html><body><h1>URL Checker</h1><p>Error loading template: {str(e)}</p></body></html>")

@app.get("/api")
async def api_root():
    """Root endpoint returning API information."""
    return {
        "name": "URL Checker API",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "urls": "/api/urls",
            "reports": "/api/reports",
            "batches": "/api/batches",
            "blacklist": "/api/blacklist",
            "test": "/test-process-file",
            "test-integration": "/test-integration"
        }
    }

@app.get("/urls")
async def urls_endpoint():
    """Temporary endpoint for testing."""
    return {
        "urls": [
            {"id": "test-1", "url": "https://example.com", "status": "pending"},
            {"id": "test-2", "url": "https://test.com", "status": "processed"}
        ]
    }

@app.get("/test-process-file")
async def test_process_file():
    """
    Test endpoint to process the sample URL file directly.
    This bypasses the UI upload and directly processes our test file.
    """
    try:
        # Path to the sample CSV file
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples", "test_urls.csv")
        
        if not os.path.exists(csv_path):
            return {"error": f"Sample file not found at {csv_path}"}
        
        # Read URLs from the CSV
        urls = []
        with open(csv_path, "r") as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header row
            for row in csv_reader:
                if row and row[0]:
                    urls.append(row[0])
        
        # Create a batch ID
        batch_id = str(uuid.uuid4())
        
        # Process the URLs (in a real implementation, this would use our URL processor)
        # For now, just return the URLs we found
        return {
            "message": f"Processed {len(urls)} URLs",
            "batch_id": batch_id,
            "urls": urls,
            "status": "success",
            "sample_file": csv_path
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-integration")
async def test_integration(url: str = None):
    """
    Test endpoint to verify integration with Pinecone, Firecrawl, and OpenRouter.
    This tests all the main services we've implemented.
    
    Parameters:
    - url: Optional custom URL to test with. If not provided, a mock URL will be used.
    """
    try:
        # Import services
        from app.services.crawler import crawler_service
        from app.services.vector_db import pinecone_service
        from app.services.ai import ai_service
        
        # Test URL (use provided URL or default to mock example)
        test_url = url if url and url.startswith("http") else "https://blog.example.com/review-of-admiralmarkets-trading"
        
        results = {}
        
        # Step 1: Test Firecrawl/Web Crawler Service
        logger.info(f"Testing web crawler service with URL: {test_url}...")
        crawler_result = await crawler_service.crawl(test_url)
        results["crawler"] = {
            "status": "success" if crawler_result.get("title") is not None else "error",
            "details": {
                "title": crawler_result.get("title"),
                "content_length": len(crawler_result.get("full_text", "")) if crawler_result.get("full_text") else 0,
                "crawled_with": crawler_result.get("metadata", {}).get("crawled_with", "unknown")
            }
        }
        
        # Only continue if crawler was successful
        if results["crawler"]["status"] == "success":
            # Create a mock URLContent with a mention of "admiralmarkets"
            from app.models.url import URLContent, URLContentMatch
            from datetime import datetime
            
            url_content = URLContent(
                url=test_url,
                title=crawler_result.get("title", "Test Title"),
                full_text=crawler_result.get("full_text", "This is a test with admiralmarkets mentioned."),
                crawled_at=datetime.now(),
                metadata=crawler_result.get("metadata", {})
            )
            
            # Extract the mention (simplistic version of what the actual processor does)
            mention_text = "admiralmarkets"
            if mention_text in url_content.full_text.lower():
                position = url_content.full_text.lower().find(mention_text)
                context_start = max(0, position - 100)
                context_end = min(len(url_content.full_text), position + len(mention_text) + 100)
                
                url_content.mentions.append(URLContentMatch(
                    text=mention_text,
                    position=position,
                    context_before=url_content.full_text[context_start:position],
                    context_after=url_content.full_text[position + len(mention_text):context_end]
                ))
            
            # Step 2: Test Pinecone Vector DB Service
            logger.info("Testing Pinecone vector DB service...")
            if pinecone_service.is_initialized:
                pinecone_result = await pinecone_service.store_content(url_content)
                results["pinecone"] = {
                    "status": "success" if pinecone_result else "error",
                    "details": {
                        "embeddings_stored": len(pinecone_result),
                        "embedding_ids": list(pinecone_result.values())
                    }
                }
            else:
                results["pinecone"] = {
                    "status": "error",
                    "details": {
                        "error": "Pinecone service not initialized"
                    }
                }
            
            # Step 3: Test OpenRouter AI Service
            logger.info("Testing OpenRouter AI service...")
            if ai_service.is_initialized:
                ai_result = await ai_service.analyze_content(url_content)
                results["openrouter"] = {
                    "status": "success" if ai_result else "error",
                    "details": {
                        "model": ai_result.model,
                        "category": ai_result.category.value if hasattr(ai_result.category, 'value') else str(ai_result.category),
                        "confidence": ai_result.confidence,
                        "explanation": ai_result.explanation,
                        "is_mock": ai_result.model == "mock-model"
                    }
                }
            else:
                results["openrouter"] = {
                    "status": "error",
                    "details": {
                        "error": "OpenRouter service not initialized"
                    }
                }
        
        # Return overall results
        return {
            "message": "Integration test completed",
            "test_url": test_url,
            "results": results,
            "status": "success" if all(r["status"] == "success" for r in results.values()) else "partial_success"
        }
        
    except Exception as e:
        logger.exception("Error in integration test")
        return {
            "error": str(e),
            "status": "error",
            "details": {
                "traceback": str(e)
            }
        }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    ) 