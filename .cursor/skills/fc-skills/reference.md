# fc-skills reference for Cursor

## Repository

- **Remote:** `github.com/flashcatcloud/fc-skills` (Claude Code plugin; same skills apply in Cursor.)
- **Default local clone:** `~/go/src/github.com/flashcatcloud/fc-skills`
- **Override:** set `FC_SKILLS_ROOT` to the absolute path of your clone if it differs.

## Skill index → SKILL.md path

| Skill | Relative path under `FC_SKILLS_ROOT` |
|-------|--------------------------------------|
| done | `skills/done/SKILL.md` |
| summary-branch | `skills/summary-branch/SKILL.md` |
| sync-branch | `skills/sync-branch/SKILL.md` |
| sync-dev | `skills/sync-dev/SKILL.md` |
| migration-checklist | `skills/migration-checklist/SKILL.md` |
| apifox-sync | `skills/apifox-sync/SKILL.md` |
| workflow-doc | `skills/workflow-doc/SKILL.md` |
| doc-review | `skills/doc-review/SKILL.md` |

## doc-review extra files

Under `skills/doc-review/`:

- `mapping.yaml` — module ↔ repo path mapping (`base_path` rules in SKILL.md)
- `analyze.md` — Phase 1 (Analyze)
- `fix.md` — Phase 2 (Fix)
- `prompts/diff.md`, `prompts/audit.md` — prompt templates

## Claude vs Cursor differences

- **Install:** Claude uses `/plugin install fc-skills@fc-skills`. Cursor reads the same skill tree from a local clone (or copy) under `FC_SKILLS_ROOT`.
- **done output path:** Original uses `~/.claude/sessions/`. Keep that path unless the user asks otherwise; create `~/.claude/sessions` if missing.
- **doc-review:** In the cloned repo, mapping is `skills/doc-review/mapping.yaml`, not `.claude/skills/doc-review/mapping.yaml` (that path is for the plugin install layout).

## Plugin metadata (for humans)

See `fc-skills/.claude-plugin/plugin.json` for plugin name and version.
