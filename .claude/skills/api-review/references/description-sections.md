# Description sections

Mintlify renders every operation page in two stacked regions:

1. **Top of page** — the OpenAPI `summary` (bold title) and `description` (short subtitle). This is the bit that needs to fit in one line without scrolling.
2. **Body of page** — below the HTTP method+path and the "Try it" button, Mintlify injects content from the **`x-mint.content`** extension as full MDX. This is where rich documentation lives: admonitions, section headers, tables, code blocks, nested components.

We split operation documentation across both regions:

- **`description`** — **one short sentence only.** Just state what the operation does. No "Use this when...", no caveats, no sections. This is the text that appears in the sidebar tooltip, the search snippet, and directly under the title.
- **`x-mint.content`** — **everything else**, structured as MDX. This is where Rate limits, Permissions, Usage notes, and the extended "when/how/caveats" prose go.

Before this split, earlier iterations of the skill stuffed everything into `description`. That produced a 4–5 paragraph wall of text at the top of the page — hard to scan, pushed the method/path line below the fold, and buried the operation signature. The split fixes that.

## What goes in `description` (the short one-liner)

Write one clear sentence in the active voice that answers "what does this operation do?". Think of it as a chapter subtitle, not a chapter.

Bad: `"Return the full configuration of a single notification template. Use this when... Pass the preset ID..."` (4 paragraphs)

Good: `"Return the full configuration of a single notification template by ID."` (1 sentence)

Rules of thumb:
- Target **60–100 characters**.
- Present tense, active voice.
- Don't repeat the operation's English name (`Get template detail`) — that's already the summary.
- Don't mention rate limits, permissions, or edge cases — those go below.
- Don't start with "Returns the" or "Retrieves the" — just start with the verb.

## What goes in `x-mint.content` (the rich body)

**Keep it compact — the body sits above the Authorization section on the Mintlify page, and any content here pushes Authorization below the fold.** Every extra line matters.

Composed from a fixed template. Every operation's `x-mint.content` contains these blocks, in order:

1. **Admonition block** (conditional) — `<Warning>` for deprecated operations only. No other admonitions by default.
2. **`## Restrictions` / `## 限制说明`** — **always emitted**, exactly 2 rows in a markdown table: rate limits on the first row, permissions on the second row. This replaces the old "Rate limits" and "Permissions" headings with a single compact block.
3. **`## Usage` / `## 使用说明`** — conditional; only emitted when there's at least one bullet to show. Contains non-obvious behavior as a bulleted list.

Do NOT emit an "Overview" section or extended prose in `x-mint.content`. Any "when to use this / how it behaves" information belongs as a Usage bullet if it's non-obvious, or in the short `description` if it's the one sentence that defines the operation. Never as a free-floating paragraph.

Each section renders as a Markdown H2 heading in the Mintlify body. Mintlify auto-generates anchor links from the heading text, so the section titles become deep-linkable.

### The Restrictions table

Exactly two rows, nothing more:

```markdown
## Restrictions

| Aspect | Value |
| ------ | ----- |
| Rate limits | **1,000 requests/minute**; **50 requests/second** per account |
| Permissions | **Templates Read** (`on-call`) |
```

Chinese version:

```markdown
## 限制说明

| 项目 | 说明 |
| ---- | ---- |
| 速率限制 | 每个 `app_key` **1,000 次/分钟**；**50 次/秒** |
| 权限要求 | **模板查看**（`on-call`） |
```

Rules:

- **Row 1 (rate limits)** — always the same format for the unified defaults. When an API has per-account caps set in the pgy registry, use those real values; otherwise fall back to the unified defaults from `mapping.yaml#default_rate_limits` (1,000/min, 50/sec).
- **Row 2 (permissions)** — one of three forms. **Keep it short — just the permission name and scope. Do NOT append error behavior like "Missing the permission → 403" or "缺少权限将返回 403" — that's already documented in the shared ErrorCode schema.**
  - Single permission: `**Templates Read** (`on-call`)`
  - Multiple permissions (API is granted by several): join with ` or ` / ` 或 ` — `**Templates Read** (`on-call`) or **Templates Manage** (`on-call`)`
  - No permission: `None — any valid `app_key` can call this operation` / `无 —— 持有有效的 `app_key` 即可调用`
