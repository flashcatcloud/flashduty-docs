# Flashduty Documentation

English | [中文](README.md)

Official documentation for [Flashduty](https://flashcat.cloud/), built with [Mintlify](https://mintlify.com/).

## Directory Structure

```
flashduty-docs/
├── zh/                    # Chinese documentation
│   ├── on-call/           # On-call incident management
│   ├── rum/               # Real User Monitoring
│   ├── monitors/          # Alert rule configuration
│   ├── platform/          # Platform settings
│   ├── openapi/           # API documentation
│   ├── compliance/        # Security compliance
│   └── changelog/         # Changelog
├── en/                    # English documentation (mirrors zh/)
├── logo/                  # Logo assets
├── docs.json              # Mintlify configuration
└── .cursor/skills/        # AI Agent Skills
```

## Product Modules

| Module | Description |
|--------|-------------|
| **On-call** | Incident management, alert routing, escalation rules, schedule management |
| **RUM** | Real User Monitoring, frontend performance and error tracking |
| **Monitors** | Multi-source alert rule configuration |

## Local Development

### Prerequisites

```bash
npm i -g mint
```

### Common Commands

```bash
# Local preview
mint dev

# Check broken links
mint broken-links
```

## Adding Documentation

### 1. Create Document

Create `.mdx` file in the appropriate directory:

```yaml
---
title: "Clear, specific title"
description: "Concise explanation of page purpose"
---
```

### 2. Update Navigation

Add page path in `docs.json`:

```json
{
  "group": "Quick Start",
  "pages": ["en/on-call/quickstart/quickstart"]
}
```

### 3. Bilingual Sync

- Maintain consistent structure between Chinese and English
- English docs go in `en/` directory, mirroring `zh/` paths
- Use `translate-zh-to-en` Skill for translation

## Writing Guidelines

### Style

- Use second person ("you")
- Use active voice
- Keep it concise and direct

### Common Components

| Component | Purpose |
|-----------|---------|
| `<Steps>` | Step-by-step instructions |
| `<Tabs>` | Platform-specific content |
| `<CodeGroup>` | Multi-language code |
| `<Note>` / `<Tip>` / `<Warning>` | Callouts |
| `<Frame>` | Image container |

### Code Examples

- Provide complete, runnable examples
- Specify language and filename
- Never include real API keys

## AI Assistance

This project provides two AI Skills:

| Skill | Purpose |
|-------|---------|
| `translate-zh-to-en` | Translate Chinese docs to English |
| `polish-document` | Polish and optimize documentation |

See [AGENTS.md](AGENTS.md) for details.

## Links

- [Flashduty Console](https://console.flashcat.cloud/)
- [Flashduty Website](https://flashcat.cloud/)
- [Mintlify Documentation](https://mintlify.com/docs)
