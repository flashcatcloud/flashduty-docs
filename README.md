# Flashduty Documentation

English | [中文](README_zh.md)

[![Mintlify](https://img.shields.io/badge/Built_with-Mintlify-8B5CF6?style=flat-square)](https://mintlify.com/)
[![Docs](https://img.shields.io/badge/Live-docs.flashcat.cloud-blue?style=flat-square)](https://docs.flashcat.cloud)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

Official documentation for [Flashduty](https://flashcat.cloud/), bilingual (Chinese & English), built with [Mintlify](https://mintlify.com/). Covers On-call incident management, RUM real user monitoring, and Monitors alert rules — **390+** pages in total.

---

## Product Modules

| Module | Description | Docs Path |
|--------|-------------|-----------|
| **On-call** | Incident management, alert routing, escalation rules, schedule management | `*/on-call/` |
| **RUM** | Real User Monitoring, frontend performance and error tracking | `*/rum/` |
| **Monitors** | Multi-source alert rule configuration | `*/monitors/` |
| **Platform** | Account management, SSO, permissions, API keys | `*/platform/` |
| **OpenAPI** | REST API reference | `*/openapi/` |

---

## Quick Start

### Prerequisites

```bash
npm i -g mint
```

### Local Preview

```bash
mint dev
```

Visit `http://localhost:3000` to view the docs.

### Check Broken Links

```bash
mint broken-links
```

> Run this after every content change to catch dead links early.

---

## Contributing

We welcome community contributions! Whether it's fixing a typo, improving descriptions, or adding new documentation — every bit helps.

### Adding or Editing Documentation

1. **Edit Chinese docs** — Create or edit `.mdx` files under `zh/` (Chinese is the source language)
2. **Update navigation** — Add the page path in `docs.json` for both `zh` and `en` sections
3. **Translate to English** — Create the corresponding file under `en/`, keeping the path structure consistent
4. **Validate links** — Run `mint broken-links` to confirm no broken links

### Frontmatter Format

Every `.mdx` file must include:

```yaml
---
title: "Clear, specific title"
description: "Concise explanation of page purpose"
---
```

### Writing Guidelines

- Use second person ("you")
- Use active voice, present tense
- Use sentence case for English titles (capitalize only first word)
- Leverage Mintlify components: `<Steps>`, `<Tabs>`, `<Note>`, `<Tip>`, `<Warning>`, `<Frame>`, `<CodeGroup>`

---

## Directory Structure

```
flashduty-docs/
├── zh/                    # Chinese docs (source of truth)
│   ├── on-call/           # On-call incident management
│   ├── rum/               # Real User Monitoring
│   ├── monitors/          # Alert rule configuration
│   ├── platform/          # Platform settings
│   ├── openapi/           # API documentation
│   ├── compliance/        # Security compliance
│   └── changelog/         # Changelog
├── en/                    # English docs (mirrors zh/)
├── api-reference/         # OpenAPI 3.1 specs (per-module, per-language)
├── glossary.md            # Chinese-English terminology glossary
├── docs.json              # Mintlify configuration & navigation
└── logo/                  # Logo assets
```

---

## Translation

Chinese is the source language; English is translated from it. When translating:

- Translate frontmatter `title` and `description`
- Keep MDX component tags unchanged, translate inner text only
- Keep code blocks unchanged, translate comments only
- Update internal link paths from `zh/` to `en/`
- Keep image paths unchanged

### Key Terminology

| Chinese | English |
|---------|---------|
| 协作空间 | channel |
| 故障 | incident |
| 分派策略 | escalation rule |
| 值班表 | schedule |
| 认领 | acknowledge |
| 静默策略 | silence rule |
| 抑制策略 | inhibit rule |
| 排除规则 | drop rule |

Full glossary: [`glossary.md`](glossary.md)

---

## Related Resources

| Resource | Link |
|----------|------|
| Flashduty Docs | [docs.flashcat.cloud](https://docs.flashcat.cloud) |
| Flashduty Console | [console.flashcat.cloud](https://console.flashcat.cloud/) |
| Flashduty Website | [flashcat.cloud](https://flashcat.cloud/) |
| MCP Server | [flashduty-mcp-server](https://github.com/flashcatcloud/flashduty-mcp-server) |
| Terraform Provider | [terraform-provider-flashduty](https://github.com/flashcatcloud/terraform-provider-flashduty) |
| Mintlify Docs | [mintlify.com/docs](https://mintlify.com/docs) |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
