#!/usr/bin/env bash
#
# Upload documentation to Meilisearch for AI Q&A bot indexing.
#
# Supports two modes:
#   - Incremental (default): uses git diff to upload only changed docs and
#     delete removed ones from the index.
#   - Full: scans all docs in zh/ and en/ and uploads everything.
#
# Required env vars: MEILI_ENDPOINT, MEILI_API_KEY, MEILI_INDEX
# Optional:
#   FULL_UPLOAD  - set to "true" for full re-upload (default: false)
#   BASE_URL     - docs base URL (default: https://docs.flashcat.cloud)
#
# Usage:
#   sh scripts/upload.sh [--full] [--dry-run] [--help]
#
# License: Same as the repository

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

SCRIPT_NAME=$(basename "$0")
BASE_URL="${BASE_URL:-https://docs.flashcat.cloud}"
FULL_UPLOAD="${FULL_UPLOAD:-false}"
DRY_RUN=false
BATCH_SIZE=500

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Upload documentation (zh/, en/) to Meilisearch for AI Q&A bot indexing.

Options:
  --full       Re-upload all docs (overrides FULL_UPLOAD env var)
  --dry-run    Validate and list files without uploading
  -h, --help   Show this help

Environment variables:
  MEILI_ENDPOINT   Meilisearch instance URL (required)
  MEILI_API_KEY    API key with documents write permission (required)
  MEILI_INDEX      Target index name (required)
  FULL_UPLOAD      Set to "true" for full re-upload (default: false)
  BASE_URL         Docs base URL (default: $BASE_URL)
EOF
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --full) FULL_UPLOAD=true ;;
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown option: $arg" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "$DRY_RUN" != true ]]; then
  if [[ -z "${MEILI_ENDPOINT:-}" || -z "${MEILI_API_KEY:-}" || -z "${MEILI_INDEX:-}" ]]; then
    echo "Error: MEILI_ENDPOINT, MEILI_API_KEY, and MEILI_INDEX must be set." >&2
    exit 1
  fi
fi

if ! command -v jq &> /dev/null; then
  echo "Error: jq is required. Install it first (e.g. brew install jq on macOS)." >&2
  exit 1
fi

# --- Helpers ---

# Generate a stable document ID from a file path (relative to repo root)
file_to_id() {
  local file=$1
  local rel="${file%.mdx}"
  rel="${rel%.md}"
  echo -n "$rel" | openssl md5 | awk '{print $NF}'
}

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

