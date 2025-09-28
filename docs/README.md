# URL Checker

A compliance monitoring application for analyzing web pages that reference your brand. This application crawls referring URLs, extracts content, and performs AI-powered compliance analysis to identify non-compliant mentions.

## Key Features

- **Efficient Batch Processing**: Handles large-scale URL processing (up to 200,000 URLs) with smart resource management
- **Intelligent Crawling**: Uses Firecrawl for reliable content extraction from both static and JavaScript-heavy pages
- **Vector Storage**: Stores content embeddings in Pinecone for semantic search and clustering
- **Resource-Aware Operation**: Dynamically adjusts concurrency based on system resources and domain distribution
- **Failed URL Management**: Separately tracks and manages URLs that fail processing
- **Comprehensive API**: RESTful endpoints for batch submission, status checking, and results retrieval
- **Testing Framework**: Includes mock processors for testing without API dependencies

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Database**: Pinecone (vector DB), SQLite (configuration)
- **AI Integration**: OpenRouter, SentenceTransformers
- **Web Crawling**: Firecrawl API with async handling
- **Development**: Poetry, Git, Virtual Environments
- **Testing**: Pytest, AsyncIO testing

## Current Status

✅ **Core system is operational with the following completed features:**
- URL validation and normalization
- Web crawling integration with Firecrawl's async API
- Content extraction and processing pipeline
- Vector database integration with Pinecone
- Dynamic batch sizing based on domain distribution
- Domain-based rate limiting
- Resource-aware concurrency control
- Failed URL tracking and management
- API endpoints for all core functionality
- Mock processing system for testing at scale

⏳ **In progress:**
- Testing with progressively larger batches
- Performance optimization for 200K URL processing
- User interface development
- Advanced error handling and retry strategies

## Setup

### Prerequisites

- Python 3.11+
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/url-checker.git
   cd url-checker
   ```

2. Set up Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## Batch Processing Configuration

Configure the batch processing parameters in your `.env` file:
```
# Batch Processing Settings
MAX_URLS_PER_BATCH=100           # Number of URLs per batch
MAX_CONCURRENT_REQUESTS=10       # Maximum concurrent HTTP requests
MAX_REQUESTS_PER_DOMAIN=2        # Maximum concurrent requests per domain
DOMAIN_COOLDOWN_PERIOD=3.0       # Seconds to wait between requests to same domain
MAX_CPU_PERCENT=80.0             # Maximum CPU usage percentage
MAX_MEMORY_PERCENT=80.0          # Maximum memory usage percentage
```

## API Endpoints

- `POST /api/batches/process`: Process a batch of URLs
- `GET /api/batches/status/{batch_id}`: Check batch processing status
- `GET /api/batches/results/{batch_id}`: Retrieve processing results
- `GET /api/batches/failed/{batch_id}`: Get failed URLs for review
- `POST /api/batches/retry`: Retry failed URLs

## Development

### Running the Application

```bash
# Start the backend server
poetry run uvicorn app.main:app --reload
```

### Project Structure

- `app/`: Main application code
  - `api/`: FastAPI routes
  - `core/`: Core application logic
  - `models/`: Data models
  - `services/`: External service integrations
  - `mock_processor.py`: Mock implementation for testing
- `data/`: Data storage
  - `inputs/`: Input CSV files
  - `outputs/`: Output reports
  - `logs/`: Processing logs
- `tests/`: Test suite
  - `test_batch_scaling.py`: Test batch processing at scale
- `memory-bank/`: Project documentation
- `run_backlinks_test.py`: Script for testing with real backlink data

### Testing Framework

The project includes a robust testing framework to validate batch processing capabilities:

- **Mock Processor**: Simulates URL processing without requiring API keys or external services
- **Configurable Success Rates**: Test different success/failure scenarios 
- **Resource Simulation**: Tracks simulated memory and CPU usage for performance testing
- **Batch Testing**: Test processing of large batches of URLs
- **CSV Processing**: Support for testing with real-world CSV data files

To run a batch test with the mock processor:

```bash
# Process URLs from a CSV file
python run_backlinks_test.py --file your_backlinks.csv --limit 10000 --batch-size 1000