- **No extra rows.** Don't add columns. Don't add a "HTTP status" column. Don't add "Documentation" links. Two rows keeps the block tiny and Authorization visible.
- **No prose around the table.** No intro sentence, no footnote. The table alone.

### The Usage section

Emit only when there's at least one bullet. The per-operation definition carries:

- `usage_en` / `usage_zh` — list of strings, each becomes a bullet. Keep each bullet to one sentence.
- `audit: true` → auto-append "Every call is recorded in the account audit log..."
- `dangerous: true` → auto-append the MFA bypass warning
- `deprecated: true` → auto-append whatever `deprecated_alt_*` says (the recommended alternative)

If all four signals are empty, omit the `## Usage` header entirely — don't emit an empty section.

When writing `usage_*` bullets, think "non-obvious behavior a developer would want to know about but that doesn't fit anywhere else":

- Validation quirks (`template_name must be unique; duplicates return InvalidParameter`)
- 2xx-for-failure behavior (`parse errors return 200 success:false, not 4xx`)
- Cascade rules (`fails with ReferenceExist if still referenced`)
- Magic values (`passing 000000000000000000000001 returns the preset`)
- Side effects visible after the call (`new state visible via GET /.../info immediately`)

Don't waste a bullet on obvious stuff (`returns the template` on `Get template detail` — that's the description's job).

### Using Mintlify MDX components inside x-mint.content

`x-mint.content` supports the full set of Mintlify MDX components. Useful ones for API docs:

- **`<Warning>…</Warning>`** — for deprecation notices. Red border, warning icon.
- **`<Note>…</Note>`** — for important-but-not-dangerous callouts (audit logging, non-obvious behavior). Blue border, info icon.
- **`<Info>…</Info>`** — for version compatibility notes (e.g., "this endpoint is compatible with SDK v5+").
- **`<Tip>…</Tip>`** — for recommended practices and pro tips.
- **`<Steps>…</Steps>`** — for multi-step processes. Don't reach for this on simple CRUD operations; save it for genuinely procedural endpoints.
- **`<Accordion>…</Accordion>`** — for collapsing long optional content.
- **`<CodeGroup>…</CodeGroup>`** — for multi-language code samples.

Don't go overboard — most operations need just the plain Markdown sections listed above. Admonitions earn their place when something is genuinely non-obvious.

## 1) Rate limits

Rule: **only expose account-level limits. Never expose total/global caps.** Account limits are what API consumers need to know to plan their integration; total caps are infrastructure details that can change without notice and would mislead consumers.

Source of truth: `fc-pgy/logic/api/api_test.go` — each row carries `AQps` / `AQpm` / `AQpd` fields for account-level per-second / per-minute / per-day limits, in addition to global `Qps` / `Qpm` which we ignore.

