# Response envelope

Every public Flashduty API is reached through the fc-pgy proxy. The proxy passes the request to a backend service, lets the backend render its response via `srv.JSON(ctx, ...)` from `go-pkg/srv/render.go`, and then forwards the response bytes unchanged. The shape that leaves pgy is exactly the shape `srv.JSON` writes.

## The wrapper struct

Source: `go-pkg/srv/render.go`:

```go
type Resp struct {
    RequestID string `json:"request_id"`
    Err       *Error `json:"error,omitempty"`
    Data      any    `json:"data,omitempty"`
}
```

And the error payload, from `go-pkg/srv/error.go`:

```go
type Error struct {
    Code           ErrorCode `json:"code"`          // STRING, not integer
    Message        string    `json:"message"`
    HTTPStatusCode int       `json:"-"`             // not serialized
    stack          string    `json:"-"`             // not serialized
}

type ErrorCode string  // enum of string constants below
```

**`code` is a string, not an integer.** This is the most important thing in this document. It's a named machine-readable enum — not a numeric status code. HTTP status lives only in the response line, not in the body.

On success (HTTP 200), the wire payload is:

```json
{
  "request_id": "01HK8XQE...",
  "data": { "...": "handler-specific" }
}
```

On error (any non-2xx), the payload is:

```json
{
  "request_id": "01HK8XQE...",
  "error": {
    "code": "InvalidParameter",
    "message": "The specified parameter template_id is not valid."
  }
}
```

**Document exactly `code` and `message` — nothing else.** Do not add any other fields to `DutyError` properties, response examples, or shared response schemas. No `raw_message`, no `i18n_key`, no `details`, no stack trace. Surfacing fields that aren't part of the public contract misleads consumers and comes back as a bug report.

## The complete ErrorCode enum

All 20 values are stable wire strings — treat this list as the enum source of truth. When generating openapi, emit the full list as `enum` on `DutyError.code` so SDK generators and API consumers can exhaustively match on it. The HTTP status is informational only (not part of the body) — include it in the documentation so the reader knows which HTTP status goes with which error.

| Code (enum value) | HTTP | Default message | Typical cause |
|---|---|---|---|
| `OK` | 200 | OK. | Not typically returned in an error payload — reserved. |
| `InvalidParameter` | 400 | The specified parameter %v is not valid. | Missing field, bad type, failed `binding:` validation. |
| `BadRequest` | 400 | Bad request. | Generic 400 used when nothing more specific fits. |
| `InvalidContentType` | 400 | Cannot accept this content-type. | Content-Type header isn't application/json. |
| `ResourceNotFound` | 400 | The resource you request is not found. | Lookup by ID returned nil. Note: 400, **not** 404 (historical choice). |
| `NoLicense` | 400 | No available license. | License-gated feature with no active license. |
| `ReferenceExist` | 400 | There still are associated resources, deletion is blocked. | Delete attempted while other entities still reference the target. |
| `Unauthorized` | 401 | You are unauthorized. | Missing or invalid app_key / JWT. |
| `BalanceNotEnough` | 402 | The account's balance is not enough, recharge required. | Billing-gated operation hit an empty wallet. |
| `AccessDenied` | 403 | Access Denied. | Caller authenticated but RBAC denies the action. |
| `RouteNotFound` | 404 | The route you request is not found. | Unknown URL path. |
| `MethodNotAllowed` | 405 | The method you request to the path is not allowed. | Wrong HTTP verb for an otherwise-known path. |
| `UndonedOrderExist` | 409 | Undone order exists, try again in a few minutes. | Outstanding billing order blocks a new one. (Note wire typo "Undoned" — preserved for compatibility.) |
| `RequestLocked` | 423 | The operation is locked due to too many failures. | Repeated failures triggered a temporary lock (auth, dangerous ops). |
| `RequestEntityTooLarge` (wire: `EntityTooLarge`) | 413 | The request entity is too large. | Request body exceeds the configured max size. |
| `RequestTooFrequently` | 429 | Request too frequently. | Per-API, per-account, or per-integration rate limit. |
| `RequestVerifyRequired` | 428 | The operation is not verified, a verification code is required. | Second-factor verification required but not supplied. |
| `DangerousOperation` | 428 | The operation you request is dangerous, a verification code is required. | High-risk operation gated behind MFA. |
| `InternalError` | 500 | We encountered an internal error, and it has been reported. Please try again later. %v | Unhandled server exception. Include request_id in the bug report. |
| `ServiceUnavailable` | 503 | The service is currently experiencing high load, please try again later. | Backend dependency (mongo, redis, upstream) is down or degraded. |

## OpenAPI components

Inject these into `components.schemas` of the generated file:

