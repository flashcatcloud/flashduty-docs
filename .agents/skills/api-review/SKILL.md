---
name: api-review
description: "Generate OpenAPI 3.1 specs for Flashduty public APIs (app_key-callable) from the fc-pgy registry and backend handlers. Produces bilingual openapi.en.json + openapi.zh.json per module under flashduty-docs/api-reference/. Use this skill whenever the user asks to build, refresh, regenerate, sync, or fix OpenAPI specs for Flashduty's public API — including partial regenerations scoped to a single module like on-call/template, monitors, rum, or platform/member."
---

# API Review

Turn the Flashduty public API surface into maintainable OpenAPI 3.1 specs.

Ground truth lives in two places, and the skill stitches them together:

1. **`fc-pgy/logic/api/api_test.go`** — the proxy registry. Every row that has ever been registered is in this file as a Go struct literal. **Commented rows are existing production APIs already persisted in the DB; uncommented rows are new additions not yet deployed, left uncommented so `go test` can upsert them.** Both are equally valid — the file is a cumulative ledger, not a declarative spec. A commented-out row does NOT mean "deleted" or "inactive"; it means "already registered, no need to re-run the test for it." That tells us *which paths are exposed* and *how they are authenticated*.
2. **Backend Go handlers** in `fc-event`, `fc-oncall`, `fc-pgy`, `fc-rum`, `fc-statuspage`, `monit-webapi`, `fc-datasource` — the real code that defines input structs and the type passed to `srv.JSON(ctx, ...)`. That tells us the *request body / query* and *response `data`* shape.

Everything else (the `request_id`/`error`/`data` envelope, security scheme, tags, server URL) is constant and lives in `references/`.

## Scope filter — what counts as "public"

A row qualifies as public if **all** of the following are true:

- `Auth` is exactly `"all"` (alias `AuthPerson`, accepts JWT or `app_key`). **`optional`, `integration`, `data`, `jwt`, and `none` are not public.** See `references/auth-modes.md`.
- The row's `path` does NOT start with `/event/push/` (alert-source push routes are integration-key authenticated, not `app_key` — they belong in per-integration setup docs, never the public API reference).
- The row's `Path` maps to a module in `mapping.yaml`.
- The row is not marked `hidden: true` on its module (see mapping — we hide internal infra like captcha/mfa/push/kv, dev/test providers like `echo`, and non-customer surfaces like `safari` by default).

`none`, `jwt`, `data`, `integration` rows are **not** public for openapi purposes and must be skipped. See `references/auth-modes.md`.

## Two phases — analyze then generate

Like `doc-review`, this skill runs in two phases with a human checkpoint between them. The phases exist because generating openapi is expensive (reading many handlers + struct definitions) and the registry can contain stale rows — a human should be able to inspect the picked-up set before we burn tokens writing JSON.

- **Phase 1 — Analyze.** Parse the registry, filter by scope and auth, look up the backend handler file for every surviving row, emit a YAML findings file listing `{api_name, method, path, handler_file, input_type, output_type, tag_en, tag_zh, summary_en, summary_zh}`. Stop so the user can delete rows or adjust tag/summary mappings.
- **Phase 2 — Generate.** Read the findings file, read each referenced handler + struct source, build one `openapi.en.json` + one `openapi.zh.json` per sub-module under `flashduty-docs/api-reference/<module>/<sub>/`. Validate the JSON loads, run `mint broken-links` on the docs repo, and report.

`--auto` skips the human checkpoint and runs both phases back-to-back. Use for incremental re-runs on a module you've already curated.

## Quick reference

```
/api-review --validate-registry                              → parse registry, print counts + any unknown paths
/api-review --mode analyze --scope on-call/template          → phase 1 for one sub-module
/api-review --mode analyze --scope on-call                   → phase 1 for an entire module
/api-review --mode analyze --scope all                       → phase 1 for everything non-hidden
/api-review --mode generate --scope on-call/template         → phase 2, reading latest findings for that scope
/api-review --mode generate --scope on-call/template --auto  → both phases, no checkpoint
/api-review --mode generate --scope on-call/template --dry-run → show what would be written, don't write
```

## Argument parsing

Parse the user's invocation:

- `--mode`: `analyze` or `generate`. Defaults to `analyze` on first invocation; subsequent runs need to be explicit.
- `--scope`: module or sub-module key from `mapping.yaml`. Accepts two levels: `on-call`, `on-call/template`, `platform/member`, etc. Special values: `all` (every non-hidden module).
- `--auto`: run phase 1 → phase 2 without stopping for review. Findings file is still written so the user can inspect it after the fact.
- `--dry-run`: paired with `--mode generate`; prints the intended output files and their top-level path counts without writing them.
- `--validate-registry`: sanity-check the parser — no findings, no openapi, just a report.

