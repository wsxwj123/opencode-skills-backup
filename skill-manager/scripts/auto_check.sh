#!/bin/bash
# auto_check.sh - Mac/Linux Compatible Script

LOG_FILE="$HOME/.config/opencode/skills/skill-manager/data/automation.log"
REPORT_FILE="$HOME/.config/opencode/skills/skill-manager/data/latest_weekly_report.json"
PYTHON_SCRIPT="$HOME/.config/opencode/skills/skill-manager/scripts/scan_and_check.py"
TARGET_DIR="$HOME/.config/opencode/skills"

# Timestamp
DATE=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$DATE] Starting weekly skill check (Mac)..." >> "$LOG_FILE"

# Determine python command
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Execute
"$PYTHON_CMD" "$PYTHON_SCRIPT" "$TARGET_DIR" > "$REPORT_FILE" 2>> "$LOG_FILE"

echo "[$DATE] Check completed. Report saved to $REPORT_FILE" >> "$LOG_FILE"
