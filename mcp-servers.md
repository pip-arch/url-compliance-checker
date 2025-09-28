# MCP Servers Documentation for URL-Checker

## Overview
This document describes how MCP (Model Context Protocol) servers are integrated into the URL-checker project to enhance functionality and provide better state management.

## Configured MCP Servers

### 1. Memory Server (`@modelcontextprotocol/server-memory`)
- **Purpose**: Provides in-memory knowledge graph for tracking relationships and context
- **Usage in URL-Checker**:
  - Track URL processing relationships
  - Store temporary analysis results
  - Maintain domain-URL relationships
  - Cache frequently accessed data

### 2. Filesystem Server (`@modelcontextprotocol/server-filesystem`)
- **Purpose**: Direct file system access within the project directory
- **Path**: `/Users/daniil.lisovets/dib/URL-checker`
- **Usage in URL-Checker**:
  - Read/write CSV files
  - Access blacklist files
  - Manage export files
  - Handle batch processing files

### 3. Pinecone Server (`@pinecone-database/mcp`)
- **Purpose**: Vector database integration for semantic search and storage
- **Configuration**:
  - API Key: Configured in MCP settings
  - Environment: gcp-starter
  - Index: url-checker-index
- **Usage in URL-Checker**:
  - Store URL content embeddings
  - Semantic search for similar URLs
  - Duplicate detection
  - Content analysis storage

### 4. Supabase Server (`@supabase/mcp-server-supabase`)
- **Purpose**: PostgreSQL database for structured data and state management
- **Project**: Ai era (jyyhtegtspvhntrrebmf)
- **Usage in URL-Checker**:
  - Processing queue management
  - Processing history and audit trail
  - Checkpoint/resume functionality
  - Domain statistics tracking
  - API usage monitoring
  - Error tracking and debugging

### 5. Firecrawl MCP
Web scraping and crawling service for extracting content from URLs.

**Configuration:**
```json
{
  "mcpServers": {
    "firecrawl-mcp": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "fc-5e6640f52eee4558b9141c6a4ef169cb"
      }
    }
  }
}
```

**Usage:**
- Primary crawler for URL content extraction
- Handles JavaScript-heavy sites
- Provides clean markdown output

## Database Schema (Supabase)

### Core Tables:
1. **url_processing_queue**: Main queue for URLs to be processed
2. **processing_history**: Complete audit trail of all processing attempts
3. **processing_checkpoints**: Resume points for batch processing
4. **domain_statistics**: Domain-level metrics and blacklist status
5. **api_usage_tracking**: Monitor API costs and usage
6. **processing_errors**: Detailed error tracking

### Key Functions:
- `get_next_urls_to_process()`: Fetch next batch of URLs
- `mark_url_processed()`: Update URL status after processing
- `save_checkpoint()`: Save processing state for resume
- `get_latest_checkpoint()`: Retrieve last checkpoint
- `sync_blacklisted_domains()`: Auto-blacklist domains
- `get_blacklist_export()`: Export blacklisted URLs
- `get_processing_metrics()`: Real-time processing statistics

## Integration Strategy

### 1. Processing Flow with MCP:
```
1. Load URLs from CSV → Filesystem MCP
2. Queue URLs in Supabase → Supabase MCP
3. Fetch content → Store in Pinecone → Pinecone MCP
4. Track relationships → Memory MCP
5. Save checkpoints → Supabase MCP
6. Export results → Filesystem MCP
```

### 2. Resume Processing:
- Use Supabase to get last checkpoint
- Memory server maintains session context
- Pinecone checks for already processed URLs
- Filesystem reads from last position

### 3. Error Recovery:
- Supabase tracks all errors
- Memory server maintains error context
- Automatic retry with exponential backoff
- Failed URLs queued for manual review

## Best Practices

### 1. Batch Processing:
- Use Supabase transactions for batch updates
- Memory server for batch context
- Pinecone batch operations for efficiency

### 2. State Management:
- Always save checkpoints after each batch
- Use Supabase for persistent state
- Memory server for temporary state
- Regular exports to filesystem

### 3. Performance Optimization:
- Use Supabase materialized views for fast lookups
- Pinecone for semantic deduplication
- Memory server for caching
- Batch operations where possible

### 4. Error Handling:
- Log all errors to Supabase
- Use Memory server for error context
- Implement retry logic with backoff
- Manual review queue for persistent failures

## Monitoring and Maintenance

### 1. Database Maintenance:
```sql
-- Refresh materialized views
SELECT refresh_blacklist_cache();

-- Check processing metrics
SELECT * FROM get_processing_metrics();

-- View recent activity
SELECT * FROM recent_processing_activity;
```

### 2. Cost Monitoring:
- Track API usage in Supabase
- Monitor Pinecone vector count
- Regular cost analysis reports

### 3. Performance Monitoring:
- Average processing time per URL
- API response times
- Queue processing rate
- Error rates by type

## Future Enhancements

1. **Real-time Dashboard**: Use Supabase real-time features
2. **Advanced Analytics**: Leverage Pinecone for pattern detection
3. **Automated Workflows**: Trigger-based processing
4. **Multi-tenant Support**: Separate processing queues
5. **Advanced Caching**: Redis integration via MCP

## Troubleshooting

### Common Issues:
1. **MCP Connection Failed**: Check API keys in ~/.cursor/mcp.json
2. **Supabase Timeout**: Increase connection pool size
3. **Pinecone Rate Limits**: Implement request throttling
4. **Memory Server OOM**: Clear cache periodically

### Debug Commands:
```bash
# Test MCP connections
npx @modelcontextprotocol/inspector ~/.cursor/mcp.json

# Check Supabase status
SELECT * FROM processing_summary;

# Verify Pinecone index
# Use Pinecone MCP tools to describe index stats
```

## Security Considerations

1. **API Keys**: Store securely in MCP config
2. **Database Access**: Use service role key carefully
3. **Data Privacy**: No PII in vector embeddings
4. **Audit Trail**: Complete processing history in Supabase
5. **Access Control**: Implement RLS policies as needed

## Integration with URL-Checker

The URL-checker system uses these MCP servers in the following priority:
1. **Firecrawl MCP** - Primary crawler
2. **Crawl4AI** - First fallback
3. **Custom Crawler** - Final fallback

## Setup Instructions

1. Install the MCP server:
   ```bash
   npx -y firecrawl-mcp
   ```

2. The API key is already configured in `.env` file

3. Test the connection:
   ```bash
   python scripts/test_firecrawl_api.py
   ```
