#!/bin/bash

# Monitor resumed Admiral Markets processing

echo "🔄 Admiral Markets Resume Monitor"
echo "================================="
echo ""

# Find the process
PID=$(ps aux | grep "run_improved_process_postgres.py.*50" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "❌ No 50-worker process found"
    exit 1
fi

echo "✅ Process running (PID: $PID)"
ps -p $PID -o etime,pcpu,pmem | tail -1
echo ""

# Blacklist stats
CURRENT=$(wc -l < data/tmp/blacklist_consolidated.csv)
echo "📈 Blacklist: $CURRENT entries (started at 1,084)"
echo ""

# Log file
LOG="data/logs/admiral_resume_50workers_20250601_172223.log"
echo "📝 Monitoring: $LOG"
echo ""

# Check for skipped already-processed
ALREADY=$(grep -c "already processed" "$LOG" 2>/dev/null || echo "0")
echo "⏭️  Already processed URLs skipped: $ALREADY"
echo ""

echo "Recent activity:"
echo "----------------"
tail -f "$LOG" | grep -E --line-buffered "Processing batch|blacklist|whitelist|Admiral Markets mentions|already processed|ERROR|url/s]" | awk '
    /already processed/ {print "\033[94m⏭️  " $0 "\033[0m"; next}
    /blacklist/ {print "\033[31m⚫ " $0 "\033[0m"; next}
    /whitelist/ {print "\033[32m⚪ " $0 "\033[0m"; next}
    /Admiral Markets mentions/ {print "\033[33m🔍 " $0 "\033[0m"; next}
    /Processing batch/ {print "\033[36m📦 " $0 "\033[0m"; next}
    /ERROR/ {print "\033[91m❌ " $0 "\033[0m"; next}
    {print "   " $0}
' 