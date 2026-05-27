# Analyze phase

Goal: produce a findings YAML that lists every public API in the requested scope, each annotated with the Go handler that serves it and the input/output types we plan to lift into OpenAPI. The human reviews this file before we spend tokens generating JSON.

## Inputs

- `--scope` — module or sub-module key from `mapping.yaml`, or `all`.
- Parsed registry from `scripts/parse_pgy_registry.py` (run it once, cache the JSON in memory for the rest of this phase).
- Source repos, synced to latest `origin/main`.

## Step 1 — load and filter the registry

Run the parser:

```bash
python3 <skill-path>/scripts/parse_pgy_registry.py ../fc-pgy/logic/api/api_test.go --format json
```

Keep only rows where:

- `auth == "all"` (other auth modes are not public — see `references/auth-modes.md`), AND
- the `path` does NOT start with `/event/push/` (integration-key routes, never `app_key`-callable), AND
- the row's `path` top-level segment matches one of the requested scope's `path_prefixes`, AND
- the row's `provider` is in the scope's `providers` list (when specified — if `providers` is omitted, match on prefix alone).

If `--scope all`, iterate every module where `hidden` is falsy and run the rest of the pipeline once per module.

**Commented vs uncommented — treat them the same.** The convention: commented-out rows are existing production APIs already persisted in the DB; uncommented rows are new additions left active so `go test` can register them. Commenting is a deployment workflow detail, not a status indicator — a commented row is NOT deleted or inactive. All rows in this file are live APIs. This is the single biggest thing to remember.

**Subgroup matching:** When a module defines `subgroups` in `mapping.yaml`, each surviving row must be assigned to a subgroup. Match by checking the row's `path` against each subgroup's `path_prefixes` in order — **first matching subgroup wins**. If no subgroup matches, assign the row to a catch-all group and emit a warning in findings so the user can update the mapping.

## Step 2 — resolve the backend handler for each row

For each surviving row, find the Go file that serves its `path`. The scope's `repos` entry tells you where to look. The convention is:

- `fc-event`: `cmd/server/controller/<feature>/<operation>.go` — one file per operation, named after the URL segment.
- `fc-oncall`: `callee/...` — grep for the path string.
- `fc-pgy`: `cmd/server/controller/...` or `logic/.../controller.go`.
- `monit-webapi`: `api/...` or `logic/.../http.go`.
- `fc-rum`: `controller/...`.
- `fc-statuspage`: `cmd/.../handler.go`.

Practical lookup strategy:

1. Try the file-name convention first. `/template/info` → `cmd/server/controller/template/info.go`. That's an O(1) hit rate >70% of the time inside fc-event.
2. If not found, `git -C <repo> grep -l '"<path>"' origin/<branch> -- <controller-paths>` — the exact path string often appears in a routes.go file near the handler reference.
3. If still not found, grep for the last URL segment as a Go identifier (e.g. `/template/preview` → `func Preview(`). Confirm you found the right handler by looking for `srv.GinToCtx` or `srv.Validate` in the same file.
4. If none of those work, record the row under `unresolved` in findings and move on. Do not guess — unresolved rows are fine and the user can fix the mapping.

For each resolved row, extract three things from the handler file:

- `handler_file`: repo-relative path (e.g., `cmd/server/controller/template/info.go`).
- `input_type`: the Go type passed to `srv.Validate(ctx, ...)`, `c.ShouldBindJSON(...)`, or `c.ShouldBindQuery(...)`. This is usually a local `xxxInput` struct in the same file. Record its name.
- `output_type`: the Go type of the value passed to `srv.JSON(ctx, <value>)` on the success branch. This is trickier — follow these rules in order:
  1. If the handler builds a struct literal inline (e.g., `srv.JSON(ctx, gin.H{"items": items, "total": total})`), record `output_type: inline` and include the field→type mapping.
  2. If the handler calls a logic method and passes the result directly (e.g., `srv.JSON(ctx, item)`), trace the Go type of `item` — usually `*structs.IncidentItem` or `[]*structs.ChannelItem` — and record the fully qualified type name.
  3. If the type is a generic helper (e.g., `listResult[structs.XxxItem]`), record both the wrapper and the element type.

Do not inline the entire struct definition here — that's phase 2's job. Phase 1 just names types and their source files so phase 2 can read them.

## Step 3 — assemble the findings YAML

Write to `.api-review/findings-<scope-slug>-<YYYYMMDD-HHMMSS>.yaml` in the docs repo. Use forward slashes in the slug (`on-call-template`).

Structure:

```yaml
scope: on-call/template
generated_at: 2026-04-10T18:30:12Z
docs_path: api-reference/on-call/template/
tag_en: Templates
tag_zh: 模板管理
providers: [event]
source_registry: ../fc-pgy/logic/api/api_test.go
source_registry_commit: <git sha of origin/main HEAD>

operations:
  - id: 1060
    method: POST
    path: /template/info
    name: template:read:info
    name_cn: 查看模板详情
    description: ""
    auth: all
    is_dangerous: false
    is_audit: false
    handler:
      repo: fc-event
      file: cmd/server/controller/template/info.go
      input_type: infoInput
      output_type: "*structs.TemplateItem"
      notes: ""
  - id: 1061
    # ...

unresolved:
  - id: 1234
    method: POST
    path: /template/mysterious-op
    reason: "no handler found under cmd/server/controller/template/"

stats:
  total_public: 8
  resolved: 8
  unresolved: 0
```

`source_registry_commit` matters — it pins what we parsed so stale re-runs are obvious later.

## Step 4 — emit the JSON sidecar and HTML report

Right after writing the YAML, emit two companion files with the same stem:

1. **JSON sidecar** at `.api-review/findings-<scope-slug>-<ts>.json` — identical structure to the YAML (`scope`, `generated_at`, `tag_en`, `tag_zh`, `operations`, `unresolved`, `stats`, …). Powers the HTML render without a PyYAML dependency.
2. **HTML report** via the bundled renderer:

   ```bash
   python3 <skill_dir>/scripts/render_html.py \
     .api-review/findings-<scope-slug>-<ts>.json \
     --out .api-review/findings-<scope-slug>-<ts>.html
   ```

   `<skill_dir>` is the directory containing this `analyze.md`. The renderer is stdlib-only — no install step. It renders operations sorted by path with HTTP-method chips, dangerous / audit-logged flags, and a dedicated "unresolved" section coloured warm oxblood so missing handlers are impossible to miss.

**Rule of thumb:** YAML is for agents (the generate phase reads it), HTML is for humans (review the picked-up set). The HTML must never be parsed or rewritten by an agent.

## Step 5 — human checkpoint

Print to the user:

- The paths to BOTH the YAML and HTML files.
- The stats block.
- Any `unresolved` rows with their reasons.
- A one-line instruction: "Review the HTML at `<html_path>`, edit the YAML to drop any rows you don't want, then run `/api-review --mode generate --scope <scope>`."

Stop. Do not proceed to generate unless `--auto` was set.

## Auto-mode behavior

If `--auto` is set, skip the "stop and wait" step but still write the findings file. Then invoke the generate phase in the same run, reading the file you just wrote.
