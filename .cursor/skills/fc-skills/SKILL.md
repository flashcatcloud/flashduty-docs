---
name: fc-skills
description: Applies Flashcat development workflows from the fc-skills skill pack (session summary, git sync, migration checklist, Apifox sync, Mermaid workflow docs, doc-review vs source repos). Resolves instructions by reading SKILL.md files under FC_SKILLS_ROOT. Use when the user mentions fc-skills, Flashcat workflows, or any of the named workflows (done, summary-branch, sync-branch, sync-dev, migration-checklist, apifox-sync, workflow-doc, doc-review), or when matching Claude Code slash-command behavior in Cursor.
---

# fc-skills (Cursor)

Use the **fc-skills** repository as the source of truth for workflow steps. Do not paraphrase long procedures from memory — read the corresponding `SKILL.md` and follow it.

## Resolve skill root

1. If environment variable `FC_SKILLS_ROOT` is set, use it as the absolute path to the `fc-skills` repo root.
2. Otherwise try `~/go/src/github.com/flashcatcloud/fc-skills`.
3. If that path does not exist, tell the user to clone `flashcatcloud/fc-skills` and set `FC_SKILLS_ROOT`, or report the missing path and stop.

## Route to the right SKILL.md

| User intent | Read and follow |
|-------------|-----------------|
| End session summary, `/done` | `skills/done/SKILL.md` |
| Summarize branch vs base | `skills/summary-branch/SKILL.md` |
| Commit + push current branch only | `skills/sync-branch/SKILL.md` |
| Commit, push, merge to `dev`, push | `skills/sync-dev/SKILL.md` |
| Production migration checklist from diff | `skills/migration-checklist/SKILL.md` |
| Sync Apifox / OpenAPI vs code | `skills/apifox-sync/SKILL.md` |
| Generate Mermaid workflow doc | `skills/workflow-doc/SKILL.md` |
| Doc drift / coverage / fix docs | `skills/doc-review/SKILL.md` |

For a full path table and file list (e.g. `doc-review` `analyze.md`, `fix.md`), see [reference.md](reference.md).

## Execution rules

1. **Read first:** `Read` the target `SKILL.md` under `FC_SKILLS_ROOT` before running commands.
2. **Sub-resources:** If that SKILL points to sibling files (e.g. `analyze.md`, `fix.md`, `mapping.yaml`), read them from the same skill directory under `fc-skills`.
3. **Git:** `sync-branch` and `sync-dev` require `git_write` permission when executing. Never force-push unless the user explicitly orders it and the project allows it (fc-skills default: never force push).
4. **doc-review:** Use `skills/doc-review/mapping.yaml` from the clone — not `.claude/skills/...` (that path is for the Claude Code plugin install).
5. **Apifox:** Follow `apifox-sync` only when Apifox MCP or equivalent tools are available; otherwise state the prerequisite and stop.

## Quick argument hints

- Pass through optional user arguments (commit message, base branch, `/doc-review` flags) exactly as the upstream SKILL describes.
- If the user names a skill ambiguously, prefer the table above and confirm once if two workflows could match.
