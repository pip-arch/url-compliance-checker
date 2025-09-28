# URL Checker Project File Documentation

This document provides an explanation of each file in the URL Checker project, outlining its purpose and function.

## Root Files

### Blacklist keywords.xlsx
- Data file containing predefined keywords for identifying non-compliant content
- Used by `app/core/blacklist_keywords.py` as a fallback mechanism for content analysis
- Contains categorized keywords related to misleading information, unauthorized offers, false representation, etc.

### README.md
- Project documentation that describes the URL Checker application
- Contains information about features, tech stack, setup instructions, and usage examples
- Documents the batch processing capabilities and API endpoints
- Lists recent updates including the URL reprocessing fix and new diagnostic tools

### TEST_GUIDE.md
- Testing guide for URL Checker that outlines how to validate performance with large batches
- Provides step-by-step instructions for initial testing and scaled testing
- Explains how to analyze test results and configure the system for production
- Includes troubleshooting tips for common issues during testing

## Application Core (app/)

### app/__init__.py
- Package initialization file for the main application
- Contains a single comment line indicating it's the URL Checker package

### app/main.py
- Main entry point for the FastAPI application
- Initializes the FastAPI application, sets up middleware, routes, and templates
- Contains endpoints for health checks, API information, and testing functionality
- Includes a test integration endpoint that verifies connections to Pinecone, Firecrawl, and OpenRouter services
- Sets up error handling and server configuration

### app/mock_processor.py
- Provides a mock implementation of the URL processor for testing
- Simulates URL processing without requiring actual API dependencies
- Useful for testing the system at scale without consuming actual API credits
- Can be configured with different success/failure rates for testing

## API Routes (app/api/)

### app/api/__init__.py
- Package initialization file for the API components
- Contains a single comment line indicating it's the API package

### app/api/routes/__init__.py
- Package initialization file for the API routes
- Contains a single comment line indicating it's the Routes package

### app/api/routes/batch_router.py
- FastAPI router for batch processing of URLs
- Provides endpoints for starting batch processing, checking status, and managing failed URLs
- Implements background task processing for batch operations
- Includes endpoints for retrying failed URLs and exporting failed URLs

### app/api/routes/blacklist_router.py
- FastAPI router for managing the blacklist functionality
- Provides endpoints to get blacklist overview with analytics
- Allows retrieving blacklisted domains with filtering and pagination
- Implements domain reputation checking and manual domain blacklisting
- Supports exporting the blacklist in various formats (CSV, JSON, TXT)

### app/api/routes/report_router.py
- FastAPI router for compliance report generation and management
- Provides endpoints to list all reports, get specific reports, and view URLs in reports
- Implements report generation for URL batches in the background
- Supports downloading reports in different formats
- Includes an endpoint for retrieving analysis statistics

### app/api/routes/url_router.py
- FastAPI router for URL upload and processing
- Handles CSV file uploads containing URLs for compliance checking
- Provides endpoints to list batches, get batch information, and view URLs in batches
- Implements batch deletion functionality
- Processes uploaded URLs in the background

## Core Logic (app/core/)

### app/core/__init__.py
- Package initialization file for the core application logic
- Contains a single comment line indicating it's the Core package

### app/core/batch_processor.py
- Core module for efficiently processing large batches of URLs
- Implements resource-aware concurrency with CPU and memory monitoring
- Provides domain-based rate limiting to avoid overloading domains
- Includes batch checkpointing for resuming interrupted processing
- Implements adaptive chunk sizing based on resource utilization

### app/core/blacklist_keywords.py
- Fallback mechanism for content analysis when AI services are unavailable
- Loads and categorizes keywords from the Blacklist keywords.xlsx file
- Analyzes URL content by matching against predefined blacklist keywords
- Categorizes content based on matches with different severity levels
- Generates explanations for why content was flagged

### app/core/blacklist_manager.py
- Manages blacklisting of domains and URLs with detailed metadata
- Handles reading, writing, and updating blacklist files
- Tracks domain reputation and violation history
- Provides methods to check if a domain is blacklisted
- Supports exporting the blacklist in various formats
- Generates analytics about blacklisted domains

### app/core/compliance_checker.py
- Analyzes URLs for compliance with brand guidelines
- Uses OpenRouter AI service to assess content for potential compliance issues
- Categorizes URLs as whitelist, blacklist, or requiring review
- Generates compliance reports with detailed analysis
- Includes a fallback mechanism using keyword matching when AI service is unavailable

### app/core/csv_batch_processor.py
- Processes CSV files containing URLs for batch analysis
- Extracts URLs from various CSV formats with flexible column mapping
- Splits large CSV files into manageable batches
- Tracks processing progress and generates statistics
- Handles CSV files with different encodings

### app/core/url_processor.py
- Main class for processing URLs and extracting content
- Validates and filters URLs based on configurable criteria
- Crawls valid URLs using the Firecrawl service
- Extracts content and context around brand mentions
- Stores content in Pinecone vector database for semantic search
- Manages domain blacklisting based on compliance results

## Utility Scripts (scripts/utils/)

### scripts/utils/utf16_to_utf8_converter.py
- Utility for converting CSV files from UTF-16 encoding to UTF-8 format
- Detects file encoding automatically using BOM markers and content analysis
- Supports batch processing of multiple files in directories
- Preserves directory structure when processing recursively
- Solves encoding issues when importing data from Excel or other external tools

## Documentation (docs/)

### docs/utf16_encoding_fix.md
- Documentation about the UTF-16 to UTF-8 converter utility
- Explains the problem with UTF-16 encoded CSV files in the workflow
- Provides usage instructions for the conversion utility
- Includes troubleshooting tips for common encoding issues

### docs/ORGANIZATION.md
- Describes the organization and structure of the project
- Outlines code organization principles and patterns
- Provides guidelines for maintaining project structure

### docs/SCRIPTS.md
- Documents the purpose and usage of various utility scripts
- Includes example commands and parameter descriptions
- Helps developers understand when and how to use each script

### docs/README.md
- Documentation overview for the docs directory
- Provides an index of available documentation files
- Explains the documentation organization

## Services (app/services/)
This directory contains service integrations with external APIs and databases:

- Database service for storing URL processing data
- Vector database service (Pinecone) for storing content embeddings
- AI service (OpenRouter) for compliance analysis
- Web crawler service (Firecrawl) for content extraction
- Error handling and failure management services

## Models (app/models/)
This directory contains data models for the application:

- URL models for representing URL data and processing status
- Report models for compliance reports and results
- User models for authentication and authorization (if applicable)
- Schema definitions for API requests and responses 