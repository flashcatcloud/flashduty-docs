# Apifox extensions (deprecated — do not emit)

**Status: these extensions were tried and removed. Do NOT emit any `x-apifox-*` fields in generated output.**

## What we tried and why it failed

We tested two Apifox-specific OpenAPI extensions to control navigation and URL slugs:

- **`x-apifox-folder`** — intended to set the folder path inside Apifox's tree.
- **`x-apifox-slug`** — intended to populate the SEO "custom URL" field.

Neither was recognized by Apifox on import. Instead, Apifox rendered both as unknown-extension metadata tags under the endpoint description (visible as rounded labels like `x-apifox-slug: template-read-list`), which added visual noise without doing anything functional.

There is also no Apifox REST API endpoint to set the SEO custom URL field. The field is UI-only and would have to be set by hand per operation.

## What we do instead

- **Folder nesting** — use slash-delimited values in the `tags` array (`"On-call/模板管理"`). Both Mintlify and Apifox honor this as a two-level sidebar.
- **URL slugs** — use a kebab-case `operationId` derived from the registry name. Mintlify uses `operationId` as the URL path segment for each operation in its rendered docs.
- **Deprecation** — use the standard `deprecated: true` field, which both renderers honor.

## Verification against a real Apifox project

When the apifox-new-mcp MCP is connected (project id `8090078`), use `mcp__apifox-*__read_project_oas` tools to fetch existing operations and confirm which fields the current project populates. If Apifox has added support for these extensions since this file was written, update this doc and `generate.md` accordingly.