## Path resolution

Base path for source repos works exactly like `doc-review`: if the skill is invoked inside `flashduty-docs`, assume all source repos are siblings of it (`../fc-pgy`, `../fc-event`, ...). A `base_path` override is not currently needed; keep it simple.

The docs repo — where output is written — is always the current working directory. Refuse to run if `pwd` is not a git repo containing `docs.json` (this is the Mintlify docs site root).

## Repo freshness

Before any analysis: **every source repo and the docs repo must be on the latest `origin/main`** (or whatever default branch each uses). Stale checkouts produce false-positive drift and wrong handler locations. Follow the same freshness protocol as doc-review:

```bash
git -C <repo> fetch origin
git -C <repo> symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
# use origin/<default-branch> for every read
```

When a required source repo is missing, auto-clone it into the sibling directory.

## Routing

### 1. Validate registry (`--validate-registry`)

Run `scripts/parse_pgy_registry.py` against `../fc-pgy/logic/api/api_test.go`. It emits JSON to stdout and a human summary to stderr. Print the summary and stop. The summary should include:

- Total rows parsed, uncommented vs commented count
- Rows per `auth` value
- Rows per `provider`
- Rows per module (after applying `mapping.yaml`)
- Any path whose top-level segment is *not* claimed by any module — these are flagged as "unknown" so the mapping can be updated

### 2. Analyze (`--mode analyze`)

Follow **`analyze.md`** in this directory. It takes the parsed registry + `--scope` and produces a findings YAML file at `.api-review/findings-<scope>-<timestamp>.yaml`.

### 3. Generate (`--mode generate`)

Follow **`generate.md`** in this directory. It reads the latest findings file for the scope (or the explicitly given one), reads every referenced Go handler + its input/output structs, then writes the two openapi JSON files to `api-reference/<scope>/`.

### 4. Auto mode (`--auto`)

Run analyze, then immediately run generate against the just-written findings file. The user still gets the findings YAML after the fact for inspection/editing before the next run.

## Output layout

Mintlify reads **per-module split files**, not a single consolidated file. `docs.json` wires each product tab to its own OpenAPI spec:

```
api-reference/
├── on-call.openapi.en.json      # On-call module operations + schemas (EN)
├── on-call.openapi.zh.json      # On-call module operations + schemas (ZH)
├── monitors.openapi.en.json     # Monitors module (EN)
├── monitors.openapi.zh.json     # Monitors module (ZH)
├── rum.openapi.en.json          # RUM module (EN)
├── rum.openapi.zh.json          # RUM module (ZH)
├── platform.openapi.en.json     # Platform module (EN)
├── platform.openapi.zh.json     # Platform module (ZH)
├── openapi.en.json              # consolidated reference copy (not read by Mintlify)
├── openapi.zh.json              # consolidated reference copy (not read by Mintlify)
└── openapi.legacy.zh.json       # old hand-maintained Apifox export, read-only reference
```

**The per-module files are what Mintlify actually renders.** The consolidated `openapi.en.json` / `openapi.zh.json` exist as reference copies and for Apifox import, but `docs.json` does NOT point to them. When fixing or regenerating specs, always update the per-module files — changes to only the consolidated files will NOT appear on the docs site.

Tab configuration in `docs.json` (already in place, included here for reference):

```json
{
  "tab": "API 参考",
  "openapi": "api-reference/on-call.openapi.zh.json"
}
```

One tab per module per language. When you edit operations in the per-module files, Mintlify picks up the change automatically on the next `mint dev` reload — no navigation edits needed.

Module/sub-module grouping within each file is preserved **via tags and `x-apifox-folder`**. Both Mintlify and Apifox render the two-level `"On-call/Templates"` tag as a sidebar tree, which is the navigation experience the docs site actually needs.

The **legacy** `openapi.legacy.zh.json` is the original hand-maintained Apifox export. Keep it as a read-only reference for porting descriptions, examples, and tag names — never overwrite it.

### Partial / incremental runs

When `--scope on-call/template` runs, the generate phase:

1. Reads the existing per-module file (e.g., `api-reference/on-call.openapi.en.json`).
2. Removes every operation whose `x-apifox-folder` matches the scope's tag.
3. Removes every schema that, after step 2, has zero remaining `$ref`s from the kept operations.
4. Merges in the newly generated operations and schemas.
5. Validates.
6. Writes the per-module file back.
7. Also updates the consolidated `openapi.en.json` with the same merge logic (for reference/Apifox).

