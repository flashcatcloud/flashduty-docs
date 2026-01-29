# Flashduty Documentation - AI Agent Guide

This document provides guidance for AI agents interacting with this project.

## Project Overview

Official documentation for Flashduty, built with [Mintlify](https://mintlify.com/). Contains bilingual documentation in Chinese and English.

## Directory Structure

```
flashduty-docs/
├── zh/                    # Chinese documentation
├── en/                    # English documentation (mirrors zh/ structure)
├── logo/                  # Logo assets
├── docs.json              # Mintlify configuration
└── .cursor/
    └── skills/            # Agent Skills
        ├── translate-zh-to-en/   # Translation skill
        │   ├── SKILL.md          # Translation guide
        │   └── glossary.md       # Terminology glossary
        └── polish-document/      # Polishing skill
            ├── SKILL.md          # Polishing guide
            ├── standards.md      # Writing standards
            └── components.md     # Component reference
```

## Available Skills

### translate-zh-to-en

Translate Chinese documentation to English.

**Trigger scenarios**: translate, Chinese to English, zh to en

**Default behavior**: 
- Detects uncommitted `.mdx` changes in `zh/` directory
- If no changes found, asks user to specify document path

**Resources**:
- `glossary.md` - Complete terminology glossary (80+ terms, categorized)

### polish-document

Polish and optimize documentation following Mintlify standards.

**Trigger scenarios**: polish, optimize, improve documentation

**Default behavior**:
- Detects uncommitted `.mdx` changes in repository
- If no changes found, asks user to specify document path

**Resources**:
- `standards.md` - Writing standards (style, organization, code examples)
- `components.md` - Mintlify component reference (Steps, Tabs, Callouts, etc.)

## Common Commands

```bash
# Local preview
mint dev

# Check broken links
mint broken-links
```

## Documentation Workflow

1. Create or edit Chinese documentation in `zh/`
2. Use **polish-document** to optimize structure and content
3. Use **translate-zh-to-en** to translate to `en/`
4. Update navigation in `docs.json`
5. Run `mint broken-links` to validate
