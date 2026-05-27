# Security scheme

Public Flashduty APIs are only callable via `app_key`. The proxy (fc-pgy) accepts it as a query parameter and converts it into an internal `Flashcat-Context` header before forwarding to the backend service.

The `Flashcat-Context` header you see in backend handlers (e.g., `fc-event/cmd/server`) is therefore a **proxy-internal** artifact. It is not part of the public contract and must never appear in generated OpenAPI specs.

## The only public entry

```
?app_key=<your-app-key>
```

`app_key` is:

- Issued per account from the Flashduty console (see the Account → API Keys page).
- Scoped to the account; some operations also require the account member that owns the key to have matching RBAC permission.
- Equivalent to a logged-in session — that's why the auth mode in the registry is literally named `"all"` (which internally maps to the constant `AuthPerson`): "any person-class credential", JWT or app_key.

## OpenAPI blocks to emit

Top-level `security`:

```json
"security": [
  { "AppKeyAuth": [] }
]
```

`components.securitySchemes`:

```json
{
  "AppKeyAuth": {
    "type": "apiKey",
    "in": "query",
    "name": "app_key",
    "description": "App key issued from the Flashduty console. Required on every public API call. Keep it secret — it grants the same access as the owning account."
  }
}
```

Every operation automatically inherits the top-level `security` block, so you do not need to repeat `security` on each operation unless you are overriding it (which we aren't — every public operation is app_key-protected).

## What to leave out

- `Flashcat-Context` headers in request/response. Do not document them.
- `Authorization` / `Bearer` patterns from the legacy Apifox export. Those were used for internal JWT auth and are not part of the app_key flow.
- `DD-API-KEY` / Datadog-compatible headers in `securitySchemes` of the legacy file. Only include them if the specific operation is explicitly a Datadog-compatibility shim — those are rare and documented separately.

## Rate limiting note

Every API is rate-limited by pgy (`RateLimits` in the registry — not surfaced to callers). If a call hits the limit, the response is a standard error envelope with code `429` and a human message. This is covered by the shared `ErrorResponse` schema; per-endpoint rate limit details are not worth inlining.
