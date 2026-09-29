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

# Upload docs to Meilisearch (for AI Q&A bot)
MEILI_ENDPOINT=... MEILI_API_KEY=... MEILI_INDEX=... bash scripts/upload.sh
```

## Documentation Workflow

1. Create or edit Chinese documentation in `zh/`
2. Use **polish-document** to optimize structure and content
3. Use **translate-zh-to-en** to translate to `en/`
4. Update navigation in `docs.json`
5. Run `mint broken-links` to validate

## Retired Monitors Features

- The monitor targets feature and monit-agent integration are retired. Do not recreate `zh/monitors/targets/*` or `en/monitors/targets/*`, restore their navigation, or describe target lists and per-row AI analysis as available. Residual routes or components in source code are not evidence of a supported feature. Preserve the overview URL redirects to the Monitors quickstart.