locale_for_file() {
  local file=$1
  if [[ "$file" == zh/* ]]; then
    echo "zh-CN"
  else
    echo "en-US"
  fi
}

dir_for_file() {
  local file=$1
  if [[ "$file" == zh/* ]]; then
    echo "zh"
  else
    echo "en"
  fi
}

is_doc_file() {
  local file=$1
  [[ "$file" == zh/*.md || "$file" == zh/*.mdx || "$file" == en/*.md || "$file" == en/*.mdx ]] || return 1
  local base
  base=$(basename "$file")
  [[ "$base" != "index.md" && "$base" != "index.mdx" ]] || return 1
  return 0
}

# Build a JSON document for a single file
build_doc_json() {
  local file=$1
  local dir locale title doc_url id
  dir=$(dir_for_file "$file")
  locale=$(locale_for_file "$file")
  title=$(extract_title "$file")
  doc_url=$(extract_url "$file" "$dir" "$locale")
  id=$(file_to_id "$file")

  jq -n \
    --arg id "$id" \
    --arg title "$title" \
    --rawfile content "$file" \
    --arg locale "$locale" \
    --arg url "$doc_url" \
    '{id: $id, title: $title, content: $content, locale: $locale, url: $url}' 2>/dev/null
}

# Upload a batch of documents (JSON array) to Meilisearch
upload_batch() {
  local payload=$1
  local count=$2

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would upload batch of $count documents"
    return 0
  fi

  local tmpfile
  tmpfile=$(mktemp)
  echo "$payload" > "$tmpfile"

  local response
  response=$(curl -sS --connect-timeout 30 --max-time 120 \
    -X POST "$MEILI_ENDPOINT/indexes/$MEILI_INDEX/documents?primaryKey=id" \
    -H "Authorization: Bearer $MEILI_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary "@$tmpfile")
  rm -f "$tmpfile"

  if echo "$response" | jq -e '.taskUid' > /dev/null 2>&1; then
    echo "Uploaded batch of $count documents (taskUid: $(echo "$response" | jq -r '.taskUid'))"
    return 0
  else
    echo "Batch upload failed" >&2
    echo "Response: $response" >&2
    return 1
  fi
}

# Delete documents from Meilisearch by IDs
delete_documents() {
  local ids_json=$1
  local count=$2

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would delete $count documents from index"
    return 0
  fi

  local tmpfile
  tmpfile=$(mktemp)
  echo "$ids_json" > "$tmpfile"

  local response
  response=$(curl -sS --connect-timeout 30 --max-time 60 \
    -X POST "$MEILI_ENDPOINT/indexes/$MEILI_INDEX/documents/delete-batch" \
    -H "Authorization: Bearer $MEILI_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary "@$tmpfile")
  rm -f "$tmpfile"

  if echo "$response" | jq -e '.taskUid' > /dev/null 2>&1; then
    echo "Deleted $count documents (taskUid: $(echo "$response" | jq -r '.taskUid'))"
    return 0
  else
    echo "Delete failed" >&2
    echo "Response: $response" >&2
    return 1
  fi
}

# Collect files into batched JSON arrays and upload
upload_files() {
  local file_list=$1
  local total_files=0
  local total_success=0
  local batch_json="["
  local batch_count=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    total_files=$((total_files + 1))

    local doc_json
    if ! doc_json=$(build_doc_json "$file"); then
      echo "JSON error: $file" >&2
      continue
    fi

    if [[ $batch_count -gt 0 ]]; then
      batch_json="${batch_json},"
    fi
    batch_json="${batch_json}${doc_json}"
    batch_count=$((batch_count + 1))

    if [[ $batch_count -ge $BATCH_SIZE ]]; then
      batch_json="${batch_json}]"
      if upload_batch "$batch_json" "$batch_count"; then
        total_success=$((total_success + batch_count))
      fi
      batch_json="["
      batch_count=0
    fi
  done < "$file_list"

  # Upload remaining
  if [[ $batch_count -gt 0 ]]; then
    batch_json="${batch_json}]"
    if upload_batch "$batch_json" "$batch_count"; then
      total_success=$((total_success + batch_count))
    fi
  fi

  echo ""
  echo "=== Upload Summary ==="
  echo "Total files: $total_files"
  echo "Uploaded: $total_success"
  echo "Failed: $((total_files - total_success))"

  [[ $total_success -eq $total_files ]] || return 1
}

# --- Main ---

echo "=== Meilisearch Doc Upload ==="
echo "Index: ${MEILI_INDEX:-<not set>}"
echo "Base URL: $BASE_URL"
echo "Mode: $([ "$FULL_UPLOAD" = "true" ] && echo "full" || echo "incremental")"
[[ "$DRY_RUN" == true ]] && echo "(dry-run mode — no uploads)"
echo ""

if [[ "$FULL_UPLOAD" == "true" ]]; then
  # Full mode: scan all docs
  echo "Scanning all documentation files..."
  temp_files=$(mktemp)
  {
    [[ -d "zh" ]] && find zh -type f \( -name "*.md" -o -name "*.mdx" \) ! -name "index.md" ! -name "index.mdx"
    [[ -d "en" ]] && find en -type f \( -name "*.md" -o -name "*.mdx" \) ! -name "index.md" ! -name "index.mdx"
  } | sort > "$temp_files"

  file_count=$(wc -l < "$temp_files" | xargs)
  echo "Found $file_count documentation files"
  echo ""

  upload_files "$temp_files"
  result=$?
  rm -f "$temp_files"
  exit $result
fi

# Incremental mode: use git diff to find changed files
if ! git rev-parse HEAD~1 > /dev/null 2>&1; then
  echo "No previous commit found — falling back to full upload"
  FULL_UPLOAD=true
  exec bash "$0" --full $([ "$DRY_RUN" = true ] && echo "--dry-run")
fi

echo "Detecting changed files since last commit..."

# Files added or modified
changed_files=$(mktemp)
git diff --name-only --diff-filter=ACMR HEAD~1 -- zh/ en/ | while IFS= read -r file; do
  is_doc_file "$file" && echo "$file"
done > "$changed_files" || true

# Files deleted
deleted_files=$(mktemp)
git diff --name-only --diff-filter=D HEAD~1 -- zh/ en/ | while IFS= read -r file; do
  is_doc_file "$file" && echo "$file"
done > "$deleted_files" || true

changed_count=$(wc -l < "$changed_files" | xargs)
deleted_count=$(wc -l < "$deleted_files" | xargs)

echo "Changed/added: $changed_count files"
echo "Deleted: $deleted_count files"
echo ""

if [[ $changed_count -eq 0 && $deleted_count -eq 0 ]]; then
  echo "No documentation changes detected. Nothing to do."
  rm -f "$changed_files" "$deleted_files"
  exit 0
fi

result=0

# Upload changed files
if [[ $changed_count -gt 0 ]]; then
  echo "--- Uploading changed documents ---"
  upload_files "$changed_files" || result=1
fi

# Delete removed files from index
if [[ $deleted_count -gt 0 ]]; then
  echo ""
  echo "--- Removing deleted documents ---"

  ids_json="["
  first=true
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    id=$(file_to_id "$file")
    if [[ "$first" == true ]]; then
      first=false
    else
      ids_json="${ids_json},"
    fi
    ids_json="${ids_json}\"${id}\""
    echo "Will delete: $file (id: $id)"
  done < "$deleted_files"
  ids_json="${ids_json}]"

  delete_documents "$ids_json" "$deleted_count" || result=1
fi

rm -f "$changed_files" "$deleted_files"

echo ""
echo "All done."
exit $result
