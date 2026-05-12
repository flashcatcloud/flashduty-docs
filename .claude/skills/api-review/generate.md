# Generate phase

Goal: turn a reviewed findings file into updates to the **per-module OpenAPI 3.1 files** that Mintlify reads (e.g., `api-reference/on-call.openapi.en.json`), and keep the consolidated reference copies (`openapi.en.json`, `openapi.zh.json`) in sync.

## File layout (critical — read first)

Mintlify reads **per-module split files**, not the consolidated files. `docs.json` wires each product tab to its own spec (e.g., `"openapi": "api-reference/on-call.openapi.zh.json"`). The consolidated `openapi.en.json` / `openapi.zh.json` exist for Apifox import and cross-module audits, but changes to them alone will NOT appear on the docs site.

Scoped runs (`--scope on-call/template`) **merge into** the per-module file for that scope's module (determined by `mapping.yaml`), replacing operations and schemas that belong to the scope and leaving everything else alone. Then the consolidated files are updated with the same merge.

## Inputs

- Findings YAML from phase 1 (either explicitly given via `--findings <path>` or the most recent one matching `--scope`).
- Source repos synced to the commit recorded in `source_registry_commit`. Warn if the repo has moved forward — the user may want to re-analyze first.
- `mapping.yaml` for the envelope, server URL, and security scheme references.

## Core contract — EN and ZH files are twins

Each module's EN and ZH files are *structurally identical*. They share:

- `paths.*` — same keys, same operations, same operation IDs.
- `components.schemas.*` — same keys, same property keys.
- `components.securitySchemes.*`, top-level `security`, `servers`, `webhooks`.

They diverge only on human-facing text:

- `info.title`, `info.description`
- `tags[*].name` (tag key is the English string; we use the same key in both files but the displayed name is localized via `tags[*].name` + per-operation `tags` arrays)
- Operation `summary` and `description`
- Schema property `title` and `description`

Generate English first, then derive the Chinese file by copying the English output and overwriting just those text fields. This guarantees structural parity without any risk of drift.

## Step 1 — load or build the skeleton

