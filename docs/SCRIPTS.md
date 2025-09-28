# URL-Checker Scripts Documentation

This document provides information about all scripts in the URL-Checker project, their purposes, and how they're used.

## Core Processing Scripts

- **run_improved_process.py** - Main script for processing URLs with improved confidence thresholds. Analyzes URLs for compliance issues and categorizes them as blacklist, whitelist, or review.
  - Usage: `python scripts/run_improved_process.py --file [csv_file] --limit [num] --batch-size [num] --workers [num]`
  - Parameters:
    - `--file`: CSV file containing URLs to process
    - `--limit`: Maximum number of URLs to process
    - `--batch-size`: Number of URLs to process in each batch
    - `--workers`: Number of concurrent workers

- **run_real_process.py** - Production version of the URL processor for real-world usage.
  - Usage: `python scripts/run_real_process.py --file [csv_file] --limit [num]`

- **run_initial_tests.sh** - Shell script for running initial tests with a small number of URLs.
  - Usage: `./scripts/run_initial_tests.sh`

- **run_scaled_tests.sh** - Shell script for testing with a larger number of URLs.
  - Usage: `./scripts/run_scaled_tests.sh`

## Diagnostic Scripts

- **openrouter_diagnostic.py** - Diagnostic script for testing OpenRouter API integration.
  - Usage: `python scripts/diagnostic/openrouter_diagnostic.py`

- **reanalyze_debugging.py** - Debug script for reanalyzing problematic URLs.
  - Usage: `python scripts/diagnostic/reanalyze_debugging.py`

- **check_process.py** - Checks the status of a running URL processing job.
  - Usage: `python scripts/check_process.py`

- **check_progress.py** - Shows detailed progress information for batch processing.
  - Usage: `python scripts/check_progress.py`

## Utility Scripts

- **check_api_key.py** - Validates API keys for external services.
  - Usage: `python scripts/utils/check_api_key.py`

- **check_blacklist.py** - Checks if specific URLs or domains are blacklisted.
  - Usage: `python scripts/utils/check_blacklist.py [url]`

- **check_pinecone_count.py** - Counts vectors stored in Pinecone.
  - Usage: `python scripts/check_pinecone_count.py`

- **check_pinecone_direct.py** - Directly queries Pinecone for specific vectors.
  - Usage: `python scripts/check_pinecone_direct.py [query]`

- **consolidate_blacklists.py** - Merges multiple blacklist files into one.
  - Usage: `python scripts/consolidate_blacklists.py`

- **export_blacklist_urls.py** - Exports blacklisted URLs to a file.
  - Usage: `python scripts/export_blacklist_urls.py --output [file]`

- **extract_blacklisted_urls.py** - Extracts blacklisted URLs from the database.
  - Usage: `python scripts/extract_blacklisted_urls.py`

- **extract_urls.py** - Extracts URLs from various file formats.
  - Usage: `python scripts/extract_urls.py --input [file] --output [file]`

## Fix Scripts

- **fix_api_key.py** - Fixes API key issues in configuration.
  - Usage: `python scripts/fixes/fix_api_key.py`

- **fix_firecrawl_auth.py** - Resolves authentication issues with Firecrawl.
  - Usage: `python scripts/fixes/fix_firecrawl_auth.py`

- **fix_openrouter_access.py** - Fixes OpenRouter API access issues.
  - Usage: `python scripts/fix_openrouter_access.py`

- **fix_url_categorization.py** - Fixes issues with URL categorization.
  - Usage: `python scripts/fixes/fix_url_categorization.py`

- **fix_url_reprocessing.py** - Fixes issues with URL reprocessing.
  - Usage: `python scripts/fix_url_reprocessing.py`

## Management Scripts

- **manage_pinecone_urls.py** - Manages URLs stored in Pinecone.
  - Usage: `python scripts/manage_pinecone_urls.py --action [action]`

- **replace_openrouter_key.py** - Updates the OpenRouter API key.
  - Usage: `python scripts/replace_openrouter_key.py --key [new_key]`

- **restore_blacklist.py** - Restores a blacklist from backup.
  - Usage: `python scripts/restore_blacklist.py --backup [file]`

