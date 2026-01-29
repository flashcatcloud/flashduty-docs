# Mintlify Writing Standards

Technical documentation writing guidelines for quality and consistency.

## Language & Style

### Voice & Tone

- **Second person**: Use "you" instead of "users" or "we"
- **Active voice**: Prefer active over passive voice
- **Tense**: Present tense for current state, future tense for results
- **Concise**: Avoid redundant words and unnecessary modifiers

### Terminology

- Define terms on first use
- Maintain consistent terminology throughout
- Reference project glossary when available

## Content Organization

### Information Architecture

```
Inverted Pyramid Structure:
┌─────────────────────┐
│   Most Important    │  ← Reader sees first
├─────────────────────┤
│   Supporting Details│
├─────────────────────┤
│   Background Info   │  ← Optional reading
└─────────────────────┘
```

### Progressive Disclosure

1. Basic concepts → Advanced features
2. Common use cases → Edge cases
3. Quick start → Detailed configuration

### Headings

- Use descriptive, keyword-rich headings
- Start with H2 (`##`), maintain clear hierarchy
- Avoid skipping levels (e.g., H2 directly to H4)

## Page Structure

### Required Frontmatter

```yaml
---
title: "Clear, specific title"
description: "Concise explanation of page purpose"
---
```

### Recommended Sections

1. **Overview** - Brief explanation of feature and value
2. **Prerequisites** - What's needed before starting
3. **Steps/Configuration** - Specific instructions
4. **Examples** - Real-world use cases
5. **FAQ** - Common questions or troubleshooting

## Code Examples

### Requirements

- ✅ Complete, runnable examples
- ✅ Specify language and filename
- ✅ Include error handling
- ✅ Use realistic data structures
- ❌ Never include real API keys

### Format

```javascript filename.js
// Good: Specify language and filename
const config = {
  apiKey: process.env.API_KEY,
  timeout: 5000
};
```

## Accessibility

- Provide descriptive alt text for images
- Use specific link text (not "click here")
- Ensure clear heading hierarchy
- Use lists and tables to enhance readability

## Quality Checklist

### Structure
- [ ] Complete frontmatter included
- [ ] Inverted pyramid structure
- [ ] Clear heading hierarchy

### Content
- [ ] Second person and active voice
- [ ] Consistent terminology
- [ ] Clear, actionable steps

### Code
- [ ] Complete, runnable examples
- [ ] Language specified
- [ ] No sensitive information

### Links
- [ ] Internal links valid
- [ ] External links accessible
