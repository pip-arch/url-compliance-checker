#!/bin/bash

# Quick monitoring command for Admiral Markets processing

LOG_FILE="data/logs/admiral_35workers_full_20250530_083716.log"

# Monitor with color highlighting
tail -f "$LOG_FILE" | grep --line-buffered -E "Processing batch|blacklist|BLACKLIST|Category:|Admiral Markets mentions|Found [0-9]+ Admiral|ETA:|url/s\]|ERROR|✅|❌|🤖" | awk '
    /blacklist|BLACKLIST/ {print "\033[31m" $0 "\033[0m"; next}
    /whitelist|WHITELIST/ {print "\033[32m" $0 "\033[0m"; next}
    /Admiral Markets mentions|Found [0-9]+ Admiral/ {print "\033[33m" $0 "\033[0m"; next}
    /Processing batch|ETA:/ {print "\033[36m" $0 "\033[0m"; next}
    /ERROR|failed|Failed/ {print "\033[91m" $0 "\033[0m"; next}
    /✅|Successfully/ {print "\033[92m" $0 "\033[0m"; next}
    {print $0}
' 