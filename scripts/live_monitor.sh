#!/bin/bash

# Admiral Markets Live Processing Monitor
# This script provides a comprehensive view of the processing status

# Colors for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Find the latest log file
LOG_FILE=$(ls -t data/logs/admiral_35workers_full_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "❌ No active processing log found"
    exit 1
fi

# Clear screen and set up monitoring
clear

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        🚀 Admiral Markets Live Processing Monitor 🚀         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to get process info
get_process_info() {
    local PID=$(lsof "$LOG_FILE" 2>/dev/null | grep Python | head -1 | awk '{print $2}')
    if [ -n "$PID" ]; then
        ps -p $PID -o pid,etime,pcpu,pmem 2>/dev/null | tail -1
    else
        echo "No process found"
    fi
}

# Function to get blacklist stats
get_blacklist_stats() {
    local CURRENT=$(wc -l < data/tmp/blacklist_consolidated.csv)
    local BEFORE=933
    local NEW=$((CURRENT - BEFORE))
    echo -e "${GREEN}Blacklist Growth:${NC} Before: $BEFORE → Current: $CURRENT (${YELLOW}+$NEW${NC})"
}

# Main monitoring loop
while true; do
    # Move cursor to top
    tput cup 7 0
    
    # Process Status
    echo -e "${PURPLE}━━━ Process Status ━━━${NC}"
    echo -e "$(get_process_info)"
    echo ""
    
    # Blacklist Stats
    get_blacklist_stats
    echo ""
    
    # Latest Activity (last 20 lines, filtered)
    echo -e "${PURPLE}━━━ Latest Activity ━━━${NC}"
    tail -20 "$LOG_FILE" | grep -E --color=always "Processing batch|blacklist|Category:|Admiral Markets mentions|Found [0-9]+ Admiral|ETA:|url/s\]" || echo "Waiting for relevant activity..."
    
    # Stats Summary (if available)
    echo -e "\n${PURPLE}━━━ Recent Stats ━━━${NC}"
    tail -100 "$LOG_FILE" | grep -E "blacklisted.*whitelisted.*review" | tail -1 || echo "No recent stats"
    
    # Progress indicator
    echo -e "\n${PURPLE}━━━ Current Progress ━━━${NC}"
    tail -200 "$LOG_FILE" | grep -E "Processing URLs.*ETA" | tail -1 || echo "Calculating..."
    
    # Refresh every 2 seconds
    sleep 2
done 