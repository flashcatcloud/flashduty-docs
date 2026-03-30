#!/bin/bash
# Scheduled doc-review audit via Claude Code CLI.
# Runs locally where skills and source repos are available.
#
# Usage:
#   ./scripts/doc-review-cron.sh                    # default: diff mode, 2 weeks
#   ./scripts/doc-review-cron.sh audit on-call       # audit mode, scoped to on-call
#   ./scripts/doc-review-cron.sh diff "" "1 week ago" # diff mode, custom time range

set -euo pipefail

DOCS_DIR="$HOME/go/src/github.com/flashcatcloud/flashduty-docs"
LOG_DIR="$DOCS_DIR/.doc-review/logs"
CLAUDE="$HOME/.local/bin/claude"

MODE="${1:-diff}"
SCOPE="${2:-}"
SINCE="${3:-2 weeks ago}"

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/$(date +%Y-%m-%d-%H%M%S).log"

SCOPE_ARG=""
if [ -n "$SCOPE" ]; then
  SCOPE_ARG="--scope $SCOPE"
fi

echo "$(date): Starting doc-review (mode=$MODE, scope=$SCOPE, since=$SINCE)" | tee "$LOGFILE"

cd "$DOCS_DIR"

# Pull latest docs before reviewing
git pull --rebase origin main >> "$LOGFILE" 2>&1 || true

echo "/doc-review --mode $MODE --since \"$SINCE\" $SCOPE_ARG --auto" | \
  $CLAUDE --print \
  --allowedTools "Read,Glob,Grep,Write,Edit,Bash,Agent,Skill" \
  >> "$LOGFILE" 2>&1

echo "$(date): Done. Log: $LOGFILE"
