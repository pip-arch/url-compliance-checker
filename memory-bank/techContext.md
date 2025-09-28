# Technical Context

## Technologies Used

### Backend
- **Python 3.10+**: Core programming language
- **FastAPI**: Web framework for building APIs
- **Pydantic**: Data validation and settings management
- **SQLAlchemy**: ORM for database interactions
- **Alembic**: Database migration tool
- **Uvicorn**: ASGI server for running the application
- **Poetry**: Dependency management

### Web Crawling & Content Processing
- **Firecrawl API**: External service for web crawling with JavaScript support
  - **CRITICAL**: Must use for real content extraction, never use mock data for compliance analysis
  - API URL: https://api.firecrawl.dev/v1/scrape
  - Authentication: Bearer token `Authorization: Bearer {FIRECRAWL_API_KEY}`
  - Must set USE_MOCK_PERCENTAGE=0 for all production runs
- **BeautifulSoup**: HTML parsing (fallback for simple sites)
- **Requests**: HTTP library (fallback for simple sites)
- **SentenceTransformers**: Text embedding generation
- **aiohttp**: Asynchronous HTTP client for concurrent requests
- **asyncio**: Asynchronous programming with Python
- **tldextract**: Domain extraction from URLs

### Vector Database
- **Pinecone**: Vector database for semantic search
- **langchain**: Framework for building LLM applications

### Batch Processing
- **URL Batching System**: Custom implementation with:
  - Dynamic batch sizing based on domain distribution
  - Resource-aware concurrency control
  - Domain-based rate limiting
  - Comprehensive error handling and retry mechanisms
  - Progress tracking and reporting
- **ThreadPoolExecutor**: Managed thread pools for controlled concurrency
- **Semaphore**: Rate limiting and resource management
- **Backoff strategies**: Exponential backoff for retries
- **Disk-based queue**: For persistent processing of large batches

### Testing
- **pytest**: Testing framework
- **pytest-asyncio**: Testing async code
- **httpx**: HTTP client for testing API endpoints
- **pytest-cov**: Test coverage reporting

## Development Setup

### Environment
- Local development with Python 3.10+
- Poetry for dependency management
- Pre-commit hooks for code quality
- Environment variables managed via .env file

### API Keys Required
- **Firecrawl API**: For web crawling with JavaScript support
- **Pinecone API**: For vector database storage and retrieval

### Resource Requirements
- **Memory**: Minimum 8GB RAM, recommended 16GB+ for larger batches
- **CPU**: 4+ cores recommended for optimal concurrent processing
- **Disk Space**: Minimum 20GB free space for storage of URL content and vectors
- **Network**: Stable internet connection with good bandwidth

## Technical Constraints

### Scaling Considerations
- **Batch Size Management**: Configurable batch sizes to manage memory usage
- **Concurrency Limits**: Adjustable concurrency based on available resources
- **Domain Rate Limiting**: Respect for website resources with domain-specific throttling
- **API Rate Limits**: 
  - Firecrawl: 10 requests/second (paid tier)
  - Pinecone: Variable based on plan (currently using standard tier)

### Resource Management
- **Memory Monitoring**: Active tracking of memory usage during batch processing
- **Graceful Degradation**: Automatic reduction of concurrency when resources are constrained
- **Persistent Queue**: Disk-based storage for batch jobs to survive restarts
- **Checkpoint System**: Regular saving of progress to enable resume after interruption

### Error Handling
- **Robust Retry Mechanism**: With exponential backoff for transient errors
- **Comprehensive Error Categorization**: 
  - Network errors (timeouts, connection issues)
  - Server errors (5xx responses)
  - Client errors (4xx responses)
  - Parsing errors (invalid HTML)
  - Resource errors (out of memory)
- **Failed URL Storage**: Separate storage with error details and retry capabilities

## Firecrawl Integration Details

### API Configuration
- **Endpoint**: https://api.firecrawl.dev/v1/scrape
- **Method**: POST
- **Headers**:
  - `Authorization: Bearer {FIRECRAWL_API_KEY}`
  - `Content-Type: application/json`
  - `Accept: application/json`
- **Payload**:
  ```json
  {
    "url": "https://example.com",
    "formats": ["markdown", "html"],
    "timeout": 30000
  }
  ```
- **Response Format**:
  ```json
  {
    "success": true,
    "data": {
      "markdown": "Content in markdown format...",
      "html": "Content in HTML format...",
      "metadata": {
        "title": "Page Title"
      }
    }
  }
  ```

### Important Environment Variables
- `FIRECRAWL_API_KEY`: API key for Firecrawl service
- `FIRECRAWL_API_URL`: API endpoint URL (default: https://api.firecrawl.dev/v1/scrape)
- `USE_MOCK_PERCENTAGE`: Must be set to 0 for compliance analysis - never use mock data
- `FIRECRAWL_TIMEOUT`: Timeout in seconds (default: 30)
- `MAX_RETRY_COUNT`: Number of retries for failed requests (default: 3)
- `SKIP_ALREADY_PROCESSED`: Control whether to skip URLs already in Pinecone (default: False)

### Error Handling
- **Rate Limits**: Handle 429 errors with exponential backoff
- **Server Errors**: Retry on 5xx errors
- **Timeout Errors**: Implement proper timeout handling
- **SSL Errors**: Optional fallback with SSL verification disabled

## Dependencies

The project uses poetry for dependency management. The core dependencies are:

```
[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.105.0"
uvicorn = "^0.24.0.post1"
pydantic = "^2.5.2"
pydantic-settings = "^2.1.0"
sqlalchemy = "^2.0.23"
alembic = "^1.12.1"
python-dotenv = "^1.0.0"
requests = "^2.31.0"
beautifulsoup4 = "^4.12.2"
aiohttp = "^3.9.1"
pinecone-client = "^2.2.4"
sentence-transformers = "^2.2.2"
langchain = "^0.0.345"
backoff = "^2.2.1"
tldextract = "^5.1.1"
```

Development dependencies include:

```
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
httpx = "^0.25.2"
pytest-cov = "^4.1.0"
black = "^23.11.0"
isort = "^5.12.0"
mypy = "^1.7.1"
ruff = "^0.1.6"
pre-commit = "^3.5.0"
```

## Batch Processing Configuration

The batch processing system is designed to be highly configurable to adapt to different hardware and network conditions:

```python
# Default settings in config.py
MAX_URLS_PER_BATCH = 1000  # Maximum URLs in a single batch
MAX_CONCURRENT_REQUESTS = 50  # Maximum concurrent requests
DOMAIN_COOLDOWN_PERIOD = 2.0  # Seconds between requests to the same domain
MAX_RETRIES = 3  # Maximum number of retries for failed requests
RETRY_BACKOFF_FACTOR = 2.0  # Exponential backoff factor for retries
MEMORY_THRESHOLD_PERCENT = 80  # Memory usage threshold for throttling
BATCH_CHECKPOINT_INTERVAL = 100  # Save progress every N URLs
```

These settings can be adjusted based on available hardware resources and specific use cases.

## Important Processing Guidelines

1. **Never use mock data for compliance analysis** - All compliance decisions must be based on real data
2. **Always process with USE_MOCK_PERCENTAGE=0** for production runs
3. **Verify that Firecrawl API is properly configured** before starting large batch jobs
4. **Monitor the processing speed** - Target 0.16-0.32 URLs/minute for thorough analysis
5. **Check both blacklist_consolidated.csv and review_needed.csv** for proper categorization
6. **Never delete URLs from blacklist without verification** 