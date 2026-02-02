---
name: polish-document
description: Polish and optimize documentation following Mintlify writing standards, then validate with broken-links check. Use when improving, optimizing, polishing, or reviewing documentation quality.
---

# Polish Documentation

Optimize documents following Mintlify writing standards and validate links.

## Quick Start

1. Detect target files (see below)
2. Read standards: [standards.md](standards.md)
3. Read components: [components.md](components.md)
4. Optimize document content
5. Run `mint broken-links` to validate

## Target File Detection

**Default behavior**: Check for uncommitted changes in documentation directories.

```bash
git diff --name-only HEAD -- '*.mdx'
git diff --name-only --cached -- '*.mdx'
```

If uncommitted `.mdx` files exist:
- List the detected files
- Confirm with user before proceeding

If no uncommitted changes:
- Ask user to specify the document path(s)
- Example: "Which document would you like to polish? (e.g., zh/platform/xxx.mdx)"

## Optimization Workflow

### 1. Check Frontmatter

Ensure required fields exist:

```yaml
---
title: "Clear, specific title"
description: "Concise explanation of page purpose"
---
```

### 2. Improve Structure

**Before:** Plain text listing steps in a paragraph.

**After:** Use `<Steps>` component with clear step titles. Each step should have a descriptive title and concise content. Code examples within steps should use proper code blocks with language identifiers.

### 3. Add Callouts

**Before:** `Note: Delete operation cannot be undone.`

**After:** Use `<Warning>` component: wrap important warnings with the Warning component and add helpful context like backup reminders.

### 4. Format Code

**Before:** Inline code mixed with text like "Run command npm install"

**After:** Use separate code blocks with language identifiers. Add a brief introduction before the code block.

### 5. Validate Links

Run the broken links check:

```bash
mint broken-links
```

**Interpreting results:**

- **parsing error in .cursor/**: Ignore these errors. They come from skill/rule markdown files that use MDX syntax examples. These files are excluded from publishing via `.mintignore`.
- **broken links in polished files**: Must be fixed before completing the task.
- **broken links in other files**: Report to user but don't block the polishing task.

## Quick Reference

### Component Selection

| Content Type | Recommended Component |
|--------------|----------------------|
| Step-by-step instructions | `<Steps>` |
| Important warnings | `<Warning>` |
| Best practices | `<Tip>` |
| Additional notes | `<Note>` |
| Platform-specific | `<Tabs>` |
| Multi-language code | `<CodeGroup>` |

### Writing Style

- ✅ Use "you" (second person)
- ✅ Active voice
- ✅ Concise and direct
- ❌ Avoid "users should..."
- ❌ Avoid passive voice

## Output Report

After optimization, provide a report:

```markdown
## Optimization Report

### Structure Improvements
- [x] Added frontmatter
- [x] Restructured steps using Steps component

### Component Optimizations
- [x] Changed notes to Warning component
- [x] Added language identifier to code blocks

### Link Validation
- ✅ No broken links in polished files
- ⚠️ X broken links found in other files (not related to this task)
```

**Note:** If `mint broken-links` shows parsing errors from `.cursor/` directory, these can be safely ignored as they are excluded from publishing.

## Resources

- Writing standards: [standards.md](standards.md)
- Component reference: [components.md](components.md)
