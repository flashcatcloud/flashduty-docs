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

## Release

The console reads these docs from two places, and each needs its own release:

| Console build | Where the docs come from | How they update |
|---|---|---|
| SaaS (production and test) | `window.FlashDocsZh` / `window.FlashDocsEn`, loaded at page start from `https://docs-cdn.flashcat.cloud/docs/{zh,en}.js` (test: `/test/docs/`) | Automatically, by GitHub Actions |
| On-premises (`saas-onpremises` build mode, no CDN script) | The `@flashcatcloud/flashduty-docs` npm package, bundled into the console at build time | Manually: publish a new npm version, then bump the console dependency |

The console prefers the CDN object and uses the npm package only when the CDN object is missing, which is always the case on-premises. A doc change therefore reaches SaaS as soon as the CDN updates, but reaches on-premises customers only after a new npm version is published and the console is rebuilt with it.

### SaaS: CDN (automatic)

The `Upload integration docs to OSS` workflow builds and checks the bundle, uploads `zh.js` / `en.js`, and refreshes the CDN:

- Push to `test` uploads to `/test/docs` (the test console).
- Push to `main` uploads to `/docs` (the production console).
- To re-upload without a new commit, run the workflow manually from the Actions tab and pick `development` or `production`.

When a console change reads a new doc key, release in this order: merge the docs to `main`, wait for the workflow to succeed, confirm that `https://docs-cdn.flashcat.cloud/docs/zh.js` contains the new key, then release the console. If the console ships first, the guide for that integration is empty until the CDN catches up.

### On-premises: npm package (manual)

1. Get the doc change merged into `main`.
2. In a PR to `main`, raise `version` in `integration-docs/package.json` (usually a patch bump). npm never accepts the same version twice; republishing an existing version fails with `409 Cannot publish over previously staged version`.
3. After that PR merges, create a GitHub Release from `main` with the tag `v<version>`, for example `v0.0.3`. Creating the release triggers the `Publish integration docs npm package` workflow, which builds, checks, and publishes the package. Use either the release or a manual run of the workflow, not both: the second run fails because the version is already published.
4. Confirm the new version is live: `npm view @flashcatcloud/flashduty-docs version`.
5. In the console repository (`fc-foundation-app`), run `pnpm add @flashcatcloud/flashduty-docs@<version>` and commit `package.json` and `pnpm-lock.yaml`. The workspace refuses versions published less than 24 hours ago. To use the new version the same day, add that exact version to `minimumReleaseAgeExclude` in `pnpm-workspace.yaml`, and remove the entry once it is older than 24 hours.
6. Build the on-premises console package as usual; the new docs are bundled into it.

You don't need a new npm version for every doc change. Publish one when an on-premises release needs the updated guides, typically when a new integration is added or an existing guide changes in a way customers must follow.