Determine the per-module file from the scope (e.g., `--scope on-call/template` → `on-call.openapi.en.json`). If it exists, load it as the working document. Otherwise build it fresh:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Flashduty Open API",
    "description": "Public HTTP API for the Flashduty platform — incidents, channels, schedules, monitors, RUM, and platform administration. Every operation is authenticated with an `app_key` query parameter issued from the Flashduty console.",
    "version": "1.0.0"
  },
  "servers": [
    { "url": "https://api.flashcat.cloud", "description": "Flashduty Open API" }
  ],
  "security": [
    { "AppKeyAuth": [] }
  ],
  "tags": [],
  "paths": {},
  "components": {
    "securitySchemes": {
      "AppKeyAuth": {
        "type": "apiKey",
        "in": "query",
        "name": "app_key",
        "description": "App key issued from the Flashduty console under Account → APP Keys. Required on every public API call."
      }
    },
    "responses": {},
    "schemas": {}
  }
}
```

The Chinese spec uses the same layout with `info.title` set to `"Flashduty 开放 API"` and `info.description` translated.

The top-level `tags` array accumulates every `<parent>/<module>` label used by any operation — merge, don't replace. Only add an entry when its name isn't already present.

## Step 2 — inject (or refresh) the shared envelope schemas

Every endpoint reuses four shared schemas: `ResponseEnvelope`, `ErrorResponse`, `DutyError`, `ErrorCode`. Define them once in `components.schemas`. Use the exact shapes in `references/response-envelope.md` — in particular, `ErrorCode` is a **string** enum with 20 named values (`InvalidParameter`, `AccessDenied`, ...), not an integer, and `DutyError` has exactly two fields: `code` (ref to `ErrorCode`) and `message`. No `raw_message` — that's an internal server field, not part of the public contract.

Also inject the shared responses in `components.responses`: `BadRequest`, `Unauthorized`, `Forbidden`, `NotFound`, `TooManyRequests`, `ServerError`. Each one includes a realistic `examples` block showing the concrete error shape consumers will receive.

If the loaded file already has any of these schemas/responses, **replace them** with the canonical versions from `references/response-envelope.md`. Drift here has caused real issues (see the pilot round-1 bug where a nonexistent `i18n_key` field was surfaced).

## Step 2.5 — scope merge: remove stale operations and schemas

Before adding new operations, prune anything from the previous state that belonged to the scope being regenerated:

1. Collect every operation in the current file whose `x-apifox-folder` matches the scope's tag (e.g., `"On-call/Templates"`). Remove those paths from `paths`.
2. After removing, walk every remaining operation and collect the set of schema names referenced via `$ref`.
3. Also add the envelope schemas (`ResponseEnvelope`, `DutyError`, `ErrorCode`, `ErrorResponse`) to the keep-set — they're used by references even though they're not referenced by any schema property directly.
4. Delete every schema in `components.schemas` that is *not* in the keep-set.
5. Repeat the reference walk until the keep-set stabilizes (a schema can reference another schema via `$ref` inside its properties).

This GC step is how partial regenerations stay safe: when you remove an operation, any schema that was only used by that operation disappears with it. Schemas shared across scopes survive because other operations still reference them.

## Step 3 — emit one path item per operation

For each `operations[]` entry in findings:

1. **Read the handler file** at `<repo>/<handler.file>`. Also read any struct files referenced by `input_type` and `output_type` (typically in the same package or under `structs/`, `model/`).
2. **Extract the input schema.** Walk the `input_type` struct recursively. Honor Go tags:
   - `json:"field_name"` is the property key. `json:"-"` means skip.
   - `binding:"required"` → add to `required`.
   - `binding:"max=N,min=N"` → `maximum`/`minimum` for numbers, `maxLength`/`minLength` for strings.
   - `binding:"oneof=a b c"` → `enum: [a, b, c]`.
   - Embedded structs → inline properties at the same level.
   - `*SomeStruct` and `SomeStruct` both produce an object type; nilability is expressed by presence in `required`, not by `nullable`.
   - Slices → `type: array` with item schema.
   - `map[string]X` → `type: object` with `additionalProperties` set to X's schema.
   - Types with a `gorm:"serializer:json"` tag are still serialized as JSON — walk them like normal structs.
   - `primitive.ObjectID` → `type: string` with a short description noting it's a MongoDB ObjectID hex.
   - `time.Time` → `type: string, format: date-time`.
   - `apidoc:"omit"` → **skip the field entirely.** Do not emit it in the schema. Also skip fields with a `// deprecated` comment above them.
   - `orderby` and similar sort/filter selector fields → always extract enum values from the handler's validation logic (e.g., `switch input.OrderBy` cases or `oneof` binding). Never leave sort fields as free-form strings.
   - **Polymorphic fields** (typed as `interface{}`, `map[string]any`, or a generic struct whose shape depends on a sibling enum like `kind` or `type`): emit `oneOf` with a `discriminator` on the enum field, listing all concrete sub-schemas. Never leave these as bare `{type: object}`.
3. **Extract the output schema.** Same walking rules, but start from `output_type`. If `handler.output_type == "inline"`, build the schema from the recorded inline field map. If the output type is a slice, wrap it: `type: array, items: {$ref: ...}`. If the output type is a known pagination wrapper (e.g., `pgy.ListResult[T]`), emit a small wrapper schema: `{items: [T], total: integer}`.
4. **Register named schemas** in `components.schemas.<TypeName>`. Use the Go type name verbatim (drop the package prefix and pointer). If two different Go types would collide on name, prefix with package name (`incident.Item` → `IncidentItem`).
5. **Emit the path operation:**

