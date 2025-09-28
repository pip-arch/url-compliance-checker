# Production Run Guide - URL Checker

## ✅ System Status: READY FOR PRODUCTION

### Quick Start Commands

#### 1. Test Run (Recommended First)
```bash
# Test with 100 URLs first
python scripts/run_improved_process_postgres.py \
  --file data/inputs/admiral_markets/referring_urls.txt \
  --column url \
  --limit 100 \
  --batch-size 20
```

#### 2. Full Production Run
```bash
# Process all 67k URLs
python scripts/run_improved_process_postgres.py \
  --file data/inputs/admiral_markets/referring_urls.txt \
  --column url \
  --batch-size 100 \
  --workers 20
```

#### 3. Monitor Progress
```bash
# In another terminal, watch the logs
tail -f data/logs/url_processing_*.log

# Check summary
python scripts/generate_summary_report.py
```

### Expected Timeline
- **100 URLs**: ~15 minutes
- **1,000 URLs**: ~2.5 hours  
- **10,000 URLs**: ~24 hours
- **67,693 URLs**: ~1 week (can be faster with more workers)

### Performance Optimization

#### For Faster Processing:
```bash
# Increase workers (if you have good internet)
--workers 50

# Larger batches (reduces overhead)
--batch-size 500

# Skip already processed domains
--max-domain 10  # Max 10 URLs per domain
```

### Monitoring Checklist

1. **Check Blacklist Growth**
   ```bash
   wc -l data/tmp/blacklist_consolidated.csv
   ```

2. **Review URLs Needing Manual Check**
   ```bash
   head data/tmp/review_needed.csv
   ```

3. **Monitor API Credits**
   - Firecrawl: Check usage in logs
   - OpenRouter: Monitor costs

4. **Database Status**
   - PostgreSQL: Check Supabase dashboard
   - Pinecone: Monitor vector count

### Troubleshooting

**If processing stops:**
1. Check last processed URL in logs
2. Restart with `--offset` parameter
3. Example: `--offset 5000` to skip first 5000

**If too many timeouts:**
1. Reduce workers: `--workers 10`
2. Increase timeout in .env: `FIRECRAWL_TIMEOUT=45`

**If database errors:**
1. Check Supabase connection
2. Verify .env credentials
3. Check network connectivity

### Daily Tasks

1. **Morning Check**
   ```bash
   python scripts/generate_summary_report.py
   ```

2. **Review High-Priority URLs**
   - Check `data/tmp/review_needed.csv`
   - Manually verify top violations

3. **Export Results**
   ```bash
   # Create report for Admiral Markets
   python scripts/export_compliance_report.py
   ```

### Success Indicators
- ✅ Steady blacklist growth (~10-20% of URLs)
- ✅ Low error rate (<10%)
- ✅ Consistent processing speed
- ✅ No memory/resource issues

### Contact for Issues
- Check logs first: `data/logs/`
- Database issues: Supabase dashboard
- API issues: Check provider status pages

---

**Remember**: Start with small batches to verify everything is working before the full run! 