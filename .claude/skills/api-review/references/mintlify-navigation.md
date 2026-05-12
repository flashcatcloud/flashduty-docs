# Mintlify navigation and icons

Mintlify renders the Flashduty API reference. The `api-reference/openapi.{en,zh}.json` files are the source of truth for operation content, but the **navigation structure** — the sidebar tree with icons and grouping — is driven by `docs.json` in the docs repo, not by OpenAPI tags.

This is important to internalize: the OpenAPI `tags` array and our `x-apifox-folder` extension do NOT populate the Mintlify sidebar. Mintlify only reads `docs.json`. When you add a new module to the skill, you must update *both* `mapping.yaml` (to drive the openapi generation) and `docs.json` (to drive the sidebar).

## The API Reference tab shape

`docs.json` has a tab per language per navigation top-level. The API Reference tab looks like this (Chinese version shown; the English tab is identical in structure with translated labels):

```json
{
  "tab": "API 参考",
  "icon": "terminal",
  "openapi": "api-reference/openapi.zh.json",
  "groups": [
    {
      "group": "On-call",
      "icon": "light-emergency-on",
      "pages": [
        {
          "group": "模板管理",
          "icon": "envelope-open-text",
          "pages": [
            "POST /template/info",
            "POST /template/list",
            "POST /template/create",
            "POST /template/update",
            "POST /template/delete",
            "POST /template/preview",
            "POST /template/enable",
            "POST /template/disable"
          ]
        }
      ]
    }
  ]
}
```

Three things to notice:

1. **`openapi` at the tab level** tells Mintlify where to resolve `"POST /template/info"`-style page references. Child groups inherit it unless they declare their own, which lets you mix multiple specs under one tab if ever needed (we don't).
2. **Nested groups** — a group's `pages` array can contain both page strings and objects. Each nested object is another group with its own `group` / `icon` / `pages`. Mintlify renders nested groups as collapsible sub-folders. We use this for the two-level "module → sub-module" structure: `On-call → 模板管理`.
3. **`"METHOD /path"` references** specific operations from the openapi spec by their exact method + path. The order in the `pages` array is the order Mintlify renders them in the sidebar — so you control sort order explicitly, no alphabetical surprises.

## Icon per module

Every module and sub-module needs an `icon` field. Mintlify uses Font Awesome names. The skill stores icons in `mapping.yaml`:

```yaml
module_parents:
  on-call:
    en: "On-call"
    zh: "On-call"
    icon: "light-emergency-on"
  platform:
    en: "Platform"
    zh: "平台"
    icon: "gear"
  monitors:
    en: "Monitors"
    zh: "Monitors"
    icon: "chart-area"
  rum:
    en: "RUM"
    zh: "RUM"
    icon: "monitor-waveform"

modules:
  on-call/template:
    tag_en: "Templates"
    tag_zh: "模板管理"
    icon: "envelope-open-text"
    # ...
```

When you add a new sub-module, pick an icon that visually matches the feature. Good Font Awesome choices for the Flashduty domain:

| Scope | Icon |
|---|---|
| on-call/incident | `siren-on` |
| on-call/channel | `comments` |
| on-call/alert | `bell` |
| on-call/schedule | `calendar-days` |
| on-call/integration | `plug` |
| on-call/enrichment | `tags` |
| on-call/template | `envelope-open-text` |
| on-call/insight | `chart-line` |
| on-call/statuspage | `signal-stream` |
| platform/member | `users` |
| platform/team | `users-line` |
| platform/account | `id-card` |
| platform/sso | `key` |
| platform/audit | `scroll` |
| platform/preference | `sliders` |
| monitors/rule | `diamond-exclamation` |
| monitors/folder | `folder-tree` |
| monitors/datasource | `database` |
| monitors/store | `books` |
| monitors/edge | `server` |
| monitors/entity | `cube` |
| monitors/problem | `triangle-exclamation` |
| rum/application | `mobile-screen-button` |
| rum/issue | `bug` |
| rum/error | `circle-exclamation` |
| rum/session-replay | `clapperboard-play` |
| rum/facet | `filter` |
| rum/sourcemap | `map` |

If you need a different icon, pick one from [fontawesome.com/icons](https://fontawesome.com/icons) — any solid-style icon works.

## How the generate phase updates docs.json

The generate phase treats `docs.json` as a semi-managed file: it only touches the API Reference tab(s), leaving every other tab untouched. The update pattern:

1. Load `docs.json`.
2. Find the tab whose `tab` field matches `"API 参考"` (zh) or `"API Reference"` (en), or whose `openapi` starts with `api-reference/openapi.`. There should be exactly one per language.
3. Rebuild that tab from `mapping.yaml` plus the set of operations present in the newly-written openapi spec. Group by parent, then by sub-module, then list each operation as a `"POST /path"` page reference in the order it appears in the spec.
4. Write `docs.json` back.
5. Validate with `mint broken-links` — Mintlify will error loudly if any referenced operation doesn't exist in the spec.

This way, after a scoped `--scope on-call/incident` run, the sidebar picks up the new incident operations automatically without the user having to touch `docs.json` by hand.

## Things NOT to rely on

- **`tags` in OpenAPI for Mintlify navigation** — Mintlify ignores the OpenAPI `tags` field when an explicit `groups` structure is present. Tags still get emitted to the spec (they work in Apifox and any other OpenAPI renderer), but Mintlify sidebar is driven by docs.json alone.
- **`x-mint` at tag level** — not documented to work for tag-level icons (operation-level `x-mint` is a separate feature we haven't needed).
- **Alphabetical auto-sort** — the sidebar respects the order in `pages` exactly. Don't assume operations will be grouped or sorted for you.