```json
{
  "<method>": {
    "operationId": "<kebab-case name>",   // e.g., "template-read-info"
    "summary": "<NameCN for zh, translated EN for en>",
    "description": "<Description from registry, or handler doc comment, or empty>",
    "tags": ["<parent>/<tag>"],
    "x-apifox-folder": "<parent>/<tag>",
    "x-apifox-slug": "<kebab-case name>",
    "security": [{ "AppKeyAuth": [] }],
    "requestBody": {
      "required": true,
      "content": {
        "application/json": {
          "schema": { "$ref": "#/components/schemas/<InputName>" }
        }
      }
    },
    "responses": {
      "200": {
        "description": "Success",
        "content": {
          "application/json": {
            "schema": {
              "allOf": [
                { "$ref": "#/components/schemas/ResponseEnvelope" },
                {
                  "type": "object",
                  "properties": {
                    "data": { "$ref": "#/components/schemas/<OutputName>" }
                  }
                }
              ]
            }
          }
        }
      },
      "400": { "$ref": "#/components/responses/BadRequest" },
      "401": { "$ref": "#/components/responses/Unauthorized" },
      "500": { "$ref": "#/components/responses/ServerError" }
    }
  }
}
```

For GET operations, use query `parameters` instead of `requestBody`, derived from the input struct.

### Request and response examples

Every operation **must** include realistic examples. These are not optional — they power Mintlify's code snippet previews, Apifox's "Try It Now" button, and the context LLM agents see when reasoning about API usage.

**Request example** — set `requestBody.content["application/json"].example`:

- Build from the input schema: populate every `required` field with a plausible value, plus 1–2 common optional fields.
- Use realistic values: real-looking 24-char hex ObjectIDs, meaningful names, valid ISO timestamps. Never use `"string"` or `"example"` placeholders.
- For list operations, include typical filter/pagination params (`page_size: 10`).

**Response example** — set `responses.200.content["application/json"].example`:

