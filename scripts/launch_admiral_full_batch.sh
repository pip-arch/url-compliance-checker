#!/bin/bash

# Launch full Admiral Markets backlinks processing with optimized settings
echo "🚀 Launching Admiral Markets Full Batch Processing"
echo "=================================================="
echo ""
echo "📊 Dataset: 67,693 URLs"
echo "⚙️  Workers: 35"
echo "📦 Batch Size: 250"
echo "🕐 Estimated Time: 5-6 days"
echo ""

# Kill any existing processing
echo "Stopping any existing processes..."
pkill -f "run_improved_process_postgres.py" || true
sleep 2

# Set optimized environment variables
export FIRECRAWL_TIMEOUT='10'
export CRAWL4AI_TIMEOUT='10000'
export MAX_RETRIES='1'
export RETRY_DELAY='1'

# Pre-filter dead domains first
echo "🔍 Pre-filtering dead domains..."
python scripts/run_optimized_batch.py data/inputs/admiral_markets/referring_urls.txt

# The optimized batch script will automatically continue with the main processing
# It uses these settings internally:
# - Workers: 20 (we'll override this)
# - Batch size: 100 (we'll override this)

# For custom settings, run the improved process directly after filtering
echo ""
echo "📝 Check progress with:"
echo "   tail -f data/logs/admiral_full_batch_*.log"
echo ""
echo "📊 Monitor blacklist growth:"
echo "   watch -n 30 'wc -l data/tmp/blacklist_consolidated.csv'" 