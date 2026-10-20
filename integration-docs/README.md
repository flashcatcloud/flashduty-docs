# Integration Docs Compatibility Bundle

This package builds the legacy documentation payload consumed by `fc-saas-web`.

The source of truth remains the Mintlify MDX files under `../zh` and `../en`.
This compatibility layer converts selected integration MDX files into plain
Markdown strings and emits the old runtime contracts:

- ESM: `flashduty-knowledge-base/zh`, `flashduty-knowledge-base/en`
- IIFE: `window.FlashDocsZh`, `window.FlashDocsEn`

Build output is written to `dist/` and should not be committed.

```bash
cd integration-docs
npm run build
npm run check
```

## Authoring conventions

The console reads these from the built Markdown; `npm run check` enforces them.

- **Steps.** `<Step title="X">` becomes `### 步骤 N：X` (zh) or `### Step N: X` (en), numbered across the whole page. Hand-written `步骤 N` / `Step N` headings and bold `**步骤 N：X**` labels are rewritten to the same form when they number 1..N in order. Pages that repeat numbers (one flow per deployment type) are left as written. `<Tab>` titles become plain `### <title>`, or `#### <title>` when the tab sits inside a step.
- **Placeholders in code blocks.** Write `{integration_url}` for the full push URL (including the key) and `{integration_key}` for the key alone; use `{api_host}` when a page must show the URL format. Do not write the push URL out against `api.flashcat.cloud` or use spellings such as `<push URL>`, `<集成密钥>` or `YOUR_INTEGRATION_KEY`.
