#!/bin/bash

# Monitor Admiral Markets processing progress

echo "📊 Admiral Markets Processing Monitor"
echo "===================================="
echo ""

# Find the latest log file
LOG_FILE=$(ls -t data/logs/admiral_35workers_full_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "❌ No active processing log found"
    exit 1
fi

echo "📝 Log file: $LOG_FILE"
echo ""

# Get current stats
echo "📈 Current Progress:"
tail -1000 "$LOG_FILE" | grep -E "Processing URLs.*ETA" | tail -1

echo ""
echo "📊 Latest Results:"
tail -1000 "$LOG_FILE" | grep -E "blacklisted.*whitelisted.*review" | tail -5

echo ""
echo "🔢 Blacklist Growth:"
BEFORE=933
CURRENT=$(wc -l < data/tmp/blacklist_consolidated.csv)
NEW=$((CURRENT - BEFORE))
echo "  Before: $BEFORE URLs"
echo "  Current: $CURRENT URLs"
echo "  New: +$NEW URLs"

echo ""
echo "⏰ Processing Rate:"
tail -1000 "$LOG_FILE" | grep -E "url/s\]|it/s\]" | tail -5

echo ""
echo "🔄 To watch live:"
echo "   tail -f $LOG_FILE | grep -E 'Processing|blacklist|Category|Admiral'"
echo ""
echo "📊 To monitor blacklist:"
echo "   watch -n 30 'wc -l data/tmp/blacklist_consolidated.csv'" 