Fallback: when an API has no account-level limit declared (the common case today — the team hasn't applied explicit account caps yet), use the unified defaults from `mapping.yaml#default_rate_limits`:

```yaml
default_rate_limits:
  per_second: 50
  per_minute: 1000
```

These defaults match the team's stated target of "50/s 1000/m" for unified rate limiting. When the team eventually sets explicit limits on specific APIs, update `mapping.yaml` and regenerate.

**Heavy APIs must NOT use defaults.** Export, import, bulk, and preview operations need lower per-operation limits. When an API has explicit `AQps` / `AQpm` in the registry, always use those. Typical tiers:

| Operation type | AQps | AQpm |
|----------------|------|------|
| Export / download | 1 | 10 |
| Import / upload | 2 | 20 |
| Bulk delete / batch | 5 | 30 |
| Preview / render | 10 | 60 |
| Complex query (insight, analytics) | 20 | 100 |
| Standard CRUD (default) | 50 | 1000 |

If a heavy API has no explicit limits in the registry, flag it in findings as needing rate limit assignment — do not silently apply the default 50/s 1000/m.

Rendered markdown (EN):

```markdown
## Rate limits

- **50 requests/second** per account
- **1,000 requests/minute** per account

Callers exceeding either cap receive `429` with `code: "RequestTooFrequently"`. Limits are account-scoped — different `app_key`s under the same account share the same bucket.
```

And the Chinese version follows the same structure with translated headers and messages.

## 2) Permissions

Rule: **look up the API's name in `fc-pgy/logic/permission/permission_test.go`.** Every entry in that file declares a permission with `factors` listing which API names it grants. An API belongs to every permission that lists it.

Build a lookup map once per run: `api_name → [permission_key, ...]`. The permission entry itself carries `name` / `nameEn` / `description` / `descriptionEn` / `class` / `classEn` / `scope` — all useful for the rendered section.

**No match → "Any valid app_key".** When the API name isn't listed as a factor on any permission, it means the pgy permission table doesn't gate it — so any authenticated caller with a valid `app_key` can hit it. Render it exactly that way; do not invent a permission.

**Multiple matches → list all of them.** Some APIs are granted by multiple permissions (e.g., a read API is usually granted by both a dedicated Read permission and by a corresponding Manage permission via a dependency list). List each one — consumers need to see the full set to know which roles can reach this API.

Permissions are rendered inside the Restrictions table (see above), not as a standalone section. Examples of the permission cell value:

- One permission: `**Templates Read** (`on-call`)`
- Multiple: `**Templates Read** (`on-call`) or **Templates Manage** (`on-call`)`
- None: `None — any valid `app_key` can call this operation`

Do NOT add error behavior text (403, AccessDenied) — the Restrictions table must stay compact.

## 3) Usage notes (conditional)

Render this section only when at least one of these flags is set on the operation:

- **`audit: true`** — comes from the `IsAudit` field on the pgy registry row. Every call is logged to the account's audit trail.
- **`dangerous: true`** — comes from `IsDangerous`. High-risk operations that would require MFA via the console; `app_key` calls skip the MFA prompt but remain audited.
- **`deprecated: true`** — comes from a `// deprecated` Go doc comment above the handler. Also sets OpenAPI `deprecated: true` at the operation level.

Rendered markdown (EN, when all three apply):

```markdown
## Usage notes

Every call is recorded in the account's audit log with the caller's member ID, request payload, and resulting error (if any). Do not put secrets in request fields.

This is a high-risk operation. When called with a console JWT it requires a second-factor verification code; `app_key` calls bypass the MFA prompt but remain fully audited — treat the key as a secret.

**This operation is deprecated.** It remains available for backward compatibility but new integrations should not depend on it.
```

Skip the whole section when none of the flags apply — don't emit an empty header.

## Section order — do not reorder

Keep the order: **Rate limits → Permissions → Usage notes**. Operators care about rate limits and permissions before they care about audit logging; putting usage notes last keeps the section optional without disrupting the scannable "limits and permissions at a glance" pattern.

## Implementation note

Emit the sections from a single `compose_mint_content(op, lang)` helper that takes the operation definition and returns the full MDX block. Each operation entry in `OPERATIONS[]` carries:

- `summary` (EN + ZH) — the bold title at the top
- `description` (EN + ZH) — the one-liner under the title
- `usage_en` / `usage_zh` — list of Usage bullets (optional; may be empty)
- `deprecated_alt_en` / `deprecated_alt_zh` — one-sentence alternative when `deprecated: true` (optional)
- `permission_key` — the API name used to look up permissions in `permission_test.go`
- `audit`, `dangerous`, `deprecated` — boolean flags driving the Warning admonition + usage bullets

The `build_operation` function sets `description` = short one-liner and `x-mint` = `{"content": compose_mint_content(op, lang)}`. Every operation across the whole API gets identical structural treatment — adding a new module is a data-only change, not a template edit.

## Apifox compatibility

Apifox imports OpenAPI but doesn't natively render Mintlify MDX. When it sees `x-mint`, it stashes the full content in its `oasExtensions` field (verified via round-trip — `readEntityDetails` on an imported operation shows the x-mint payload stored there verbatim).

Practical implications:
- **Apifox users see the short `description` and nothing else.** They don't get the Rate limits / Permissions / Usage notes sections unless they look inside the raw extensions, which they won't.
- **That is an acceptable tradeoff.** Mintlify is the primary documentation surface; Apifox is a staging tool for internal team review. If Apifox ever needs to surface the same content, Apifox-specific fields (`commonParameters`, per-response headers, etc.) would be a separate population step.
- **Round-trip is preserved.** Re-importing the same openapi.json into Apifox produces a stable result — no corruption, no data loss on the Mintlify side.

## Migration rule

If you find an operation whose `description` contains multiple paragraphs, headings, admonitions, or Markdown lists, that's a migration debt from the pre-x-mint era. Move everything except the one-liner into `x-mint.content` under the right section, and shorten the one-liner until it fits on a line.