# Available options
--file TEXT          CSV file containing URLs [required]
--column TEXT        Column name containing URLs [default: Referring page URL]
--limit INTEGER      Maximum number of URLs to process [default: 1000]
--offset INTEGER     Start position in CSV file [default: 0]
--batch-size INTEGER Number of URLs per batch [default: 200]
```

### Memory Bank

This project uses a Memory Bank approach for comprehensive documentation:
- `projectbrief.md`: Core project requirements
- `activeContext.md`: Current work focus
- `systemPatterns.md`: System architecture
- `techContext.md`: Technical details
- `progress.md`: Current status
- `productContext.md`: Problem and solution context

## License

[MIT License](LICENSE)

## Acknowledgements

- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [Playwright](https://playwright.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pinecone](https://www.pinecone.io/)
- [OpenRouter](https://openrouter.ai/)

## Batch Processing for Large Datasets

This application is optimized for processing large volumes of URLs (up to 200,000) with efficient resource management:

### Features

- **Smart Batching**: URLs are processed in configurable batches to manage memory usage
- **Domain-Based Rate Limiting**: Prevents overloading individual domains with too many requests
- **Resource-Aware Concurrency**: Adjusts concurrency based on CPU and memory usage
- **Failed URL Management**: Separately tracks and stores failed URLs for later review
- **Detailed Reporting**: Provides comprehensive statistics on processing results
- **Testing Mode**: Supports mock processing to validate system performance before using real APIs

### Processing Large Batches

1. **Environment Configuration**:
   
   Configure the batch processing parameters in your `.env` file:
   ```
   # Batch Processing Settings
   MAX_URLS_PER_BATCH=100           # Number of URLs per batch
   MAX_CONCURRENT_REQUESTS=10       # Maximum concurrent HTTP requests
   MAX_REQUESTS_PER_DOMAIN=2        # Maximum concurrent requests per domain
   DOMAIN_COOLDOWN_PERIOD=3.0       # Seconds to wait between requests to same domain
   MAX_CPU_PERCENT=80.0             # Maximum CPU usage percentage
   MAX_MEMORY_PERCENT=80.0          # Maximum memory usage percentage
   ```

2. **API Endpoints**:

   - `POST /api/batches/process`: Process a batch of URLs
   - `GET /api/batches/status/{batch_id}`: Check batch processing status
   - `POST /api/batches/failed-urls`: Get failed URLs for review
   - `POST /api/batches/retry`: Retry a failed URL
   - `GET /api/batches/export-failed/{batch_id}`: Export failed URLs to a file

3. **Monitoring Progress**:

   The system provides real-time status updates on batch processing, including:
   - Total URLs processed
   - Success/failure counts
   - Processing speed (URLs per second)
   - Estimated completion time
   - Resource usage

4. **Handling Failed URLs**:

   Failed URLs are stored separately with detailed error information. You can:
   - Review failed URLs through the API or UI
   - Export failed URLs to CSV or JSON
   - Retry individual failed URLs
   - Mark URLs as reviewed after manual inspection

5. **Testing Mode**:

   Before processing with real APIs, you can use the testing framework:
   - Validates system design without consuming API credits
   - Simulates realistic success/failure scenarios
   - Tests resource management with large batches
   - Provides performance metrics for optimization

### Best Practices for Large Batches

1. **Gradual Scaling**: Start with smaller batches (1,000-10,000 URLs) before processing the full 200,000
2. **Monitor Resources**: Keep an eye on CPU and memory usage during processing
3. **Domain Distribution**: Distribute URLs across different domains to avoid rate limiting
4. **Off-Peak Processing**: Schedule large batch jobs during off-peak hours
5. **Checkpointing**: Use the batch ID to track progress and resume if necessary
6. **Test First**: Use the mock processor to validate system performance before using real APIs 

## Recent Updates

### URL Reprocessing Fix (Enhanced)

We've implemented and enhanced a fix to prevent the crawler from processing URLs that have already been stored in Pinecone. The issue was that the system was only checking the database for processed URLs and not checking Pinecone, leading to duplicate processing.

Key changes:
- Added a `url_exists_in_pinecone` method to the `URLProcessor` class that checks if a URL is already stored in Pinecone
- Modified the URL processing logic to skip URLs that either exist in the database with "processed" status or are found in Pinecone
- Enhanced the matching algorithm to search more results (top_k=5) and check each result for an exact URL match
- This improvement ensures that URLs with the same content but different ranking in semantic search results will still be properly detected

### New Diagnostic Tools

Several new utility scripts have been added to help debug and test the system:

1. **access_pinecone_llm.py**:
   - Verifies Pinecone access and retrieves processed URLs
   - Can analyze URL content via LLM directly from Pinecone data
   - Provides sample query functionality to test Pinecone's retrieval capabilities

   ```bash
   # Basic Pinecone access test
   python access_pinecone_llm.py
   
   # Analyze URLs from Pinecone with LLM
   python access_pinecone_llm.py --analyze
   
   # Use a custom query for Pinecone search
   python access_pinecone_llm.py --query "admirals forex" --limit 10
   ```

2. **fix_url_reprocessing.py**:
   - Diagnoses the URL reprocessing issue
   - Implements and tests the fix
   - Creates a patch file for the permanent solution

   ```bash
   # Run full diagnosis and fix
   python fix_url_reprocessing.py
   
   # Only diagnose the issue
   python fix_url_reprocessing.py --diagnose
   
   # Only test the fix
   python fix_url_reprocessing.py --test
   ```

3. **test_pinecone_url_check.py**:
   - Tests the URL reprocessing fix on real URLs
   - Verifies Pinecone search functionality
   - Compares database and Pinecone results

   ```bash
   # Test with sample URLs from the database
   python test_pinecone_url_check.py
   
   # Test with a specific URL
   python test_pinecone_url_check.py --url "https://example.com"
   ``` 