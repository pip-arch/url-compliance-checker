# URL-Checker Project Organization

This document outlines the organization of the URL-Checker project and explains the purpose of each directory.

## Directory Structure

```
URL-checker/
├── app/                    # Core application code
│   ├── api/                # API endpoints and routes
│   ├── core/               # Core business logic
│   ├── models/             # Data models and schemas
│   ├── services/           # External service integrations
│   │   ├── crawlers/       # Web crawling services
│   │   ├── enrichment.py   # URL enrichment (WHOIS, SSL, screenshots)
│   │   ├── domain_analyzer.py # Smart domain analysis
│   │   ├── pattern_detector.py # ML pattern detection
│   │   └── quality_assurance.py # QA and confidence calibration
│   └── ui/                 # User interface components
├── data/                   # Data storage (ORGANIZED)
│   ├── inputs/             # Input files for processing
│   │   ├── admiral_markets/    # Processed Admiral Markets CSV files
│   │   ├── blacklist_keywords/ # Blacklist keyword files (CSV/XLSX)
│   │   └── raw_backlinks/      # Original raw backlink exports (UTF-16)
│   ├── outputs/            # Output files from processing
│   │   ├── blacklists/         # Blacklisted URLs and domains
│   │   ├── whitelists/         # Verified whitelist URLs
│   │   ├── review/             # URLs requiring manual review
│   │   ├── organized/          # Organized batch outputs with timestamps
│   │   ├── screenshots/        # URL screenshots for enrichment
│   │   ├── analysis_results/   # Batch processing results
│   │   ├── domain_analysis/    # Domain-level analysis reports
│   │   ├── enrichment/         # Enriched URL data (WHOIS, SSL, etc.)
│   │   └── qa_reports/         # Quality assurance reports
│   ├── archive/            # Archived files
│   │   ├── tmp_backup/         # Backup of old /tmp folder contents
│   │   └── old_inputs/         # Archived input files
│   ├── test_files/         # Test files (cleaned)
│   │   ├── all_admiral_urls.csv    # All 96,844 extracted URLs
│   │   ├── test_100_urls.csv       # 100 URL test sample
│   │   ├── test_10_urls.csv        # 10 URL test sample
│   │   └── archive/                # Archived old test files
│   ├── batch_state/        # State of processing batches
│   ├── db/                 # Database files
│   ├── logs/               # Log files
│   ├── models/             # ML models for pattern detection
│   ├── qa/                 # QA results and calibration data
│   └── tmp/                # Temporary files (now empty/clean)
├── docs/                   # Documentation
│   ├── SCRIPTS.md          # Documentation of all scripts
│   ├── ORGANIZATION.md     # This file - project organization
│   └── TEST_GUIDE.md       # Guide for testing
├── scripts/                # Utility and processing scripts
│   ├── diagnostic/         # Scripts for diagnosing issues
│   ├── fixes/              # Scripts for fixing specific issues
│   ├── testing/            # Scripts for testing functionality
│   ├── utils/              # Utility scripts
│   ├── organize_data_structure.py  # Data organization script
│   ├── extract_all_urls.py         # URL extraction from CSV files
│   └── run_improved_process.py     # Main processing script
├── tests/                  # Test scripts and test cases
├── venv/                   # Python virtual environment
├── .env                    # Environment variables
├── .env.example            # Example environment file
├── .gitignore              # Git ignore file
├── SYSTEM_ARCHITECTURE.md # Detailed system architecture
├── poetry.lock             # Poetry dependency lock file
├── pyproject.toml          # Poetry project configuration
├── README.md               # Project readme
├── requirements.txt        # Python dependencies
└── roadmap.md              # Development roadmap
```

## Directory Descriptions

### Application Code (`app/`)

The `app/` directory contains the core application code, organized into several subdirectories:

