#!/usr/bin/env bash
#
# Upload documentation to Meilisearch for AI Q&A bot indexing.
#
# Reads markdown/mdx files from zh/ and en/, formats them into JSON,
# and uploads to Meilisearch. Run from repository root, or the script
# will cd to repo root automatically.
#
# Required env vars: MEILI_ENDPOINT, MEILI_API_KEY, MEILI_INDEX
# Optional: BASE_URL (default https://docs.flashcat.cloud)
#
# Usage:
#   sh scripts/upload.sh [--dry-run] [--help]
#
# License: Same as the repository

set -euo pipefail

# Ensure we run from repo root (parent of scripts/)
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

# --- Constants ---
SCRIPT_NAME=$(basename "$0")
BASE_URL="${BASE_URL:-https://docs.flashcat.cloud}"
DRY_RUN=false

# --- Help ---
usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Upload documentation (zh/, en/) to Meilisearch for AI Q&A bot indexing.

Options:
  --dry-run    Validate and list files without uploading
  -h, --help   Show this help

Environment variables:
  MEILI_ENDPOINT   Meilisearch instance URL (required)
  MEILI_API_KEY    API key with documents write permission (required)
  MEILI_INDEX      Target index name (required)
  BASE_URL         Docs base URL for link construction (default: $BASE_URL)

Examples:
  MEILI_ENDPOINT=https://meilisearch.example.com \\
  MEILI_API_KEY=xxx MEILI_INDEX=docs sh scripts/upload.sh

  sh scripts/upload.sh --dry-run
EOF
}

# --- Argument parsing ---
for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# --- Validation ---
if [[ "$DRY_RUN" != true ]]; then
  if [[ -z "${MEILI_ENDPOINT:-}" || -z "${MEILI_API_KEY:-}" || -z "${MEILI_INDEX:-}" ]]; then
    echo "Error: MEILI_ENDPOINT, MEILI_API_KEY, and MEILI_INDEX must be set." >&2
    echo "Run with --help for usage." >&2
    exit 1
  fi
fi

if ! command -v jq &> /dev/null; then
  echo "Error: jq is required. Install it first (e.g. brew install jq on macOS)." >&2
  exit 1
fi

# --- Counters ---
total_success=0
total_files=0
total_errors=0

