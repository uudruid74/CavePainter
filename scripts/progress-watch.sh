#!/usr/bin/env bash
# gopher-draw-progress — Poll kanban and report gopher-draw task status
# Runs as a cron job, reports to Telegram when things change.

set -euo pipefail

BOARD="gopher-draw"
STATE_FILE="/tmp/gopher-draw-progress.state"
OUTPUT=""

# Get current task list
TASKS=$(hermes kanban list 2>&1 | grep -E "t_b328631b|t_e2cc67b0|t_494f40b0|t_09cbd866|t_f3b51d0a|t_d54a752f|t_e486a6bf" || true)

if [ -z "$TASKS" ]; then
    echo "No gopher-draw tasks found — maybe board needs switching"
    exit 0
fi

# Build a summary
SUMMARY=$(echo "$TASKS" | awk '{
    status = $2
    id = $1
    title = ""
    for(i=4;i<=NF;i++) title = title $i " "
    if (status == "?") status = "triage"
    else if (status == "⊘") status = "blocked"
    printf "%s|%s|%s\\n", id, status, title
}')

# Check for state changes since last run
if [ -f "$STATE_FILE" ]; then
    OLD_SUMMARY=$(cat "$STATE_FILE")
    if [ "$SUMMARY" != "$OLD_SUMMARY" ]; then
        # Something changed! Build a diff
        CHANGES=$(diff <(echo "$OLD_SUMMARY") <(echo "$SUMMARY") || true)
        if [ -n "$CHANGES" ]; then
            OUTPUT="🖌️ **Gopher Draw Progress Update**\n\n"
            while IFS= read -r line; do
                ID=$(echo "$line" | awk '{print $2}' | tr -d '><')
                
                # Get current status
                STATUS=$(hermes kanban list 2>&1 | grep "$ID" | awk '{print $2}')
                TITLE=$(hermes kanban list 2>&1 | grep "$ID" | awk '{$1=$2=""; print $0}' | sed 's/^ *//')
                
                STATUS_ICON="?"
                [ "$STATUS" = "✓" ] && STATUS_ICON="✅"
                [ "$STATUS" = "⊘" ] && STATUS_ICON="🚫"
                [ "$STATUS" = "▶" ] && STATUS_ICON="▶️"
                [ "$STATUS" = "⏱" ] && STATUS_ICON="⏱️"
                [ "$STATUS" = "?" ] && STATUS_ICON="❓"
                
                OUTPUT="${OUTPUT}${STATUS_ICON} ${TITLE:0:60}\n"
            done <<< "$CHANGES"
            
            # Check if we should celebrate
            ALL_DONE=$(echo "$SUMMARY" | grep -c "^[^|]*|✓|" || true)
            echo "All done count: $ALL_DONE"
            
            echo -e "$OUTPUT"
        fi
    fi
fi

# Save current state
echo "$SUMMARY" > "$STATE_FILE"

# If all 7 tasks are done, deliver a celebration
DONE_COUNT=$(echo "$SUMMARY" | grep -c "✓" || true)
TOTAL_COUNT=$(echo "$SUMMARY" | wc -l)
if [ "$DONE_COUNT" -eq "$TOTAL_COUNT" ] && [ "$DONE_COUNT" -gt 0 ]; then
    echo "ALL TASKS DONE — Time for Plato's Cave! 🖌️🐹"
fi
