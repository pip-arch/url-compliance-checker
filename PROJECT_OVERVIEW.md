# Admiral Markets URL Compliance Checker - Project Overview

## Executive Summary

The URL Compliance Checker is an AI-powered system designed to automatically analyze 200.000+ backlink URLs referencing Admiral Markets to identify potential compliance violations, brand misuse, and misleading content. The system leverages advanced web crawling, natural language processing, and machine learning to categorize URLs into blacklist, whitelist, or human review categories.

## Key Business Value

- **Automated Compliance Monitoring**: Processes thousands of URLs automatically vs manual review
- **Risk Mitigation**: Identifies unauthorized use of Admiral Markets brand, misleading claims, and regulatory violations
- **Efficiency**: 80%+ speed improvement through parallel processing and intelligent filtering
- **Scalability**: Processes 50+ URLs concurrently with automatic retry and fallback mechanisms
- **Accuracy**: Multi-layered AI analysis with confidence scoring and human review queue

## System Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           ADMIRAL MARKETS URL COMPLIANCE CHECKER                      │
│                                   AI-Powered Pipeline                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

1. INPUT SOURCES                    2. PRE-FILTERING                   3. WEB CRAWLING
┌──────────────────┐               ┌─────────────────────┐           ┌──────────────────┐
│ CSV Files        │               │ Domain Filtering    │           │ Crawler Chain    │
│ • 200.000 URLs   │──────────────▶│ • Skip own domains  │──────────▶│                  │
│ • Backlink data  │               │ • Skip blacklisted  │           │ 1. Firecrawl API │
│ • Referring URLs │               │ • Domain sampling   │           │ 2. Crawl4AI      │
└──────────────────┘               │ • Dead domain check │           │ 3. BeautifulSoup │
                                   └─────────────────────┘           └──────────────────┘
                                                                              │
                                                                              ▼
4. CONTENT ANALYSIS               5. DEDUPLICATION                   6. AI COMPLIANCE ANALYSIS
┌──────────────────────┐         ┌────────────────────┐            ┌──────────────────────┐
│ Admiral Detection    │         │ Pinecone Vector DB │            │ LLM Chain            │
│ • Pattern matching   │────────▶│ • Embedding storage│───────────▶│ 1. OpenRouter (95%)  │
│ • Context extraction │         │ • Similarity search│            │ 2. OpenAI (backup)   │
│ • Skip if no mention │         │ • Duplicate check  │            │ 3. Keyword fallback  │
└──────────────────────┘         └────────────────────┘            └──────────────────────┘
                                                                              │
                                                                              ▼
7. CATEGORIZATION                 8. DATA PERSISTENCE               9. OUTPUT & REPORTING
┌──────────────────────┐         ┌────────────────────┐           ┌──────────────────────┐
│ Decision Engine      │         │ PostgreSQL/Supabase│           │ Blacklist Export     │
│ • BLACKLIST ────────────────────▶ • URL records     │──────────▶│ • CSV format         │
│ • WHITELIST          │         │ • Compliance data  │           │ • Domain grouping    │
│ • REVIEW (human)     │         │ • Analysis history │           │ • Confidence scores  │
└──────────────────────┘         └────────────────────┘           └──────────────────────┘
```

## AI Integration Details

### 1. **Multi-Model LLM Analysis**
   - **Primary**: OpenRouter (Meta LLaMA 4 Scout) - 95% of requests
   - **Fallback**: OpenAI GPT-4 Turbo - When OpenRouter fails
   - **Emergency**: Keyword-based analysis - When both LLMs fail

### 2. **Compliance Detection Criteria**
   The AI analyzes content for:
   - **Misleading Information**: False claims about profits, guarantees, risk-free trading
   - **Unauthorized Offers**: Bonuses, promotions not sanctioned by Admiral Markets
   - **False Representation**: Fake partnerships, cloned sites, brand impersonation
   - **Regulatory Violations**: Non-compliant financial advice, missing risk disclosures
   - **Inappropriate Marketing**: Get-rich-quick schemes, exaggerated claims

### 3. **Intelligent Skipping Logic**
   - Pages without "Admiral Markets" mentions are automatically skipped
   - Already-processed URLs are detected via Pinecone vector similarity
   - Blacklisted domains are filtered before crawling begins

### 4. **Confidence Scoring**
   Each URL receives a confidence score (0.0-1.0) based on:
   - LLM model certainty
   - Number of compliance rule matches
   - Pattern detection algorithms
   - Historical domain reputation

## Technical Implementation

### Database Architecture
- **PostgreSQL (Supabase)**: Primary data storage
  - URL records with status tracking
  - Compliance analysis results
  - Batch processing metadata
  
- **Pinecone Vector DB**: Deduplication & similarity
  - Content embeddings
  - Fast duplicate detection
  - Semantic search capabilities

### Processing Optimization
- **Parallel Processing**: 50 concurrent workers
- **Smart Timeouts**: 10s for crawling, reduced from 30s
- **Domain Sampling**: Max 5 URLs per domain to avoid spam
- **Batch Processing**: 250 URLs per batch for efficiency
- **Skip Lists**: 8+ problematic domains pre-filtered

### Current Performance Metrics
- **Processing Speed**: ~3.8 batches/hour (950 URLs/hour)
- **Blacklist Growth**: 987 → 1,322 entries (+34% in current run)
- **Admiral Mention Hit Rate**: ~7.6% of crawled URLs
- **LLM Usage**: 95% OpenRouter, 3% OpenAI, 2% fallback

## Compliance Categorization Logic

```python
if high_priority_rule_match:
    → BLACKLIST (immediate)
elif ai_suggests_blacklist:
    → BLACKLIST (AI-driven)
elif rule_matches and (no_ai or ai_uncertain):
    → BLACKLIST (conservative)
elif ai_suggests_whitelist and no_rule_matches:
    → WHITELIST (safe)
else:
    → REVIEW (human needed)
```

## Key Features

1. **Automated Blacklist Management**
   - CSV export with domain grouping
   - Permanent storage of violations
   - Reason tracking with timestamps

2. **Quality Assurance**
   - Pattern learning from violations
   - Domain reputation tracking
   - Confidence adjustment algorithms

3. **Monitoring & Resumability**
   - Real-time progress tracking
   - Graceful pause/resume capability
   - Detailed logging and error handling

## Current Status (June 2025)
- **Progress**: 64.1% complete (84/131 batches)
- **URLs Processed**: ~21,000 of 32,577 (after sampling)
- **Blacklisted**: 1,322 URLs across multiple domains
- **Time Invested**: 36+ hours of processing
- **Remaining**: ~13 hours to completion

## Future Enhancements
- Admin dashboard for real-time monitoring
- API endpoint for on-demand URL checking
- Integration with Admiral Markets' internal systems
- Machine learning model fine-tuning based on results
- Automated weekly compliance reports 