#!/usr/bin/env bash
# gopher-draw-progress.notify — watches kanban and delivers changes
# Runs every 30 min via cron. Silently exits unless a state change is detected.

set -euo pipefail

BOARD="gopher-draw"
STATE_FILE="/tmp/.gopher-draw-progress-state"

# Switch to board
hermes kanban boards switch "$BOARD" 2>/dev/null || true

# Get current tasks
CURRENT=$(hermes kanban list 2>&1 | grep -E "t_b328631b|t_e2cc67b0|t_494f40b0|t_09cbd866|t_f3b51d0a|t_d54a752f|t_e486a6bf" || true)

if [ -z "$CURRENT" ]; then
    exit 0
fi

# Compare with previous state
if [ -f "$STATE_FILE" ]; then
    PREVIOUS=$(cat "$STATE_FILE")
    if [ "$CURRENT" = "$PREVIOUS" ]; then
        exit 0  # No changes — silent exit
    fi
fi

# Save state
echo "$CURRENT" > "$STATE_FILE"

# Build status report
REPORT="🖌️ **Gopher Draw — Progress Update**"
while IFS= read -r line; do
    STATUS=$(echo "$line" | awk '{print $2}')
    TITLE=$(echo "$line" | awk '{$1=$2=""; print $0}' | sed 's/^ *//')
    case "$STATUS" in
        "?") ICON="❓";;
        "⊘") ICON="🚫";;
        "✓") ICON="✅";;
        "▶") ICON="▶️";;
        "⏱") ICON="⏱️";;
        *) ICON="❓";;
    esac
    REPORT="$REPORT\n$ICON $TITLE"
done <<< "$CURRENT"

echo -e "$REPORT"