The same merge logic applies to the Chinese files. Always verify that the per-module file is correct — that's what Mintlify renders.

## The bilingual contract

Both language files must:

- Use the **same English operation IDs, paths, schema names, and Apifox extensions** (`x-apifox-folder`, `x-apifox-slug`). Only human-facing text fields change between languages.
- Operation IDs are **kebab-case derived from the registry `name`** — `template:read:info` → `template-read-info`. Kebab-case reads cleanly in URLs, is SEO-friendly, and is what Apifox picks up as the default slug.
- Each operation carries exactly one tag formatted as `"<parent>/<module>"` — e.g., `"On-call/Templates"` (EN) / `"On-call/模板管理"` (ZH). The `<parent>` comes from `module_parents` in `mapping.yaml`; the `<module>` comes from the scope's `tag_en`/`tag_zh`. Both Mintlify and Apifox render slash-delimited tags as a two-level sidebar. Scopes without a parent (like `monitors`, `rum`) use a single-level tag.
- Schema keys (`IncidentItem`, `TemplateCreateRequest`, ...) are identical across languages. Only schema property `description` changes; property keys, types, `required`, and `enum` values are structurally identical.
- The language files are **derived from each other**, not written independently. Build English first, then copy it to Chinese and overwrite only `info.title`, `info.description`, `tags[].name`, per-operation `tags[0]`, per-operation `summary` and `description`, and schema property `description` fields. Any drift between the two is a generator bug.
- Every schema's validation — `required`, `minLength`, `maxLength`, `minimum`, `maximum`, `pattern`, `enum`, `default` — comes **only** from Go `binding:` tags or explicit handler code (e.g., `if input.Limit == 0 { input.Limit = 20 }` → `default: 20`). Do not invent constraints from handler logic that happens to branch on specific values.

This lets Mintlify and Apifox serve the same URL path from either spec, keep internal references aligned, and render identical navigation trees.

## Response envelope

Every endpoint's 200 response wraps the handler output in the fc-pgy Resp struct from `go-pkg/srv/render.go`:

```json
{
  "request_id": "string",
  "error": { "code": 0, "message": "string" },
  "data": <handler-specific shape>
}
```

See `references/response-envelope.md` for the exact shape the generator should emit, including the standard error responses (4xx/5xx) which all share the same envelope with `error` set and `data` absent.

## Security scheme

`app_key` is passed as a query parameter on every public endpoint. See `references/security-scheme.md` for the exact `securitySchemes` + `security` blocks to inject into every file.

## Handler extraction — how to find input/output shapes

See `references/handler-extraction.md` for the pattern. The short version:

1. From `mapping.yaml`, the sub-module tells you which backend repo + controller paths to search.
2. Find the handler by `Path` — e.g., `/template/info` lives at `fc-event/cmd/server/controller/template/info.go` (convention: one file per operation under `controller/<feature>/`).
3. Input: look for the first `type xxxInput struct` definition in the file or for the struct literal passed to `srv.Validate(ctx, ...)`. Fields use `json:"name" binding:"required"` tags.
4. Output: look for the value passed to `srv.JSON(ctx, <value>)`. Trace the Go type of that value — it is usually a `*structs.XxxItem`, a `[]*structs.XxxItem`, or a small anonymous struct. Read the struct definition and walk nested fields recursively.
5. The output becomes `components.schemas.<TypeName>`; the endpoint's 200 response wraps it as `{request_id, error, data: {$ref}}`.

Be pragmatic: if a handler uses generic helpers that hide the output type, fall back to a loose `data: object` with a note in the description, and add the handler to `findings.unresolved`.

## Key resources

Read as data, not invoked:

- **Registry parser:** `scripts/parse_pgy_registry.py`
- **Module mapping:** `mapping.yaml`
- **Envelope reference:** `references/response-envelope.md`
- **Security scheme:** `references/security-scheme.md`
- **Handler extraction:** `references/handler-extraction.md`
- **Auth mode table:** `references/auth-modes.md`
- **Description sections (rate limits / permissions / usage notes):** `references/description-sections.md`
- **Mintlify nav & icons:** `references/mintlify-navigation.md`
- **Apifox extensions (deprecated):** `references/apifox-extensions.md`
- **Legacy Apifox export (reference only):** `api-reference/openapi.zh.json` in the docs repo
- **Translation glossary:** `.cursor/skills/translate-zh-to-en/glossary.md` in the docs repo

## Findings storage

