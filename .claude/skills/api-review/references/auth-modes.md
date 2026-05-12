# Auth modes in the pgy registry

The `Auth` field on every row in `fc-pgy/logic/api/api_test.go` determines how the proxy authenticates the caller. **Only one of these modes qualifies as public for OpenAPI purposes: `all`.**

| Value | Constant | Public? | Meaning |
|---|---|---|---|
| `all` | `AuthPerson` | **yes** | Any "person-class" credential: either a console JWT session or an account-scoped `app_key`. This is the bulk of the public API and **the only mode we document**. |
| `optional` | `AuthOptional` | no | Attempts auth if a credential is present, but lets the request through either way. Used for public-viewer pages (status pages, RSS feeds) — **not** a supported `app_key` surface. |
| `none` | `AuthNone` | no | No auth at all (login endpoints, public metadata lookups, RSS/Atom feeds). Not part of the documented public API — we don't want to invite the world to hit these. |
| `jwt` | `AuthJWT` | no | Console JWT only. Blocks `app_key` explicitly — these are console-internal endpoints (password reset, member-level API key CRUD, etc.). |
| `data` | `AuthEngine` | no | API-key for data push/pull (different key type from `app_key`, used by collectors and engines). Separate product surface. |
| `integration` | `AuthIntegration` | no | Per-integration tokens used by webhook / alert-source pairings. Entirely separate key type. Documented per-integration elsewhere — **NOT** here. |

**Rule for this skill:** only emit OpenAPI for rows where `auth == "all"`. Everything else is skipped. Earlier iterations of the skill also accepted `optional` — that was wrong, because `optional`-mode endpoints respond differently to anonymous vs authenticated callers and are not a stable `app_key` contract.

## Why we drop `/event/push/*` even though some might look public

`/event/push/*` covers 60+ alert-source push routes (Prometheus remote write, Zabbix, Grafana, AWS CloudWatch, Alibaba Cloud, Slack bot commands, Jira sync, and so on). Every one of them authenticates with a **per-integration key** issued by Flashduty when a user creates the integration in the console — not with an `app_key`. They are documented as part of each individual integration's setup guide, not in the general API reference.

When filtering the registry, drop any path starting with `/event/push/` even if the registry shows `auth` as `all`, `optional`, or `none` — these routes are never callable with an account `app_key`.
