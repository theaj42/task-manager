#!/bin/bash
#
# task-manager auto-sync
# Runs daily at 0400 to prepare the day's tasks
#
# Workflow:
# 1. Sync completions from yesterday (if any checkboxes were checked)
# 2. Update today's daily note with fresh task recommendations
# 3. Update the Task Dashboard for manual curation

cd "$(dirname "$0")"

LOG_FILE="logs/auto-sync.log"
mkdir -p logs

echo "=== task-manager auto-sync: $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# 1. Sync completions from daily note
echo "[$(date '+%H:%M:%S')] Running sync-completions..." >> "$LOG_FILE"
./task-manager.py sync-completions >> "$LOG_FILE" 2>&1

# 2. Update daily note with today's tasks
echo "[$(date '+%H:%M:%S')] Running sync-daily..." >> "$LOG_FILE"
./task-manager.py sync-daily >> "$LOG_FILE" 2>&1

# 3. Update Task Dashboard
echo "[$(date '+%H:%M:%S')] Running sync-dashboard..." >> "$LOG_FILE"
./task-manager.py sync-dashboard >> "$LOG_FILE" 2>&1

echo "[$(date '+%H:%M:%S')] Auto-sync complete" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