- **update_api_key.py** - Updates API keys for various services.
  - Usage: `python scripts/update_api_key.py --service [service] --key [new_key]`

## Reanalysis Scripts

- **reanalyze_pinecone_urls.py** - Reanalyzes URLs stored in Pinecone.
  - Usage: `python scripts/reanalyze_pinecone_urls.py`

- **reanalyze_remaining.py** - Reanalyzes remaining unprocessed URLs.
  - Usage: `python scripts/reanalyze_remaining.py`

- **reanalyze_remaining_with_fallback.py** - Reanalyzes with fallback options.
  - Usage: `python scripts/reanalyze_remaining_with_fallback.py`

- **reanalyze_remaining_with_openai.py** - Reanalyzes using OpenAI.
  - Usage: `python scripts/reanalyze_remaining_with_openai.py`

## Test Scripts

- **test_analysis_methods.py** - Tests various URL analysis methods.
  - Usage: `python scripts/test_analysis_methods.py`

- **test_backlinks.py** - Tests processing of backlink data.
  - Usage: `python scripts/test_backlinks.py`

- **test_batch_with_fallback.py** - Tests batch processing with fallback.
  - Usage: `python scripts/test_batch_with_fallback.py`

- **test_blacklist.py** - Tests blacklist functionality.
  - Usage: `python tests/test_blacklist.py`

- **test_categorization_fix.py** - Tests URL categorization fixes.
  - Usage: `python tests/test_categorization_fix.py`

- **test_firecrawl_auth.py** - Tests Firecrawl authentication.
  - Usage: `python tests/test_firecrawl_auth.py`

- **test_firecrawl_direct.py** - Tests direct Firecrawl API calls.
  - Usage: `python scripts/test_firecrawl_direct.py [url]`

- **test_firecrawl_fixed.py** - Tests fixed Firecrawl integration.
  - Usage: `python scripts/test_firecrawl_fixed.py`

- **test_firecrawl_updated.py** - Tests updated Firecrawl integration.
  - Usage: `python scripts/test_firecrawl_updated.py`

- **test_firecrawl_v2.py** - Tests Firecrawl V2 API.
  - Usage: `python scripts/test_firecrawl_v2.py`

- **test_openrouter.py** - Tests OpenRouter integration.
  - Usage: `python tests/test_openrouter.py`

- **test_openrouter_fallback.py** - Tests OpenRouter fallback mechanisms.
  - Usage: `python scripts/test_openrouter_fallback.py`

- **test_openrouter_fallback_direct.py** - Tests direct fallback to alternative models.
  - Usage: `python scripts/test_openrouter_fallback_direct.py`

- **test_openrouter_raw.py** - Tests raw OpenRouter API responses.
  - Usage: `python scripts/test_openrouter_raw.py`

- **test_pinecone.py** - Tests Pinecone integration.
  - Usage: `python scripts/test_pinecone.py`

- **test_pinecone_fix.py** - Tests fixes for Pinecone issues.
  - Usage: `python scripts/test_pinecone_fix.py`

- **test_pinecone_url_check.py** - Tests URL checking against Pinecone.
  - Usage: `python scripts/test_pinecone_url_check.py [url]`

- **test_run_real.py** - Tests the real processing workflow.
  - Usage: `python tests/test_run_real.py`

- **test_url_processor.py** - Tests the URL processor component.
  - Usage: `python tests/test_url_processor.py`

## Other Scripts

- **init_db.py** - Initializes the database.
  - Usage: `python scripts/init_db.py`

- **access_pinecone_llm.py** - Accesses Pinecone and LLM services.
  - Usage: `python scripts/access_pinecone_llm.py`

- **openrouter_simplified.py** - Simplified interface to OpenRouter.
  - Usage: `python scripts/openrouter_simplified.py`

- **url_analyzer_direct.py** - Direct analysis of URLs without batch processing.
  - Usage: `python scripts/url_analyzer_direct.py [url]`

- **url_checker.py** - Simple URL checking script.
  - Usage: `python scripts/url_checker.py [url]`

## Important Note

Do not delete or modify these scripts without understanding their purpose and dependencies. The main application relies on many of these scripts for its functionality. 