- **api/**: Contains API endpoints and route definitions for the FastAPI application.
- **core/**: Contains the core business logic of the application, including:
  - URL processing and compliance checking
  - Blacklist management and keyword fallback
  - Review management
- **models/**: Contains data models and schemas used throughout the application.
- **services/**: Contains integrations with external services and advanced features:
  - **crawlers/**: Web crawling services (Firecrawl, Crawl4AI, custom crawler)
  - **enrichment.py**: URL enrichment with WHOIS, SSL, screenshots, security headers
  - **domain_analyzer.py**: Smart domain analysis with violation tracking and auto-blacklisting
  - **pattern_detector.py**: ML-based pattern detection using TF-IDF and clustering
  - **quality_assurance.py**: QA checks and confidence score calibration
- **ui/**: Contains user interface components, templates, and static assets.

### Data Storage (`data/`) - NEWLY ORGANIZED

The `data/` directory has been completely reorganized for clarity and efficiency:

#### **Input Files (`data/inputs/`)**
- **admiral_markets/**: Processed Admiral Markets CSV files ready for analysis
  - `admiralmarkets_latest_utf8.csv` (37.6MB) - Latest UTF-8 encoded version
  - `admiralmarkets_clean.csv` (4.4MB) - Cleaned version
  - `referring_urls.txt` (4.8MB) - Extracted referring URLs
- **blacklist_keywords/**: Blacklist keyword files in multiple formats
  - `Blacklist keywords.csv` (1.5KB) - Current active keywords
  - `Blacklist keywords (1).xlsx` (14.6KB) - Original Excel version
  - `Blacklist keywords.xlsx` (10.8KB) - Backup version
- **raw_backlinks/**: Original raw backlink export files (UTF-16 encoded)
  - Two Admiral Markets backlink files totaling ~150MB

#### **Output Files (`data/outputs/`)**
- **blacklists/**: Blacklisted URLs and domains
  - `blacklist_consolidated_master.csv` (748KB) - Master blacklist
  - `blacklist_direct.csv` (32KB) - Direct blacklist entries
- **whitelists/**: Verified whitelist URLs
- **review/**: URLs requiring manual review
- **organized/**: Organized batch outputs with timestamps
- **screenshots/**: URL screenshots for enrichment analysis
- **analysis_results/**: Batch processing results
- **domain_analysis/**: Domain-level analysis reports and violation tracking
- **enrichment/**: Enriched URL data (WHOIS, SSL certificates, security headers)
- **qa_reports/**: Quality assurance reports and accuracy metrics

#### **Archive (`data/archive/`)**
- **tmp_backup/**: Complete backup of old `/tmp` folder contents
- **old_inputs/**: Archived input files

#### **Test Files (`data/test_files/`)**
- `all_admiral_urls.csv` (6.8MB) - All 96,844 extracted URLs ready for processing
- `test_100_urls.csv` (7.5KB) - 100 URL test sample
- `test_10_urls.csv` (741B) - 10 URL test sample
- **archive/**: Old test files moved here

#### **Other Data Directories**
- **batch_state/**: State of processing batches for resuming interrupted processing
- **db/**: Database files (SQLite)
- **logs/**: Log files from application runs
- **models/**: ML models for pattern detection
- **qa/**: QA results and confidence calibration data
- **tmp/**: Temporary files (now clean and empty)

### Documentation (`docs/`)

The `docs/` directory contains project documentation:

- **SCRIPTS.md**: Detailed documentation of all scripts in the project.
- **ORGANIZATION.md**: This file - explains the project organization.
- **TEST_GUIDE.md**: Guide for running tests and interpreting results.

### Scripts (`scripts/`)

The `scripts/` directory contains various scripts for different purposes:

- **diagnostic/**: Scripts for diagnosing issues with the application or external services.
- **fixes/**: Scripts for fixing specific issues in the application or data.
- **testing/**: Scripts for testing functionality of the application.
- **utils/**: Utility scripts for common tasks.
- **organize_data_structure.py**: Script for organizing data files into clean structure.
- **extract_all_urls.py**: Script for extracting URLs from Admiral Markets CSV files.

### Tests (`tests/`)

The `tests/` directory contains test scripts and test cases for verifying the functionality of the application.

## Core Files

- **run_improved_process.py**: Main script for processing URLs with enhanced features:
  - Smart domain analysis and auto-blacklisting
  - ML pattern detection and learning
  - URL enrichment with screenshots and metadata
  - Quality assurance checks and confidence calibration
- **.env**: Contains environment variables needed by the application.
- **SYSTEM_ARCHITECTURE.md**: Detailed system architecture and workflow documentation.
- **requirements.txt**: Lists Python dependencies required by the application.
- **pyproject.toml** and **poetry.lock**: Poetry configuration and dependency lock files.

## Enhanced Features

The URL-Checker now includes advanced intelligence features:

1. **Smart Domain Analysis**: Tracks domain violations and automatically blacklists problematic domains
2. **Pattern Detection**: ML-based learning from violations to detect new patterns
3. **URL Enrichment**: Captures screenshots, WHOIS data, SSL certificates, and security headers
4. **Quality Assurance**: Random re-checks and confidence score calibration
5. **Organized Output**: Clean, timestamped output files with domain summaries

## Usage

The main functionality of the application is provided by the enhanced `run_improved_process.py` script:

```bash
# Process URLs with all enhanced features
PYTHONPATH=/path/to/URL-checker python scripts/run_improved_process.py \
  --file data/inputs/admiral_markets/admiralmarkets_latest_utf8.csv \
  --column url \
  --limit 1000 \
  --batch-size 20 \
  --workers 10

# Process all extracted Admiral Markets URLs
PYTHONPATH=/path/to/URL-checker python scripts/run_improved_process.py \
  --file data/test_files/all_admiral_urls.csv \
  --column url \
  --limit 96844
```

## Data Organization Benefits

The new organized structure provides:

- **Clear separation** of input and output files
- **Easy backup and archival** of old data
- **Structured outputs** for different analysis types
- **Clean test environment** with archived old files
- **Comprehensive documentation** with README files and inventories
- **Scalable architecture** ready for large-scale processing

For more information on specific scripts and their usage, see [SCRIPTS.md](SCRIPTS.md). 