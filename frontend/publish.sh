#!/bin/bash
# Usage: ./publish.sh <slug> [<audit-dir>]
# Renders the SPA for <slug> and publishes to the server directory.
# Example: ./publish.sh dsw

SLUG="${1:-dsw}"
if [ -n "$2" ]; then
  AUDIT_BASE="$2"
elif [ -n "$ALGOLIA_AUDIT_DIR" ]; then
  AUDIT_BASE="$ALGOLIA_AUDIT_DIR"
else
  echo "⚠️  ALGOLIA_AUDIT_DIR not set — using current directory fallback"
  AUDIT_BASE="$(pwd)"
fi
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORTS_DIR="$REPO_DIR/reports"
DATA_DIR="$REPORTS_DIR/data"
SCRIPTS=~/.claude/skills/algolia-search-audit/scripts
DELIV="$AUDIT_BASE/$(echo "$SLUG" | tr '[:lower:]' '[:upper:]')/deliverables"

# Handle known slug→folder mappings
case "$SLUG" in
  dsw)  COMPANY_DIR="DSW" ;;
  *)    COMPANY_DIR="$(echo "$SLUG" | sed 's/\b./\u&/g')" ;;
esac
DELIV="$AUDIT_BASE/$COMPANY_DIR/deliverables"

echo "Rendering $SLUG..."
cd "$DELIV" && deno run --allow-read --allow-write --allow-env --allow-net \
  "$SCRIPTS/render-audit.ts" "$SLUG" site 2>&1 | grep -E "✓|✗|Done|KB"

if [ $? -ne 0 ]; then
  echo "Render failed — not publishing"
  exit 1
fi

# Copy rendered files to the reports IA tree.
mkdir -p "$REPORTS_DIR/$SLUG" "$DATA_DIR"
echo "Publishing to $REPORTS_DIR/$SLUG/..."
cp "$DELIV/$SLUG/index.html" "$REPORTS_DIR/$SLUG/index.html"
cp "$DELIV/$SLUG/ae-report.html" "$REPORTS_DIR/$SLUG/ae-report.html" 2>/dev/null || true
cp "$DELIV/$SLUG/battle-card.html" "$REPORTS_DIR/$SLUG/battle-card.html" 2>/dev/null || true
cp "$DELIV/$SLUG/leave-behind.html" "$REPORTS_DIR/$SLUG/leave-behind.html" 2>/dev/null || true
cp -R "$DELIV/$SLUG/screenshots" "$REPORTS_DIR/$SLUG/screenshots" 2>/dev/null || true
cp "$DELIV/$SLUG-audit-data.json" "$DATA_DIR/$SLUG-audit-data.json" 2>/dev/null || true

echo "Done. Open: http://localhost:8766/reports/$SLUG/index.html"
