#!/bin/bash

# Continue URL processing with more workers for speed
echo "🚀 Continuing URL processing with increased workers..."
echo "=" * 60

# Use 40 workers (double the previous 20)
WORKERS=40
BATCH_SIZE=200  # Larger batches for efficiency

echo "Configuration:"
echo "  Workers: $WORKERS (was 20)"
echo "  Batch size: $BATCH_SIZE (was 100)"
echo ""

# The filtered URLs are already in data/tmp/filtered_urls.csv
echo "📊 Processing remaining URLs from filtered list..."

python scripts/run_improved_process_postgres.py \
  --file data/tmp/filtered_urls.csv \
  --column url \
  --batch-size $BATCH_SIZE \
  --workers $WORKERS \
  --offset 100  # Skip the first 100 URLs that were already processed

echo ""
echo "✅ Started processing with $WORKERS workers!" 