Findings are written to `.api-review/` in the docs repo (gitignore it). Each analyze run produces a trio of artefacts sharing one stem:

```
.api-review/
├── findings-on-call-template-2026-04-10-183012.yaml   # agent-readable (consumed by generate phase)
├── findings-on-call-template-2026-04-10-183012.json   # JSON sidecar that feeds the HTML renderer
├── findings-on-call-template-2026-04-10-183012.html   # human-readable kami-styled report
└── history/
```

**YAML for agents** (generate phase, pin matching); **HTML for humans** (review the picked-up set, hand-off). The HTML is produced by `scripts/render_html.py` — stdlib only, no PyYAML dependency.

The user can edit or remove rows in the YAML before running `--mode generate`. By default, generate picks the most recent YAML file matching the scope. When `--auto` is used this human review is skipped.

## Workflow preferences

- **Never overwrite `api-reference/openapi.legacy.zh.json`** — that's the legacy Apifox export, read-only.
- **Always validate output JSON** with `python3 -c "import json; json.load(open(path))"` before announcing success.
- **Do not create a PR automatically.** Leave the user to review the diff and commit/PR themselves. This skill's blast radius is large; a human should eyeball the first few generations.
- **Respect the `hidden: true` flag** in `mapping.yaml`. Hidden modules are skipped even when `--scope all` is given. The user can flip them manually.
- **After writing files, push to the Apifox project** when `--publish` is set. Use the `apifox-new-mcp` tools (loaded as `mcp__apifox-*`) to upsert operations and schemas into project id `8090078`. See `references/apifox-extensions.md` for which tools to use.

## Description guidance — split short + rich

Every operation's documentation is **split across two OpenAPI fields**, not packed into `description`:

- **`description`** — a **single short sentence** that states what the operation does. 60–100 characters, active voice, present tense. This is the only text that appears at the top of the Mintlify page, under the operation title and above the HTTP method line. Think chapter subtitle, not chapter.
- **`x-mint.content`** — the **rich body** of the page, rendered as full Mintlify MDX below the method line. Contains the extended prose, rate limits, permissions, and usage notes as structured sections. See `references/description-sections.md` for the exact layout.

The short `description` answers *what*. The `x-mint.content` body answers *when / how / caveats / limits / permissions / response shape*.

When writing the long-form `prose_en` / `prose_zh` that feeds the Overview section, the 4-question framework still applies:

1. **When should I use this?** Place the operation in a typical workflow. "Use this after `POST /incident/list` when you need the full payload for one row rather than the list summary."
2. **How does it behave in non-obvious ways?** Side effects, preconditions, differences from similar endpoints, edge cases in request validation.
3. **What are the deprecation / compatibility caveats?** If the operation is `deprecated`, explain what replaces it; if it has version-gated behavior, flag it.
4. **What does the response tell me?** What the shape of `data` signifies — especially for operations where the response shape isn't obvious from the type name.

Keep the prose tight — 2–4 paragraphs is plenty. Write in present tense, active voice, second person ("you"). Avoid marketing language ("powerful", "robust", "comprehensive"); avoid redundant phrases ("this API allows you to"); avoid repeating the operation summary.

**Field-level descriptions** follow the same rule but shorter — one sentence max. State what the field represents and any non-obvious constraint. Omit the type (the `type` keyword already says it). Example:

- Good: `"Unique template name within the account. 1–39 characters."`
- Bad: `"This is a string that represents the template name (required, must be unique)."`

### Examples are mandatory

Every operation must include at least one realistic example:

- **`requestBody.content["application/json"].example`** — a valid request payload a consumer could copy-paste. Use plausible values (real-looking IDs, meaningful names), not `"string"` placeholders.
- **`responses.200.content["application/json"].example`** — a realistic success response envelope showing the envelope wrapping the `data` payload. Use the same IDs as the request example so the pair tells a coherent story.

Examples drive Apifox's "Try It Now" button, Mintlify's code snippet previews, and the context LLM agents see when reasoning about API usage. They're not optional flourish — they're the difference between a docs page that teaches and one that just lists fields.

### Capturing real 200 response examples from the dev API

Use the Flashduty dev environment to capture real API responses as examples. Only 200 responses matter — error responses use the shared `ErrorResponse` schema and don't need per-op examples.

**Dev API base URL:** `https://api-dev.flashcat.cloud`
**Auth:** `app_key` query parameter, value from `$FLASHDUTY_APP_KEY` environment variable.

```bash
# Example: call the team list API
curl -s "https://api-dev.flashcat.cloud/team/list?app_key=${FLASHDUTY_APP_KEY}" \
  -H "Content-Type: application/json" -d '{}'
```

