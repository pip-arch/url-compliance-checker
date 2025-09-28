# Project Brief

## Purpose
This application is designed to perform **AI-powered compliance analysis** on web pages that refer to our company ("referring pages"). The goal is to ensure that all mentions of our brand and services on third-party sites are compliant with **EU regulatory requirements**.

## Core Features
- **Batch processing of URLs**: Extracts and processes referring page URLs from CSV files (e.g., backlink exports).
- **Crawling and content extraction**: 
  - Primary: Uses Requests + BeautifulSoup for static content
  - Secondary: Uses Playwright for JavaScript-heavy sites
  - Smart detection to minimize resource-intensive processing
- **AI compliance analysis**: Uses OpenRouter (LLM integration) to analyze the content of each referring page for:
  - Accurate and compliant brand mentions
  - Absence of misleading or non-compliant statements
  - Adherence to EU financial promotion and advertising regulations
- **Embeddings and semantic search**: Stores page embeddings in Pinecone for advanced search, clustering, and further AI analysis.
- **Reporting and blacklisting**: Generates compliance reports, flags non-compliant pages, and can blacklist domains with repeated violations.
- **Failed URL management**: Separately stores and manages URLs that fail processing for manual review.

## Why This Matters
- **Regulatory risk**: EU regulators (e.g., ESMA, CySEC, FCA) require strict compliance for all public mentions of financial services.
- **Brand protection**: Ensures our brand is not misrepresented or associated with non-compliant or fraudulent promotions.
- **Scalability**: Automates what would otherwise be a manual, error-prone process across thousands of referring pages.
- **Cost efficiency**: Processes large volumes of URLs (200,000+) using free, open-source tools to minimize operational costs.

## Technical Stack
- **Requests + BeautifulSoup** for primary web crawling
- **Playwright** for JavaScript-heavy sites (fallback)
- **OpenRouter** for LLM-based compliance analysis
- **Pinecone** for vector storage and semantic search
- **FastAPI** backend, Python, and modern async processing
- **SQLite** for local data storage

## Outcome
- Automated, scalable, and auditable compliance monitoring of all referring pages mentioning our brand, with actionable reports for legal and compliance teams.
- Cost-effective solution capable of processing 200,000+ URLs with minimal external service costs.
- Clear separation of successfully processed URLs and those requiring manual review. 