# --- Upload a single document ---
upload_document() {
  local json_payload=$1
  local title=$2

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would upload: $title"
    return 0
  fi

  local response
  response=$(curl -sS --connect-timeout 30 --max-time 60 -X POST "$MEILI_ENDPOINT/indexes/$MEILI_INDEX/documents?primaryKey=id" \
    -H "Authorization: Bearer $MEILI_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary "$json_payload")

  if [[ -z "$response" ]]; then
    echo "Upload failed: $title (empty response)" >&2
    return 1
  fi

  if echo "$response" | jq -e '.taskUid' > /dev/null 2>&1; then
    echo "Uploaded: $title"
    return 0
  else
    echo "Upload failed: $title" >&2
    echo "Response: $response" >&2
    return 1
  fi
}

# --- Extract title from frontmatter or filename ---
extract_title() {
  local file=$1
  local title
  title=$(grep -m 1 '^title:' "$file" 2>/dev/null | sed -n 's/title: *"\(.*\)"/\1/p') || true
  if [[ -z "${title:-}" ]]; then
    title=$(grep -m 1 '^title:' "$file" 2>/dev/null | sed -n 's/title: *\(.*\)$/\1/p' | xargs) || true
  fi
  if [[ -z "${title:-}" ]]; then
    local base
    base=$(basename "$file")
    title="${base%.mdx}"
    title="${title%.md}"
    title=$(echo "$title" | sed 's/^[0-9.]*[[:space:]]*//')
  fi
  echo "$title"
}

# --- Extract URL from frontmatter or construct from path ---
extract_url() {
  local file=$1
  local dir=$2
  local locale=$3
  local doc_url
  doc_url=$(grep -m 1 '^url:' "$file" 2>/dev/null | sed -n 's/url: *"\(.*\)"/\1/p') || true
  if [[ -z "${doc_url:-}" ]]; then
    doc_url=$(grep -m 1 '^url:' "$file" 2>/dev/null | sed -n 's/url: *\(.*\)$/\1/p' | xargs) || true
  fi
  if [[ -z "${doc_url:-}" ]]; then
    local rel_path
    rel_path="${file#$dir/}"
    rel_path="${rel_path%.mdx}"
    rel_path="${rel_path%.md}"
    local locale_prefix
    [[ "$locale" == "zh-CN" ]] && locale_prefix="zh" || locale_prefix="en"
    doc_url="${BASE_URL}/${locale_prefix}/${rel_path}"
  fi
  echo "$doc_url"
}

# --- Process a directory ---
process_directory() {
  local dir=$1
  local locale=$2
  local temp_success temp_error temp_total

  echo "Processing $dir/..."

  temp_success=$(mktemp)
  temp_error=$(mktemp)
  temp_total=$(mktemp)
  echo "0" > "$temp_success"
  echo "0" > "$temp_error"
  echo "0" > "$temp_total"

  temp_files=$(mktemp)
  find "$dir" -type f \( -name "*.md" -o -name "*.mdx" \) ! -name "index.md" ! -name "index.mdx" > "$temp_files"

  while IFS= read -r file; do
    local title doc_url rel_path id json_payload
    title=$(extract_title "$file")
    doc_url=$(extract_url "$file" "$dir" "$locale")

    rel_path="${file#$dir/}"
    rel_path="${rel_path%.mdx}"
    rel_path="${rel_path%.md}"
    id=$(echo -n "${dir}/${rel_path}" | openssl md5 | awk '{print $NF}')

    if json_payload=$(jq -n \
      --arg id "$id" \
      --arg title "$title" \
      --rawfile content "$file" \
      --arg locale "$locale" \
      --arg url "$doc_url" \
      '{id: $id, title: $title, content: $content, locale: $locale, url: $url}' 2>/dev/null); then

      if upload_document "$json_payload" "$title"; then
        echo $(($(cat "$temp_success") + 1)) > "$temp_success"
      else
        echo $(($(cat "$temp_error") + 1)) > "$temp_error"
      fi
    else
      echo "JSON error: $title ($file)" >&2
      echo $(($(cat "$temp_error") + 1)) > "$temp_error"
    fi

    echo $(($(cat "$temp_total") + 1)) > "$temp_total"
    echo "Progress: $(cat "$temp_total") files"
  done < "$temp_files"
  rm -f "$temp_files"

  local final_success final_error final_total
  final_success=$(cat "$temp_success")
  final_error=$(cat "$temp_error")
  final_total=$(cat "$temp_total")

  total_success=$((total_success + final_success))
  total_errors=$((total_errors + final_error))
  total_files=$((total_files + final_total))

  echo "Done $dir/: $final_success ok, $final_error failed"
  rm -f "$temp_success" "$temp_error" "$temp_total"
}

# --- Main ---
echo "Uploading docs to Meilisearch index: ${MEILI_INDEX:-<not set>}"
echo "Base URL: $BASE_URL"
echo "Working directory: $(pwd)"
[[ "$DRY_RUN" == true ]] && echo "(dry-run mode - no uploads)"
echo ""

if [[ -d "zh" ]]; then
  process_directory "zh" "zh-CN"
else
  echo "Warning: zh/ directory not found"
fi

if [[ -d "en" ]]; then
  process_directory "en" "en-US"
else
  echo "Warning: en/ directory not found"
fi

echo ""
echo "=== Summary ==="
echo "Total files: $total_files"
echo "Uploaded: $total_success"
echo "Failed: $total_errors"

if [[ $total_files -gt 0 ]]; then
  success_rate=$((total_success * 100 / total_files))
  echo "Success rate: ${success_rate}%"
fi

if [[ $total_errors -gt 0 ]]; then
  echo "Some uploads failed. Check errors above."
  exit 1
fi

echo "All done."