**Workflow for capturing examples per module:**

1. Read the module JSON file from `.api-review/modules/<module>.json`
2. For each operation missing `example_response_data`:
   a. Build a minimal valid request body from the operation's schema (use `example_request` if present, otherwise construct from required fields)
   b. Call the dev API: `curl -s "https://api-dev.flashcat.cloud<path>?app_key=${FLASHDUTY_APP_KEY}" -H "Content-Type: application/json" -d '<body>'`
   c. Parse the JSON response — extract `.data` from the envelope
   d. If the response reveals schema bugs (missing fields, wrong types, wrong enums), fix the schema in the module file first
   e. Write the `.data` value into the operation's `example_response_data` field
   f. For list operations, trim `items` to 1–2 entries to keep examples concise
3. Skip operations that are destructive (delete/remove) on resources you didn't create, or that trigger side effects (notifications, exports)
4. For create operations: create → capture response → optionally delete the created resource

**Important:** The `example_response_data` field holds only the `data` portion of the response (not the full envelope). The generator wraps it in `{"request_id": "...", "data": <value>}` automatically.

### The error-code enum

`DutyError.code` is a **string enum**, not an integer. See `references/response-envelope.md` for the full list of 20 wire values and their HTTP-status mapping. Every generated file must define `ErrorCode` as a single shared schema in `components.schemas` and `$ref` it from `DutyError.code`. Never inline the enum per-operation — it belongs once, at the envelope layer.

### Restrictions and Usage in the rich body

The Mintlify page body (rendered from `x-mint.content`) stays **small** so the Authorization section stays above the fold. Two blocks, in order:

1. **`## Restrictions`** — a 2-row markdown table. Row 1 is rate limits (unified defaults or per-API account caps), row 2 is permissions (looked up in `permission_test.go`, or "any valid `app_key`" when no permission gates the call). No prose around the table.
2. **`## Usage`** — bulleted list of non-obvious behaviors. Conditional — omit the whole section when there's nothing to say. Auto-populated with boilerplate bullets when `audit: true`, `dangerous: true`, or `deprecated: true`. Per-operation bullets come from `usage_en` / `usage_zh` on the operation definition.

Deprecation also gets a `<Warning>` admonition at the very top of `x-mint.content` (above Restrictions), so users see the deprecation badge before any other content. The recommended alternative lives in `deprecated_alt_*` and gets appended to the Usage bullets.

Full rules, table format, and bullet-writing guidance are in `references/description-sections.md`.

### Translation and terminology

Every summary, description, and schema property description is written twice (EN + ZH). Stay consistent with the Flashduty glossary at `.cursor/skills/translate-zh-to-en/glossary.md` — in particular the "API documentation" section which covers operation verbs (Create / List / Get / Update / Delete), permission class names (which come from `permission_test.go#classEn`), and the structural terms used in the rate-limits / permissions sections.

When picking English names, **prefer the frontend console label** (from `fc-foundation-app/src/Packages/.../i18n`) over a fresh translation — that's what the end user actually sees in the UI, and consistency between UI and API reference is worth a lot.

## Design principles

1. **Registry over routes.** The pgy registry is authoritative for which paths are exposed; the backend route files are authoritative for which handler serves a path and what types it uses. Never invent an endpoint that isn't in the registry.
2. **App-key-callable only.** The only public entry is the `app_key` query parameter via fc-pgy. `Flashcat-Context` headers that appear in backend handlers are proxy-internal — do not surface them in the spec.
3. **Thin envelope contract.** The `{request_id, error, data}` wrapper is universal; define it once in `components.schemas` and `$ref` it everywhere. Only the `data` payload changes per endpoint.
4. **English path is canonical.** Chinese file reuses the same English path, operation ID, and schema keys. Only human-facing text differs.
5. **Per-module files for Mintlify, consolidated files for reference.** Mintlify reads the per-module split files (`on-call.openapi.*.json`, `platform.openapi.*.json`, etc.) — always update those. The consolidated `openapi.en.json` / `openapi.zh.json` are kept in sync as reference copies for Apifox import and cross-module audits, but they are NOT what the docs site renders.
6. **Fail loudly on drift.** If a registered row's path cannot be located in any backend repo, record it under `unresolved` in findings and keep going — do not emit a fabricated path operation.
7. **Incremental and resumable.** Scope everything so the user can rebuild one sub-module without touching neighbors. This is how we avoid one bad extraction from corrupting hundreds of unrelated endpoints.