- Wrap in the standard envelope: `{"request_id": "01J...", "data": <payload>}`.
- The `data` payload should match the output schema with realistic field values.
- For list operations, include 1–2 items in the `items` array and a plausible `total`.
- Omit `error` from 200 examples (success responses don't carry it).

**Capturing real examples from the dev API:**

When generating for the first time, capture real 200 responses from the dev environment to use as response examples:

```bash
curl -s "https://api-dev.flashcat.cloud<path>?app_key=${FLASHDUTY_APP_KEY}" \
  -H "Content-Type: application/json" -d '<minimal-request-body>'
```

Extract the `.data` portion from the response envelope. For list operations, trim `items` to 1–2 entries. Skip destructive operations (delete/remove) on resources you didn't create.

**Use captures to validate schemas:** If the real response reveals fields missing from your schema, wrong types, or unexpected enum values, fix the schema first, then use the response as the example. Real API responses are the best schema validation tool — treat each capture as a test.

If the dev API is unavailable or the operation has side effects, construct a synthetic example from the output schema instead — but prefer real data when possible.

**Bilingual examples:** Request and response examples use the same values in both EN and ZH files — field keys and values are always English (they're API payloads, not UI text). Do NOT create separate Chinese examples.

### Operation summaries

Summaries must follow the glossary verb conventions from `flashduty-docs/.cursor/skills/translate-zh-to-en/glossary.md`. Do NOT mechanically transliterate the path or `name_cn` — read the handler to understand the operation's purpose, then write a clear summary using the standard verbs:

| Pattern | ZH | EN |
|---------|----|----|
| Get one | 查看xxx详情 | Get xxx detail |
| List | 查询xxx列表 | List xxx |
| Create | 创建xxx | Create xxx |
| Update | 更新xxx | Update xxx |
| Delete | 删除xxx | Delete xxx |
| Enable/Disable | 启用/禁用xxx | Enable/Disable xxx |
| Batch get | 批量查询xxx | Batch get xxx |

Keep summaries consistent across operations within a module. When the registry `name_cn` is vague or misleading, improve it based on what the handler actually does.

### Operation IDs, tags, and rendering

- **`operationId`** — convert the registry `name` (`template:read:info`) to **kebab-case** (`template-read-info`). Kebab-case is URL-safe, SEO-friendly, and what Mintlify uses as the URL path segment for each rendered operation. One stable ID per colon-separated token.
- **`tags`** — each operation gets exactly **one** tag, formatted as `"<parent>/<module-label>"`. The parent comes from `module_parents` in `mapping.yaml` (e.g., `On-call`, `Platform`, `Monitors`, `RUM`). The module label is the scope's `tag_en` or `tag_zh`. Example: `"On-call/Templates"` (EN), `"On-call/模板管理"` (ZH). Tag arrays are length-1 by design — no cross-tagging. Mintlify renders slash-delimited tags as a nested sidebar, which is exactly what we want.
- **`deprecated: true`** — set when the Go handler is commented with `// deprecated` above the function. Grep for this when walking the handler file.

Every pair of files (EN + ZH) uses the **same** operationId. Only the displayed `tags` string and the `tag_en`/`tag_zh` labels differ.

**`x-mint.href` URL paths:** Both EN and ZH specs must produce parallel URL paths. The ZH spec uses paths starting with `/zh/api-reference/...` (Mintlify default). The EN spec must use `/en/api-reference/...` — set `x-mint.href` with the `/en/` prefix explicitly. URL path segments are always English in both languages; only the sidebar labels differ.

**Do NOT emit `x-apifox-slug` / `x-apifox-folder`.** They don't work — see `references/apifox-extensions.md`. Apifox treats them as unknown-extension metadata and renders them as visual-noise tags, without populating any real fields.

## Step 4 — localize into the Chinese spec

After the English document is complete, derive the Chinese one by deep-copying it and walking it with a fixed rule set:

- `info.title`, `info.description` — replace with the Chinese skeleton strings.
- Every `tags[*].name` and every operation `tags[*]` entry — replace with `tag_zh`.
- Every operation `summary` — set to the registry `name_cn`.
- Every operation `description` — if the English description came from a Go doc comment, look for a matching Chinese comment; otherwise leave as the registry description (which is already Chinese in the source) or translate using the glossary at `../../flashduty-docs/.cursor/skills/translate-zh-to-en/glossary.md`.
- Schema `property.title` — if a Go tag like `title_zh:"中文标题"` exists, use it; else translate from English using the glossary.
- Everything else (keys, types, refs, required, enum values) — keep identical.

Critically: do **not** rebuild the Chinese file from scratch. Deriving it from the English one guarantees they stay in sync structurally.

## Step 5 — write output files

Write to the per-module files that Mintlify reads, then update the consolidated reference copies:

```
# Per-module files (what Mintlify renders — always update these)
<docs-repo>/api-reference/<module>.openapi.en.json
<docs-repo>/api-reference/<module>.openapi.zh.json

# Consolidated reference copies (for Apifox import / cross-module audits)
<docs-repo>/api-reference/openapi.en.json
<docs-repo>/api-reference/openapi.zh.json
```

The module name comes from `mapping.yaml` — e.g., `on-call/template` belongs to module `on-call`, so the target files are `on-call.openapi.en.json` and `on-call.openapi.zh.json`.

**Never touch `api-reference/openapi.legacy.zh.json`** — that's the legacy Apifox export, preserved for reference porting.

## Step 6 — validate

For each written file:

```bash
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('ok', sys.argv[1], 'paths=', len(d['paths']), 'schemas=', len(d['components']['schemas']))" <path>
```

Fail loudly if JSON does not parse. Then run `mint broken-links` from the docs repo. Expected noise from `.cursor/` is fine to ignore — only flag real broken links in newly written files.

## Step 7 — report to the user

Print:

- The two output file paths.
- A tiny diff summary: operations added, removed, unchanged vs the previous version (diff against the files that existed before this run if any).
- Any `unresolved` items from findings that were skipped.
- Any schema the generator had to synthesize as loose `{type: object}` because the Go type couldn't be resolved — these are technical debt the user should fix by hand or by improving the handler.

Stop. Do not commit, do not open a PR. The human decides when to ship.

## Dry-run behavior

With `--dry-run`, do everything up to Step 5, then instead of writing files, print each file's top-level path count and schema count and a preview of 2-3 sample paths. This is the fastest way to sanity-check a scope before committing tokens to disk.
