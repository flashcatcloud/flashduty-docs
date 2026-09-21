#!/usr/bin/env bash
#
# Sync documentation to Meilisearch for AI Q&A bot indexing.
#
# Every run makes the index match the docs in zh/ and en/: all docs are
# upserted (Meilisearch only re-embeds documents whose content changed) and
# index documents whose source file no longer exists are deleted.
#
# Required env vars: MEILI_ENDPOINT, MEILI_API_KEY, MEILI_INDEX
# Optional:
#   BASE_URL  - docs base URL (default: https://docs.flashduty.com)
#
# Usage:
#   bash scripts/upload.sh [--dry-run] [--help]
#
# License: Same as the repository

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

SCRIPT_NAME=$(basename "$0")
BASE_URL="${BASE_URL:-https://docs.flashduty.com}"
DRY_RUN=false
BATCH_SIZE=5
LIST_PAGE_SIZE=1000

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Sync documentation (zh/, en/) to Meilisearch for AI Q&A bot indexing:
upload every doc and delete index documents whose source file is gone.

Options:
  --dry-run    List what would be uploaded and deleted without writing
  -h, --help   Show this help

Environment variables:
  MEILI_ENDPOINT   Meilisearch instance URL (required)
  MEILI_API_KEY    API key with documents read/write permission (required)
  MEILI_INDEX      Target index name (required)
  BASE_URL         Docs base URL (default: $BASE_URL)
EOF
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown option: $arg" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "${MEILI_ENDPOINT:-}" || -z "${MEILI_API_KEY:-}" || -z "${MEILI_INDEX:-}" ]]; then
  echo "Error: MEILI_ENDPOINT, MEILI_API_KEY, and MEILI_INDEX must be set." >&2
  exit 1
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

# Clean raw MDX content for indexing: strip frontmatter, import statements and
# HTML/MDX tags, collapse whitespace. Tags are stripped after lines are joined
# so a tag whose attributes span several lines goes too; a tag must start with
# a letter or '/', which keeps comparisons like "a < b" intact.
# The whole page is indexed so keyword search sees all of it. The index's
# embedder cuts its own input in its documentTemplate
# ({{doc.content | truncate: 6000}}), so nothing here has to fit the embedding
# model's input limit.
clean_content() {
  local file=$1
  awk 'BEGIN{skip=0} NR==1 && /^---$/{skip=1;next} skip && /^---$/{skip=0;next} !skip' "$file" \
    | grep -v '^import ' \
    | tr '\n' ' ' \
    | sed -E 's/<[A-Za-z/][^<>]*>//g; s/ +/ /g'
}

# Build a JSON document for a single file
build_doc_json() {
  local file=$1
  local dir locale title doc_url id content
  dir=$(dir_for_file "$file")
  locale=$(locale_for_file "$file")
  title=$(extract_title "$file")
  doc_url=$(extract_url "$file" "$dir" "$locale")
  id=$(file_to_id "$file")
  content=$(clean_content "$file")

  # The content goes through stdin: as a --arg it would hit the kernel's
  # 128 KiB limit on a single command-line argument for a long page.
  printf '%s' "$content" | jq -Rs \
    --arg id "$id" \
    --arg title "$title" \
    --arg locale "$locale" \
    --arg url "$doc_url" \
    '{id: $id, title: $title, content: ., locale: $locale, url: $url}' 2>/dev/null
}

# Write "id<TAB>url" for every document in the index to $1. Fails unless the
# pages add up to exactly the total the index reports, so an incomplete
# listing can never drive deletions.
list_index_docs() {
  local out=$1
  local offset=0
  local total=""
  local page page_total listed

  while :; do
    if ! page=$(curl -sS --fail-with-body --connect-timeout 30 --max-time 60 \
      -H "Authorization: Bearer $MEILI_API_KEY" \
      "$MEILI_ENDPOINT/indexes/$MEILI_INDEX/documents?fields=id,url&limit=$LIST_PAGE_SIZE&offset=$offset"); then
      echo "Listing index documents failed: $page" >&2
      return 1
    fi
    if ! page_total=$(jq -er '.total' <<<"$page"); then
      echo "Unexpected listing response: $page" >&2
      return 1
    fi
    if [[ -z "$total" ]]; then
      total=$page_total
    elif [[ "$page_total" != "$total" ]]; then
      echo "Index changed while listing (total $total -> $page_total)" >&2
      return 1
    fi
    jq -r '.results[] | [.id, (.url // "")] | @tsv' <<<"$page" >> "$out" || return 1

    offset=$((offset + LIST_PAGE_SIZE))
    [[ $offset -lt $total ]] || break
  done

  listed=$(cut -f1 "$out" | sort -u | wc -l | xargs)
  if [[ "$listed" -ne "$total" ]]; then
    echo "Listed $listed unique documents but the index reports $total" >&2
    return 1
  fi
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

echo "=== Meilisearch Doc Sync ==="
echo "Index: $MEILI_INDEX"
echo "Base URL: $BASE_URL"
[[ "$DRY_RUN" == true ]] && echo "(dry-run mode — no writes)"
echo ""

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

echo "Scanning all documentation files..."
find zh en -type f \( -name "*.md" -o -name "*.mdx" \) ! -name "index.md" ! -name "index.mdx" \
  | sort > "$work_dir/files"
file_count=$(wc -l < "$work_dir/files" | xargs)
echo "Found $file_count documentation files"
if [[ $file_count -eq 0 ]]; then
  echo "Error: no documentation files found; refusing to sync an empty doc set." >&2
  exit 1
fi

while IFS= read -r file; do
  file_to_id "$file"
done < "$work_dir/files" | LC_ALL=C sort -u > "$work_dir/current_ids"

echo "Listing documents in index..."
if ! list_index_docs "$work_dir/index_docs"; then
  echo "Error: could not list the whole index; nothing was written." >&2
  exit 1
fi
echo "Index has $(wc -l < "$work_dir/index_docs" | xargs) documents"
echo ""

# Index documents with no source file in the current doc set
LC_ALL=C sort "$work_dir/index_docs" \
  | LC_ALL=C join -t $'\t' -v 1 - "$work_dir/current_ids" > "$work_dir/stale_docs"
stale_count=$(wc -l < "$work_dir/stale_docs" | xargs)

result=0

echo "--- Uploading documents ---"
upload_files "$work_dir/files" || result=1

echo ""
echo "--- Removing documents with no source file ---"
if [[ $stale_count -eq 0 ]]; then
  echo "None."
else
  while IFS=$'\t' read -r id url; do
    echo "Will delete: $url (id: $id)"
  done < "$work_dir/stale_docs"
  ids_json=$(cut -f1 "$work_dir/stale_docs" | jq -Rn '[inputs]')
  delete_documents "$ids_json" "$stale_count" || result=1
fi

echo ""
echo "All done."
exit $result
