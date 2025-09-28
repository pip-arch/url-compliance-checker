#!/bin/bash

# Simple monitoring for clean Admiral Markets processing

echo "🔍 Admiral Markets Clean Processing Monitor"
echo "=========================================="
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
echo "📈 Blacklist: $CURRENT entries (started at 987)"
echo ""

# Find latest log
LOG=$(ls -t data/logs/admiral_clean_50workers_*.log 2>/dev/null | head -1)
if [ -z "$LOG" ]; then
    LOG=$(ls -t data/logs/*.log | head -1)
fi

echo "📝 Monitoring log: $(basename $LOG)"
echo ""
echo "Recent activity:"
echo "----------------"
tail -f "$LOG" | grep -E --line-buffered "Processing batch|blacklist|whitelist|Admiral Markets mentions|ERROR|url/s]|Successfully processed" | awk '
    /blacklist/ {print "\033[31m⚫ " $0 "\033[0m"; next}
    /whitelist/ {print "\033[32m⚪ " $0 "\033[0m"; next}
    /Admiral Markets mentions/ {print "\033[33m🔍 " $0 "\033[0m"; next}
    /Processing batch/ {print "\033[36m📦 " $0 "\033[0m"; next}
    /ERROR/ {print "\033[91m❌ " $0 "\033[0m"; next}
    /Successfully/ {print "\033[92m✅ " $0 "\033[0m"; next}
    {print "   " $0}
' 