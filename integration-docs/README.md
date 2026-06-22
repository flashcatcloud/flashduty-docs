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

The `legacy/` directory is only for compatibility fallbacks when a document
exists in the old embedded docs contract but has not yet been migrated to the
Mintlify documentation tree.
