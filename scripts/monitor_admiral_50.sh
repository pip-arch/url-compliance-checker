#!/bin/bash

# Enhanced monitoring for Admiral Markets 50-worker processing

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Find the latest log
LOG_FILE=$(ls -t data/logs/admiral_50workers_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo -e "${RED}❌ No active processing log found${NC}"
    exit 1
fi

echo -e "${BLUE}📊 Admiral Markets Processing Monitor (50 Workers)${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Function to get stats
get_stats() {
    # Process info
    local PID=$(ps aux | grep -E "python.*improved_process.*50" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        echo -e "${GREEN}✅ Process Active${NC} (PID: $PID)"
        ps -p $PID -o etime,pcpu,pmem | tail -1
    else
        echo -e "${RED}❌ Process Not Running${NC}"
    fi
    
    echo ""
    
    # Blacklist growth
    local CURRENT=$(wc -l < data/tmp/blacklist_consolidated.csv)
    local BEFORE=933
    local NEW=$((CURRENT - BEFORE))
    echo -e "${GREEN}📈 Blacklist Growth:${NC}"
    echo -e "   Before: $BEFORE → Current: $CURRENT (${YELLOW}+$NEW${NC})"
    
    echo ""
    
    # Processing stats
    echo -e "${GREEN}📊 Processing Stats:${NC}"
    local PROCESSED=$(grep -c "Processing https" "$LOG_FILE" 2>/dev/null || echo "0")
    local SKIPPED=$(grep -c "Skipping" "$LOG_FILE" 2>/dev/null || echo "0")
    local ADMIRAL_FOUND=$(grep -c "Found [0-9]* Admiral Markets mentions" "$LOG_FILE" 2>/dev/null || echo "0")
    local ERRORS=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo "0")
    
    echo -e "   URLs Processed: $PROCESSED"
    echo -e "   URLs Skipped: $SKIPPED"
    echo -e "   Admiral Mentions Found: $ADMIRAL_FOUND"
    echo -e "   Errors: ${RED}$ERRORS${NC}"
    
    echo ""
    
    # Recent activity
    echo -e "${GREEN}📜 Recent Activity:${NC}"
    tail -100 "$LOG_FILE" | grep -E "blacklist|whitelist|review|Admiral Markets mentions|Processing batch" | tail -5
    
    echo ""
    
    # Speed estimate
    local LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    local LOG_AGE=$(stat -f%m "$LOG_FILE" 2>/dev/null || stat -c%Y "$LOG_FILE" 2>/dev/null)
    local CURRENT_TIME=$(date +%s)
    local RUNTIME=$((CURRENT_TIME - LOG_AGE))
    
    if [ $RUNTIME -gt 0 ] && [ $PROCESSED -gt 0 ]; then
        local SPEED=$(echo "scale=2; $PROCESSED / ($RUNTIME / 60)" | bc)
        echo -e "${GREEN}⚡ Speed:${NC} ~$SPEED URLs/minute"
    fi
}

# Continuous monitoring
while true; do
    clear
    get_stats
    echo ""
    echo -e "${YELLOW}Refreshing every 5 seconds... (Ctrl+C to exit)${NC}"
    sleep 5
done 