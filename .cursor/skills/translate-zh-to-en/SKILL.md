---
name: translate-zh-to-en
description: Translate Chinese documentation to English following the terminology glossary. Use when translating documents from zh/ to en/, or when the user mentions Chinese to English translation.
---

# Translate Chinese to English

Translate documents from `zh/` directory to `en/` directory.

## Quick Start

1. Detect target files (see below)
2. Read glossary: [glossary.md](glossary.md)
3. Translate document content
4. Save to corresponding `en/` path

## Target File Detection

**Default behavior**: Check for uncommitted changes in `zh/` directory.

```bash
git diff --name-only HEAD -- 'zh/*.mdx'
git diff --name-only --cached -- 'zh/*.mdx'
```

If uncommitted `.mdx` files exist in `zh/`:
- List the detected files
- Confirm with user before proceeding

If no uncommitted changes:
- Ask user to specify the document path(s)
- Example: "Which document would you like to translate? (e.g., zh/platform/xxx.mdx)"

## Translation Rules

### Language Quality

- **Professional & concise**: Avoid Chinglish, use native English expressions
- **Grammatically correct**: Ensure proper sentence structure
- **Consistent**: Use the same terminology throughout the document

### Formatting

- **Sentence case**: Capitalize only the first letter of titles/sentences
- **Punctuation**: Add proper punctuation for complete sentences
- **Variables**: Keep placeholder order unchanged

### Structure Preservation

| Element | Handling |
|---------|----------|
| YAML frontmatter | Translate `title` and `description` |
| MDX components | Keep tags unchanged, translate inner text |
| Code blocks | Keep code unchanged, translate comments only |
| Internal links | Update path prefix to `en/` |
| Image paths | Keep unchanged |

## Example

**Input** `zh/on-call/escalate.mdx`:

```mdx
---
title: "配置分派策略"
description: "了解如何配置分派策略来管理故障升级"
---

## 概述

分派策略定义了告警如何分配给处理人员。

<Note>
建议至少配置两个环节的分派策略。
</Note>
```

**Output** `en/on-call/escalate.mdx`:

```mdx
---
title: "Configure escalation rules"
description: "Learn how to configure escalation rules to manage incident escalation"
---

## Overview

Escalation rules define how alerts are assigned to responders.

<Note>
It is recommended to configure at least two levels of escalation rules.
</Note>
```

## Key Terminology

Always read the full glossary before translating: [glossary.md](glossary.md)

**Quick reference**:

| Chinese | English |
|---------|---------|
| 协作空间 | channel |
| 故障 | incident |
| 告警 | alert |
| 分派策略 | escalation rule |
| 处理人员 | responders |
| 认领 | acknowledge |
| 值班表 | schedule |

## Checklist

- [ ] Check git diff for uncommitted zh/ files
- [ ] Read terminology glossary
- [ ] Translate frontmatter (title, description)
- [ ] Use correct terminology
- [ ] Preserve MDX component structure
- [ ] Update internal link paths
- [ ] Apply Sentence case capitalization
- [ ] Verify output path mirrors source path
