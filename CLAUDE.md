# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flashduty official documentation site, built with [Mintlify](https://mintlify.com/). Bilingual (Chinese `zh/` and English `en/`) with mirrored directory structures.

Three product modules: **On-call** (incident management), **RUM** (real user monitoring), **Monitors** (alert rules).

## Commands

```bash
# Local preview
mint dev

# Check broken links (run after any content changes)
mint broken-links

# Upload docs to Meilisearch for AI Q&A bot
MEILI_ENDPOINT=... MEILI_API_KEY=... MEILI_INDEX=... bash scripts/upload.sh
```

Prerequisite: `npm i -g mint`

## Architecture

- **`docs.json`** — Central Mintlify config: navigation structure, tabs, theme. All new pages must be registered here under the correct language → tab → group.
- **`zh/`** and **`en/`** — Mirror each other. Chinese is the source of truth; English is translated from it.
- **`glossary.md`** — Chinese-English terminology glossary for translation consistency.
- **`api-reference/`** — OpenAPI 3.1 spec files (per-module, per-language) powering the API Reference tab.
- **`.cursor/skills/`** — AI agent skills for translation (`translate-zh-to-en`) and polishing (`polish-document`).

## Documentation Workflow

1. Create/edit Chinese docs in `zh/` as `.mdx` files
2. Add the page path to `docs.json` navigation (both `zh` and `en` language sections)
3. Translate to English using the glossary at `glossary.md`
4. Run `mint broken-links` to validate

## Key Terminology (zh → en)

These are non-obvious translations that must stay consistent:

| Chinese | English |
|---------|---------|
| 协作空间 | channel |
| 故障 | incident |
| 分派策略 | escalation rule |
| 处理人员 | responders |
| 认领 | acknowledge |
| 值班表 | schedule |
| 新奇故障 | outlier incident |
| 静默策略 | silence rule |
| 抑制策略 | inhibit rule |
| 排除规则 | drop rule |
| 环节 | level |
| 告警聚合 | alert grouping |
| 规则告警聚合 | pattern alert grouping |
| 智能告警聚合 | intelligent alert grouping |

Full glossary: `glossary.md`

## Writing Conventions

- Use second person ("you" / "您")
- Active voice, present tense
- Every `.mdx` file needs frontmatter with `title` and `description`
- Sentence case for English titles (capitalize only first word)
- Use Mintlify components: `<Steps>`, `<Tabs>`, `<Note>`, `<Tip>`, `<Warning>`, `<Frame>`, `<CodeGroup>`, `<Accordion>`
- Component reference: `.cursor/skills/polish-document/components.md`

## Translation Rules

- Translate frontmatter `title` and `description`
- Keep MDX component tags unchanged, translate inner text only
- Keep code unchanged, translate comments only
- Update internal link paths from `zh/` to `en/`
- Keep image paths unchanged

## Link Validation Notes

`mint broken-links` may report parsing errors from `.cursor/` directory — these are safe to ignore (excluded from publishing via `.mintignore`). Only fix broken links in actual doc files.