```json
{
  "ErrorCode": {
    "type": "string",
    "description": "Flashduty error code enum. Every failed API response sets `error.code` to one of these values. The value is a stable wire string — not a localized message and not a numeric status. HTTP status is informational (see the table in references/response-envelope.md).",
    "enum": [
      "OK",
      "InvalidParameter",
      "BadRequest",
      "InvalidContentType",
      "ResourceNotFound",
      "NoLicense",
      "ReferenceExist",
      "Unauthorized",
      "BalanceNotEnough",
      "AccessDenied",
      "RouteNotFound",
      "MethodNotAllowed",
      "UndonedOrderExist",
      "RequestLocked",
      "EntityTooLarge",
      "RequestTooFrequently",
      "RequestVerifyRequired",
      "DangerousOperation",
      "InternalError",
      "ServiceUnavailable"
    ]
  },
  "DutyError": {
    "type": "object",
    "description": "Error payload inside the response envelope. Present only on non-2xx responses.",
    "properties": {
      "code": { "$ref": "#/components/schemas/ErrorCode" },
      "message": {
        "type": "string",
        "description": "Human-readable error message, localized by the caller's Accept-Language. May contain field names, IDs, or other context from the failing request."
      }
    },
    "required": ["code", "message"]
  },
  "ResponseEnvelope": {
    "type": "object",
    "description": "Standard response envelope used by every Flashduty public API. On success `data` contains the endpoint-specific payload and `error` is absent. On failure `error` is present and `data` is absent. `request_id` is always present and is also mirrored in the `Flashcat-Request-Id` response header.",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "Unique ID for this request. Mirrored in the Flashcat-Request-Id header. Include it when reporting issues.",
        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4"
      },
      "error": { "$ref": "#/components/schemas/DutyError" },
      "data": { "description": "Endpoint-specific payload. See each operation's 200 response schema." }
    },
    "required": ["request_id"]
  },
  "ErrorResponse": {
    "type": "object",
    "description": "Response envelope for errors. `error` is required; `data` is absent.",
    "properties": {
      "request_id": { "type": "string", "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4" },
      "error": { "$ref": "#/components/schemas/DutyError" }
    },
    "required": ["request_id", "error"]
  }
}
```

## Shared responses

```json
{
  "BadRequest": {
    "description": "Invalid request — usually a missing or malformed parameter.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" },
        "examples": {
          "missingParameter": {
            "summary": "Missing required parameter",
            "value": {
              "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
              "error": {
                "code": "InvalidParameter",
                "message": "The specified parameter template_id is not valid."
              }
            }
          }
        }
      }
    }
  },
  "Unauthorized": {
    "description": "Missing or invalid app_key.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" },
        "examples": {
          "missingAppKey": {
            "value": {
              "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
              "error": { "code": "Unauthorized", "message": "You are unauthorized." }
            }
          }
        }
      }
    }
  },
  "Forbidden": {
    "description": "The app_key is valid but lacks permission for this operation.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" },
        "examples": {
          "noEditPermission": {
            "value": {
              "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
              "error": { "code": "AccessDenied", "message": "Access Denied." }
            }
          }
        }
      }
    }
  },
  "NotFound": {
    "description": "The referenced resource does not exist or has been deleted. Note: Flashduty historically uses HTTP 400 with code `ResourceNotFound` for missing domain entities; a true 404 is reserved for unknown routes.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" }
      }
    }
  },
  "TooManyRequests": {
    "description": "Rate limit hit. Either the global API limit, a per-account limit, or a per-integration limit.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" },
        "examples": {
          "rateLimited": {
            "value": {
              "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
              "error": { "code": "RequestTooFrequently", "message": "Request too frequently." }
            }
          }
        }
      }
    }
  },
  "ServerError": {
    "description": "Unexpected server-side error. Include the request_id when reporting.",
    "content": {
      "application/json": {
        "schema": { "$ref": "#/components/schemas/ErrorResponse" },
        "examples": {
          "internal": {
            "value": {
              "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
              "error": {
                "code": "InternalError",
                "message": "We encountered an internal error, and it has been reported. Please try again later."
              }
            }
          }
        }
      }
    }
  }
}
```

Every operation's `responses` object reuses these via `$ref`. The 200 response is the only one that varies — it uses `allOf` to combine `ResponseEnvelope` with an endpoint-specific `data` schema. The 200 response should also carry a realistic inline `example` of `data` so API consumers see the concrete shape at a glance.

`request_id` is also set in the `Flashcat-Request-Id` response header for log correlation. Document it in operation responses as a header for completeness.

The schemas and shared responses above are the single source of truth for envelope generation. The generate phase injects them into `components.schemas` and `components.responses` of every output file, replacing any stale versions that may already exist.
