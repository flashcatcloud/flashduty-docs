#!/usr/bin/env python3
"""Data-driven OpenAPI 3.1 generator for Flashduty public APIs.

Architecture:
  - Per-module data files at flashduty-docs/.api-review/modules/<scope>.json
  - This generator reads all module files, merges them into consolidated
    openapi.en.json and openapi.zh.json under api-reference/.
  - The pilot (on-call/template) is included inline as a baseline module
    and merged with any additional module files found on disk.

Run:
    python3 generate_openapi.py
    python3 generate_openapi.py --scope platform/preference   # regenerate one module
    python3 generate_openapi.py --validate                     # validate only, no write
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

DOCS_ROOT = Path(
    os.environ.get("FLASHDUTY_DOCS_ROOT", "")
    or Path(__file__).resolve().parents[6] / "flashduty-docs"
)
OUT_EN = DOCS_ROOT / "api-reference" / "openapi.en.json"
OUT_ZH = DOCS_ROOT / "api-reference" / "openapi.zh.json"
MODULES_DIR = DOCS_ROOT / ".api-review" / "modules"
REGISTRY_FILE = DOCS_ROOT / ".api-review" / "pgy_registry.json"

# Per-parent split files live next to the combined spec. We emit one file per
# (parent, language) pair so Mintlify can attach each parent group in docs.json
# to a smaller slice of the schema set and cut the spec payload on the API
# Reference pages. See split_spec_by_parent().
SPLIT_DIR = DOCS_ROOT / "api-reference"

# ---------------------------------------------------------------------------
# Error codes and envelope schemas — identical across all modules
# ---------------------------------------------------------------------------

ERROR_CODES = [
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
    "ServiceUnavailable",
]

# Per-code metadata from references/response-envelope.md. Used to render a
# markdown table in `ErrorCode.description` (guaranteed to render everywhere)
# and to populate `x-enumDescriptions` (Redoc-style extension that some
# renderers display as per-value hover text). Both are emitted so consumers
# get rich information regardless of which renderer they use.
ERROR_CODE_META = [
    ("OK", 200, "Reserved — not returned on real errors.",
     "保留值，正常错误响应不会返回。"),
    ("InvalidParameter", 400, "A required parameter is missing or failed validation.",
     "必填参数缺失或未通过校验。"),
    ("BadRequest", 400, "Generic 400 used when no more specific code fits.",
     "通用的 400 错误，通常是请求本身不合法。"),
    ("InvalidContentType", 400, "The `Content-Type` header is not `application/json`.",
     "请求头 `Content-Type` 不是 `application/json`。"),
    ("ResourceNotFound", 400, "The referenced resource does not exist. Note: returned as HTTP 400, not 404 (historical choice).",
     "目标资源不存在。注意 HTTP 状态码是 400 而非 404（历史设计）。"),
    ("NoLicense", 400, "The feature is license-gated and no active license was found.",
     "功能需要有效授权，但未找到可用的 license。"),
    ("ReferenceExist", 400, "Deletion blocked — other entities still reference this resource.",
     "该资源仍被其他实体引用，无法删除。"),
    ("Unauthorized", 401, "`app_key` is missing, invalid, or expired.",
     "`app_key` 缺失、无效或已过期。"),
    ("BalanceNotEnough", 402, "Billing-gated operation with insufficient account balance.",
     "账户余额不足，无法执行需要计费的操作。"),
    ("AccessDenied", 403, "Authenticated but lacking the permission required for this operation.",
     "身份认证通过，但 RBAC 权限不足以执行该操作。"),
    ("RouteNotFound", 404, "The request URL path is not a known route.",
     "请求的 URL 路径不是已知路由。"),
    ("MethodNotAllowed", 405, "The HTTP method is not allowed on this otherwise-known path.",
     "当前路径不接受所使用的 HTTP 方法。"),
    ("UndonedOrderExist", 409, "An outstanding billing order blocks this new one. Wait and retry.",
     "账户存在未完成的订单，请稍后重试。"),
    ("RequestLocked", 423, "Operation temporarily locked due to repeated failures.",
     "因连续失败被临时锁定。"),
    ("EntityTooLarge", 413, "Request body exceeds the configured max size.",
     "请求体超过允许的最大长度。"),
    ("RequestTooFrequently", 429, "Rate limit hit — API-global, per-account, or per-integration.",
     "命中限流（全局、账户级或集成级）。"),
    ("RequestVerifyRequired", 428, "Second-factor verification required but not supplied.",
     "操作需要二次验证码，但未提供。"),
    ("DangerousOperation", 428, "High-risk operation requires MFA verification.",
     "危险操作，需要进行 MFA 验证。"),
    ("InternalError", 500, "Unhandled server-side error. Include `request_id` in the bug report.",
     "服务端未预期错误。反馈问题请附上 `request_id`。"),
    ("ServiceUnavailable", 503, "A backend dependency is unavailable. Try again later.",
     "后端依赖不可用，请稍后重试。"),
]


def _error_code_table(lang: str) -> str:
    if lang == "en":
        rows = "\n".join(
            f"| `{code}` | {http} | {en_desc} |" for code, http, en_desc, _ in ERROR_CODE_META
        )
        return (
            "Flashduty error code enum. Every failed API response sets `error.code` to one of "
            "these stable wire strings. HTTP status is informational — the authoritative signal "
            "is the enum value.\n\n"
            "| Code | HTTP | Meaning |\n"
            "|---|---|---|\n"
            f"{rows}"
        )
    rows = "\n".join(
        f"| `{code}` | {http} | {zh_desc} |" for code, http, _, zh_desc in ERROR_CODE_META
    )
    return (
        "Flashduty 错误码枚举。每个失败响应的 `error.code` 都是下列稳定值之一，HTTP 状态码仅作参考。\n\n"
        "| 错误码 | HTTP | 含义 |\n"
        "|---|---|---|\n"
        f"{rows}"
    )


def _error_code_enum_descriptions(lang: str) -> dict:
    return {
        code: (en_desc if lang == "en" else zh_desc)
        for code, _http, en_desc, zh_desc in ERROR_CODE_META
    }


DEFAULT_RATE_LIMITS = {"per_second": 50, "per_minute": 1000}


def envelope_schemas(lang: str) -> dict:
    if lang == "en":
        return {
            "ErrorCode": {
                "type": "string",
                "description": _error_code_table("en"),
                "enum": ERROR_CODES,
                "x-enumDescriptions": _error_code_enum_descriptions("en"),
                "example": "InvalidParameter",
            },
            "DutyError": {
                "type": "object",
                "description": "Error payload inside the response envelope. Present only on non-2xx responses.",
                "properties": {
                    "code": {"$ref": "#/components/schemas/ErrorCode"},
                    "message": {
                        "type": "string",
                        "description": (
                            "Human-readable error message, localized by the caller's Accept-Language. "
                            "May contain field names, IDs, or other context from the failing request."
                        ),
                        "example": "The specified parameter template_id is not valid.",
                    },
                },
                "required": ["code", "message"],
            },
            "SuccessEnvelope": {
                "type": "object",
                "description": (
                    "Success response envelope. On every 2xx response, `request_id` identifies the call "
                    "(also mirrored in the `Flashcat-Request-Id` header) and `data` holds the "
                    "endpoint-specific payload. Failure responses use a different shape — see "
                    "`ErrorResponse`."
                ),
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Unique ID for this request. Mirrored in the Flashcat-Request-Id response header. Include it when reporting issues.",
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "data": {
                        "description": "Endpoint-specific payload. See each operation's 200 response schema."
                    },
                },
                "required": ["request_id", "data"],
            },
            "ErrorResponse": {
                "type": "object",
                "description": "Response envelope for errors. `error` is required; `data` is absent.",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "error": {"$ref": "#/components/schemas/DutyError"},
                },
                "required": ["request_id", "error"],
            },
            "EmptyObject": {
                "type": "object",
                "description": (
                    "An empty object. Returned as the `data` payload by operations whose success signal "
                    "is simply the absence of an error."
                ),
                "additionalProperties": False,
            },
            "EmptyResponse": {
                "type": "object",
                "description": "Generic empty response data.",
                "additionalProperties": False,
            },
            "EmptyRequest": {
                "type": "object",
                "description": "Generic empty request body.",
                "additionalProperties": False,
            },
        }
    else:
        return {
            "ErrorCode": {
                "type": "string",
                "description": _error_code_table("zh"),
                "enum": ERROR_CODES,
                "x-enumDescriptions": _error_code_enum_descriptions("zh"),
                "example": "InvalidParameter",
            },
            "DutyError": {
                "type": "object",
                "description": "响应结构中的错误 payload，仅在非 2xx 响应时出现。",
                "properties": {
                    "code": {"$ref": "#/components/schemas/ErrorCode"},
                    "message": {
                        "type": "string",
                        "description": (
                            "用户可读的错误描述，语言会跟随调用方的 Accept-Language。"
                            "可能包含字段名、ID 等请求上下文。"
                        ),
                        "example": "The specified parameter template_id is not valid.",
                    },
                },
                "required": ["code", "message"],
            },
            "SuccessEnvelope": {
                "type": "object",
                "description": (
                    "成功响应结构。2xx 响应中 `request_id` 标识本次调用（同时出现在 `Flashcat-Request-Id` 响应头中），"
                    "`data` 为接口业务 payload。失败响应使用不同结构，参见 `ErrorResponse`。"
                ),
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": (
                            "本次请求的唯一 ID，也会在 Flashcat-Request-Id 响应头中返回。反馈问题时请一并附上。"
                        ),
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "data": {
                        "description": "每个接口自己的业务 payload，详见各接口的 200 响应 schema。"
                    },
                },
                "required": ["request_id", "data"],
            },
            "ErrorResponse": {
                "type": "object",
                "description": "错误响应结构。`error` 必填，`data` 不存在。",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "error": {"$ref": "#/components/schemas/DutyError"},
                },
                "required": ["request_id", "error"],
            },
            "EmptyObject": {
                "type": "object",
                "description": "空对象。当操作的成功信号就是不报错时，作为 `data` 返回。",
                "additionalProperties": False,
            },
            "EmptyResponse": {
                "type": "object",
                "description": "通用空响应数据。",
                "additionalProperties": False,
            },
            "EmptyRequest": {
                "type": "object",
                "description": "通用空请求体。",
                "additionalProperties": False,
            },
        }


def shared_responses(lang: str) -> dict:
    rid = "01HK8XQE3Z7JM2NTFQ5YJ8P9R4"

    def _resp(desc: str, example_key: str, example: dict) -> dict:
        return {
            "description": desc,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        example_key: {"value": {"request_id": rid, "error": example}}
                    },
                }
            },
        }

    if lang == "en":
        return {
            "BadRequest": _resp(
                "Invalid request — usually a missing or malformed parameter.",
                "missingParameter",
                {"code": "InvalidParameter", "message": "The specified parameter is not valid."},
            ),
            "Unauthorized": _resp(
                "Missing or invalid app_key.",
                "missingAppKey",
                {"code": "Unauthorized", "message": "You are unauthorized."},
            ),
            "Forbidden": _resp(
                "The app_key is valid but lacks permission for this operation.",
                "noEditPermission",
                {"code": "AccessDenied", "message": "Access Denied."},
            ),
            "NotFound": _resp(
                "The referenced resource does not exist or has been deleted. Note: Flashduty historically returns HTTP 400 with code `ResourceNotFound` for missing domain entities; a true 404 is reserved for unknown routes.",
                "resourceMissing",
                {"code": "ResourceNotFound", "message": "The resource you request is not found"},
            ),
            "TooManyRequests": _resp(
                "Rate limit hit. Either the global API limit, a per-account limit, or a per-integration limit.",
                "rateLimited",
                {"code": "RequestTooFrequently", "message": "Request too frequently."},
            ),
            "ServerError": _resp(
                "Unexpected server-side error. Include the request_id when reporting.",
                "internal",
                {
                    "code": "InternalError",
                    "message": "We encountered an internal error, and it has been reported. Please try again later.",
                },
            ),
        }
    else:
        return {
            "BadRequest": _resp(
                "请求非法 — 通常是参数缺失或格式不正确。",
                "missingParameter",
                {"code": "InvalidParameter", "message": "The specified parameter is not valid."},
            ),
            "Unauthorized": _resp(
                "app_key 缺失或无效。",
                "missingAppKey",
                {"code": "Unauthorized", "message": "You are unauthorized."},
            ),
            "Forbidden": _resp(
                "app_key 有效但没有执行该操作的权限。",
                "noEditPermission",
                {"code": "AccessDenied", "message": "Access Denied."},
            ),
            "NotFound": _resp(
                "目标资源不存在或已被删除。注意：Flashduty 对业务实体的缺失通常返回 HTTP 400 + code=`ResourceNotFound`，真正的 404 只用于未知路由。",
                "resourceMissing",
                {"code": "ResourceNotFound", "message": "The resource you request is not found"},
            ),
            "TooManyRequests": _resp(
                "命中限流。可能是全局 API 限流、账户级限流或集成级限流。限流按账户聚合。",
                "rateLimited",
                {"code": "RequestTooFrequently", "message": "Request too frequently."},
            ),
            "ServerError": _resp(
                "服务端未预期错误。反馈问题时请携带 request_id。",
                "internal",
                {
                    "code": "InternalError",
                    "message": "We encountered an internal error, and it has been reported. Please try again later.",
                },
            ),
        }


# ---------------------------------------------------------------------------
# x-mint.content composition helpers
# ---------------------------------------------------------------------------


def rate_limits_cell(lang: str, op: dict | None = None) -> str:
    # Per-op override wins over the account-wide default.
    rl = op.get("rate_limit", DEFAULT_RATE_LIMITS) if op else DEFAULT_RATE_LIMITS
    per_s = rl["per_second"]
    per_m = rl["per_minute"]
    if lang == "en":
        noun_m = "request" if per_m == 1 else "requests"
        noun_s = "request" if per_s == 1 else "requests"
        return f"**{per_m:,} {noun_m}/minute**; **{per_s} {noun_s}/second** per account"
    return f"每个账户 **{per_m:,} 次/分钟**；**{per_s} 次/秒**"


def _read_permission(p: dict, lang: str, fallback_key: str) -> tuple[str, str]:
    """Return (name, scope) for a permission entry.

    Module files use one of two shapes:
      A) flat: {name_en, name_zh, scope, ...}
      B) nested: {en: {name, scope, ...}, zh: {name, scope, ...}}

    Both are honored so existing data files don't need migration.
    """
    nested = p.get(lang) if isinstance(p.get(lang), dict) else None
    if nested:
        name = nested.get("name", fallback_key)
        scope = nested.get("scope", "")
    else:
        name = p.get(f"name_{lang}", fallback_key)
        scope = p.get("scope", "")
    return name, scope


def permissions_cell(api_name: str, permissions_index: dict, permissions: dict, lang: str) -> str:
    """Build the permissions table cell for one operation."""
    keys = permissions_index.get(api_name)
    if not keys:
        return (
            "None — any valid `app_key` can call this operation"
            if lang == "en"
            else "无 —— 持有有效的 `app_key` 即可调用"
        )
    parts = []
    for key in keys:
        p = permissions.get(key, {})
        name, scope = _read_permission(p, lang, key)
        if lang == "en":
            parts.append(f"**{name}** (`{scope}`)")
        else:
            parts.append(f"**{name}**（`{scope}`）")
    sep = " or " if lang == "en" else " 或 "
    return sep.join(parts)


def restrictions_table(op: dict, permissions_index: dict, permissions: dict, lang: str) -> str:
    if lang == "en":
        return (
            "## Restrictions\n\n"
            "| Aspect | Value |\n"
            "| ------ | ----- |\n"
            f"| Rate limits | {rate_limits_cell('en', op)} |\n"
            f"| Permissions | {permissions_cell(op.get('permission_key', op.get('handler', '')), permissions_index, permissions, 'en')} |"
        )
    return (
        "## 限制说明\n\n"
        "| 项目 | 说明 |\n"
        "| ---- | ---- |\n"
        f"| 速率限制 | {rate_limits_cell('zh', op)} |\n"
        f"| 权限要求 | {permissions_cell(op.get('permission_key', op.get('handler', '')), permissions_index, permissions, 'zh')} |"
    )


def usage_section(op: dict, lang: str) -> str:
    bullets: list[str] = list(op.get(f"usage_{lang}", []))
    if op.get("audit"):
        bullets.append(
            "Every call is recorded in the account audit log. Don't put secrets in request fields."
            if lang == "en"
            else "每次调用都会记录到账户审计日志，请不要把敏感信息放在请求字段中。"
        )
    if op.get("dangerous"):
        bullets.append(
            "High-risk operation. Console JWT callers must pass a second-factor code; "
            "`app_key` callers bypass the MFA prompt but remain audited — treat the key as a secret."
            if lang == "en"
            else "本接口为高危操作。控制台 JWT 调用需二次验证码；`app_key` 调用跳过 MFA 但仍会被完整记录，请妥善保管 app_key。"
        )
    if op.get("deprecated"):
        alt = op.get(f"deprecated_alt_{lang}")
        if alt:
            bullets.append(alt)
    if not bullets:
        return ""
    header = "## Usage" if lang == "en" else "## 使用说明"
    lines = [header, ""]
    for b in bullets:
        lines.append(f"- {b}")
    return "\n".join(lines)


def compose_mint_content(op: dict, permissions_index: dict, permissions: dict, lang: str) -> str:
    blocks: list[str] = []
    if op.get("deprecated"):
        if lang == "en":
            blocks.append(
                "<Warning>\n  **Deprecated.** This operation remains available for "
                "backward compatibility; new integrations should not depend on it.\n</Warning>"
            )
        else:
            blocks.append(
                "<Warning>\n  **已废弃。** 出于向后兼容仍然保留，新接入请不要依赖它。\n</Warning>"
            )
    blocks.append(restrictions_table(op, permissions_index, permissions, lang))
    usage = usage_section(op, lang)
    if usage:
        blocks.append(usage)
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Operation builder
# ---------------------------------------------------------------------------

EXTRA_RESPONSE_CODE_MAP = {
    "Forbidden": "403",
    "NotFound": "404",
    "TooManyRequests": "429",
}


def build_operation(
    op: dict,
    lang: str,
    tag: str,
    permissions_index: dict,
    permissions: dict,
    example_request: dict,
    example_response_data: dict,
    module_meta: dict | None = None,
) -> tuple[str, dict]:
    success_desc = "Success" if lang == "en" else "成功"

    response_example = {
        "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
        "data": example_response_data,
    }

    responses: dict = {
        "200": {
            "description": success_desc,
            "content": {
                "application/json": {
                    "schema": {
                        "allOf": [
                            {"$ref": "#/components/schemas/SuccessEnvelope"},
                            {
                                "type": "object",
                                "properties": {
                                    "data": {
                                        "$ref": f"#/components/schemas/{op.get('response_ref', 'EmptyResponse')}"
                                    }
                                },
                            },
                        ]
                    },
                    "example": response_example,
                }
            },
        },
        "400": {"$ref": "#/components/responses/BadRequest"},
        "401": {"$ref": "#/components/responses/Unauthorized"},
    }
    for extra in op.get("extra_responses", []):
        code = EXTRA_RESPONSE_CODE_MAP.get(extra, extra)
        responses[code] = {"$ref": f"#/components/responses/{extra}"}
    # Always add 429 and 500
    if "429" not in responses:
        responses["429"] = {"$ref": "#/components/responses/TooManyRequests"}
    if "500" not in responses:
        responses["500"] = {"$ref": "#/components/responses/ServerError"}

    method = op.get("method", "post").lower()

    x_mint: dict = {
        "content": compose_mint_content(op, permissions_index, permissions, lang),
    }
    # Emit an explicit Latin URL slug so Mintlify doesn't derive paths from
    # CJK group labels. Both languages get their prefix (ZH at /zh/..., EN at /en/...).
    if module_meta:
        parent_slug = module_meta.get("parent_slug", "")
        sub_slug = module_meta.get("sub_slug", "")
        op_slug = _camel_to_kebab(op["slug"])
        segments = ["api-reference"]
        if parent_slug:
            segments.append(parent_slug)
        if sub_slug:
            segments.append(sub_slug)
        segments.append(op_slug)
        base_path = "/" + "/".join(segments)
        x_mint["href"] = f"/{lang}{base_path}"
        # Mintlify derives sidebar labels from the href slug by default, which
        # produces English labels for the ZH sidebar. Override via metadata.
        x_mint["metadata"] = {"sidebarTitle": op[lang]["summary"]}

    op_body: dict = {
        "operationId": op["slug"],
        "summary": op[lang]["summary"],
        "description": op[lang]["description"],
        "tags": [tag],
        "x-mint": x_mint,
        "responses": responses,
    }

    if method == "get":
        # GET operations use query parameters instead of requestBody.
        # op["parameters"] holds a list of OpenAPI parameter objects.
        params = op.get("parameters", [])
        if params:
            op_body["parameters"] = params
    else:
        op_body["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{op.get('request_ref', 'EmptyRequest')}"},
                    "example": example_request,
                }
            },
        }

    if op.get("deprecated"):
        op_body["deprecated"] = True

    # Build the path item; handle path parameters (e.g. {label_name})
    path_val = op["path"]
    return path_val, {method: op_body}


# ---------------------------------------------------------------------------
# Module loader — reads a .json data file and extracts operations
# ---------------------------------------------------------------------------


def load_module(module_file: Path) -> dict:
    """Load a per-module data file, rejecting any duplicate JSON keys.

    Python's default json loader silently collapses duplicate keys to the last
    one, which hides real authoring bugs — Mintlify's stricter YAML parser then
    fails at build time ("duplicated mapping key") and the stack trace points
    at the generated openapi.json rather than the offending source file.
    Failing loudly here keeps authoring errors visible at generation time.
    """
    def reject_dupes(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                raise ValueError(
                    f"{module_file.name}: duplicate JSON key {k!r}. "
                    "Each key must appear at most once per dict."
                )
            seen.add(k)
        return dict(pairs)

    with open(module_file) as f:
        return json.load(f, object_pairs_hook=reject_dupes)


# ---------------------------------------------------------------------------
# Pilot module (on-call/template) — hardcoded since it predates the file system
# ---------------------------------------------------------------------------

def get_pilot_module() -> dict:
    """Return the on-call/template module as a data dict matching the file format."""
    OBJECT_ID = {
        "type": "string",
        "pattern": "^[0-9a-fA-F]{24}$",
        "description": "MongoDB ObjectID (24-character hexadecimal string).",
        "example": "6605a1b2c3d4e5f6a7b8c9d0",
    }
    OBJECT_ID_ZH = {
        "type": "string",
        "pattern": "^[0-9a-fA-F]{24}$",
        "description": "MongoDB ObjectID（24 位 16 进制字符串）。",
        "example": "6605a1b2c3d4e5f6a7b8c9d0",
    }
    CHANNEL_FIELDS_EN = {k: {"type": "string", "description": desc} for k, desc in [
        ("email", "Email body template source (Go `html/template` syntax)."),
        ("sms", "SMS template source (Go `text/template` syntax)."),
        ("voice", "Voice call script template source."),
        ("dingtalk", "DingTalk robot message template source."),
        ("wecom", "WeCom robot message template source."),
        ("feishu", "Feishu robot message template source."),
        ("feishu_app", "Feishu app message template source."),
        ("dingtalk_app", "DingTalk app message template source."),
        ("wecom_app", "WeCom app message template source."),
        ("slack_app", "Slack app message template source."),
        ("teams_app", "Microsoft Teams app message template source."),
        ("telegram", "Telegram bot message template source."),
        ("slack", "Slack robot message template source."),
        ("zoom", "Zoom bot message template source."),
    ]}
    CHANNEL_FIELDS_ZH = {k: {"type": "string", "description": desc} for k, desc in [
        ("email", "邮件正文模板源（Go `html/template` 语法）。"),
        ("sms", "短信模板源（Go `text/template` 语法）。"),
        ("voice", "语音呼叫脚本模板源。"),
        ("dingtalk", "钉钉群机器人消息模板源。"),
        ("wecom", "企业微信群机器人消息模板源。"),
        ("feishu", "飞书群机器人消息模板源。"),
        ("feishu_app", "飞书应用消息模板源。"),
        ("dingtalk_app", "钉钉应用消息模板源。"),
        ("wecom_app", "企业微信应用消息模板源。"),
        ("slack_app", "Slack 应用消息模板源。"),
        ("teams_app", "Microsoft Teams 应用消息模板源。"),
        ("telegram", "Telegram 机器人消息模板源。"),
        ("slack", "Slack 机器人消息模板源。"),
        ("zoom", "Zoom 机器人消息模板源。"),
    ]}
    EX_TEMPLATE_ID = "6605a1b2c3d4e5f6a7b8c9d0"
    EX_ITEM = {
        "account_id": 10023, "team_id": 0, "template_id": EX_TEMPLATE_ID,
        "template_name": "Prod incident default",
        "description": "Default template for production incidents.",
        "email": "Incident {{ .IncidentName }} on {{ .Severity }}",
        "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}",
        "voice": "", "dingtalk": "", "wecom": "", "feishu": "",
        "feishu_app": "", "dingtalk_app": "", "wecom_app": "",
        "slack_app": "", "teams_app": "", "telegram": "", "slack": "", "zoom": "",
        "status": "enabled", "creator_id": 80011, "updated_by": 80011,
        "created_at": 1712700000, "updated_at": 1712702400,
    }
    CH_REQ = list(CHANNEL_FIELDS_EN.keys())
    ITEM_REQ = [
        "account_id", "team_id", "template_id", "template_name", "description",
        *CH_REQ, "status", "creator_id", "updated_by", "created_at", "updated_at",
    ]
    return {
        "scope": "on-call/template",
        "tag_en": "On-call/Templates",
        "tag_zh": "On-call/模板管理",
        "permissions_index": {
            "template:read:info": ["templates_read"],
            "template:read:list": ["templates_read", "templates_manage"],
            "template:read:preview": ["templates_read", "templates_manage"],
            "template:write:create": ["templates_manage"],
            "template:write:update": ["templates_manage"],
            "template:write:delete": ["templates_manage"],
            "template:write:enable": ["templates_manage"],
            "template:write:disable": ["templates_manage"],
        },
        "permissions": {
            "templates_read": {
                "name_zh": "模板查看", "name_en": "Templates Read",
                "desc_zh": "查看通知模板、故障模板等各类模板配置。",
                "desc_en": "View notification templates, incident templates and other template configurations.",
                "scope": "on-call",
            },
            "templates_manage": {
                "name_zh": "模板管理", "name_en": "Templates Manage",
                "desc_zh": "创建、编辑和删除各类模板，自定义模板内容和格式。",
                "desc_en": "Create, edit and delete templates, customize template content and formats.",
                "scope": "on-call",
            },
        },
        "operations": [
            {
                "slug": "template-read-info", "path": "/template/info",
                "permission_key": "template:read:info", "audit": False, "dangerous": False,
                "request_ref": "TemplateIDRequest", "response_ref": "TemplateItem",
                "en": {"summary": "Get template detail", "description": "Return a single notification template by ID."},
                "zh": {"summary": "查看模板详情", "description": "按 ID 返回单个通知模板。"},
                "usage_en": ["Pass `000000000000000000000001` as `template_id` to retrieve the built-in preset template for the caller's account locale."],
                "usage_zh": ["传入 `000000000000000000000001` 作为 `template_id` 可以获取当前账户语种下的系统预置模板。"],
                "example_request": {"template_id": EX_TEMPLATE_ID},
                "example_response_data": EX_ITEM,
                "example_request_zh": {"template_id": EX_TEMPLATE_ID},
                "example_response_data_zh": dict(EX_ITEM, template_name="生产环境默认模板"),
            },
            {
                "slug": "template-read-list", "path": "/template/list",
                "permission_key": "template:read:list", "audit": False, "dangerous": False,
                "request_ref": "TemplateListRequest", "response_ref": "TemplateListResponse",
                "en": {"summary": "List templates", "description": "Return a paginated list of notification templates."},
                "zh": {"summary": "查询模板列表", "description": "分页返回当前账户下的通知模板列表。"},
                "usage_en": [
                    "Pagination defaults to page 1 with 20 rows. The response's `has_next_page` tells you whether another page exists without needing a separate count request.",
                    "When `is_my_team` is `true`, `team_ids` is ignored.",
                ],
                "usage_zh": [
                    "默认返回第 1 页、每页 20 条。响应中的 `has_next_page` 可以直接告知是否还有下一页，无需额外计数请求。",
                    "当 `is_my_team=true` 时 `team_ids` 字段会被忽略。",
                ],
                "example_request": {"p": 1, "limit": 20, "orderby": "updated_at", "asc": False, "is_my_team": False},
                "example_response_data": {"total": 47, "has_next_page": True, "items": [EX_ITEM]},
                "example_request_zh": {"p": 1, "limit": 20, "orderby": "updated_at", "asc": False, "is_my_team": False},
                "example_response_data_zh": {"total": 47, "has_next_page": True, "items": [dict(EX_ITEM, template_name="生产环境默认模板")]},
            },
            {
                "slug": "template-write-create", "path": "/template/create",
                "permission_key": "template:write:create", "audit": True, "dangerous": False,
                "request_ref": "TemplateCreateRequest", "response_ref": "TemplateCreateResponse",
                "en": {"summary": "Create a template", "description": "Create a new notification template."},
                "zh": {"summary": "创建模板", "description": "创建一个新的通知模板。"},
                "usage_en": [
                    "`template_name` must be unique within the account; duplicates return `InvalidParameter`.",
                    "The server validates every non-empty channel template by rendering it against a mock incident — a syntactic error in any channel fails the whole request with `InvalidParameter`.",
                ],
                "usage_zh": [
                    "`template_name` 必须在账户内唯一，重名会返回 `InvalidParameter`。",
                    "服务端会对所有非空通道按 Mock 故障做一次渲染校验，任何通道的语法错误都会导致整个请求返回 `InvalidParameter`。",
                ],
                "example_request": {"team_id": 0, "template_name": "Prod incident default", "description": "Default template for production incidents.", "email": "Incident {{ .IncidentName }} on {{ .Severity }}", "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}"},
                "example_response_data": {"template_id": EX_TEMPLATE_ID, "template_name": "Prod incident default"},
                "example_request_zh": {"team_id": 0, "template_name": "生产环境默认模板", "description": "生产环境故障的默认模板。", "email": "Incident {{ .IncidentName }} on {{ .Severity }}", "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}"},
                "example_response_data_zh": {"template_id": EX_TEMPLATE_ID, "template_name": "生产环境默认模板"},
            },
            {
                "slug": "template-write-update", "path": "/template/update",
                "permission_key": "template:write:update", "audit": True, "dangerous": False,
                "request_ref": "TemplateUpdateRequest", "response_ref": "EmptyObject",
                "extra_responses": ["Forbidden"],
                "en": {"summary": "Update a template", "description": "Replace the content of every channel on an existing template."},
                "zh": {"summary": "更新模板", "description": "替换指定模板在所有通道上的内容。"},
                "usage_en": [
                    "Every channel field in the request overwrites the stored value — send an empty string to clear a channel.",
                    "The caller needs data-permission on the template's team; otherwise the response is `AccessDenied`.",
                ],
                "usage_zh": [
                    "请求中的每个通道字段会覆盖存储值——想清空某通道时，把该字段设置为空字符串即可。",
                    "调用者必须对目标模板所属团队拥有数据权限，否则返回 `AccessDenied`。",
                ],
                "example_request": {"template_id": EX_TEMPLATE_ID, "template_name": "Prod incident default", "description": "Updated description.", "email": "Incident {{ .IncidentName }} on {{ .Severity }}", "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}"},
                "example_response_data": {},
                "example_request_zh": {"template_id": EX_TEMPLATE_ID, "template_name": "生产环境默认模板", "description": "已更新的描述。", "email": "Incident {{ .IncidentName }} on {{ .Severity }}", "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}"},
                "example_response_data_zh": {},
            },
            {
                "slug": "template-write-delete", "path": "/template/delete",
                "permission_key": "template:write:delete", "audit": True, "dangerous": False,
                "request_ref": "TemplateIDRequest", "response_ref": "EmptyObject",
                "extra_responses": ["Forbidden"],
                "en": {"summary": "Delete a template", "description": "Soft-delete a template by ID."},
                "zh": {"summary": "删除模板", "description": "按 ID 软删除一个模板。"},
                "usage_en": [
                    "Fails with `400 ReferenceExist` if the template is still referenced by any channel, escalation rule, or notification subscription.",
                    "Deletion is soft — `deleted_at` is set. The record remains for audit, but the template stops appearing in listings.",
                ],
                "usage_zh": [
                    "若模板仍被任何协作空间、分派策略或通知订阅引用，会返回 `400 ReferenceExist`。",
                    "删除是软删除（`deleted_at` 被置值），记录仍保留用于审计，但模板不会再出现在列表中。",
                ],
                "example_request": {"template_id": EX_TEMPLATE_ID},
                "example_response_data": {},
                "example_request_zh": {"template_id": EX_TEMPLATE_ID},
                "example_response_data_zh": {},
            },
            {
                "slug": "template-write-enable", "path": "/template/enable",
                "permission_key": "template:write:enable", "audit": True, "dangerous": False,
                "request_ref": "TemplateIDRequest", "response_ref": "EmptyObject",
                "extra_responses": ["Forbidden"], "deprecated": True,
                "deprecated_alt_en": "New templates are enabled by default. Delete templates you no longer use instead of disabling them.",
                "deprecated_alt_zh": "新建模板默认启用。若不再使用某个模板，请直接删除，而不是禁用它。",
                "en": {"summary": "Enable a template", "description": "Flip a template from `disabled` to `enabled`."},
                "zh": {"summary": "启用模板", "description": "将模板从 `disabled` 切换为 `enabled`。"},
                "example_request": {"template_id": EX_TEMPLATE_ID},
                "example_response_data": {},
                "example_request_zh": {"template_id": EX_TEMPLATE_ID},
                "example_response_data_zh": {},
            },
            {
                "slug": "template-write-disable", "path": "/template/disable",
                "permission_key": "template:write:disable", "audit": True, "dangerous": False,
                "request_ref": "TemplateIDRequest", "response_ref": "EmptyObject",
                "extra_responses": ["Forbidden"], "deprecated": True,
                "deprecated_alt_en": "Delete templates you no longer use instead of disabling them.",
                "deprecated_alt_zh": "若不再使用某个模板，请直接删除，而不是禁用它。",
                "en": {"summary": "Disable a template", "description": "Flip a template from `enabled` to `disabled`."},
                "zh": {"summary": "禁用模板", "description": "将模板从 `enabled` 切换为 `disabled`。"},
                "example_request": {"template_id": EX_TEMPLATE_ID},
                "example_response_data": {},
                "example_request_zh": {"template_id": EX_TEMPLATE_ID},
                "example_response_data_zh": {},
            },
            {
                "slug": "template-read-preview", "path": "/template/preview",
                "permission_key": "template:read:preview", "audit": False, "dangerous": False,
                "request_ref": "TemplatePreviewRequest", "response_ref": "TemplatePreviewResponse",
                "en": {"summary": "Preview a template", "description": "Render a template source against mock or real incident data."},
                "zh": {"summary": "预览模板", "description": "使用 Mock 或指定的真实故障渲染模板源。"},
                "usage_en": [
                    "**Parse and render failures return `200` with `success: false`**, not a 4xx. The failure reason is in `message`.",
                    "Pass `incident_id` to render against a real incident from your account; leave it empty to use the built-in mock incident.",
                ],
                "usage_zh": [
                    "**模板解析与渲染失败会返回 `200` + `success: false`**，而不是 4xx。失败原因在 `message` 字段中。",
                    "传入 `incident_id` 可以按账户中的真实故障渲染；留空则使用内置 Mock 故障。",
                ],
                "example_request": {"content": "Incident {{ .IncidentName }} on {{ .Severity }}", "type": "email"},
                "example_response_data": {"success": True, "content": "Incident Prod DB down on P1"},
                "example_request_zh": {"content": "Incident {{ .IncidentName }} on {{ .Severity }}", "type": "email"},
                "example_response_data_zh": {"success": True, "content": "Incident 生产库宕机 on P1"},
            },
        ],
        "schemas_en": {
            "TemplateItem": {
                "type": "object",
                "description": "A notification template. Each channel field holds the template source string for that delivery channel; an empty string means 'no custom template for that channel'.",
                "required": ITEM_REQ,
                "properties": {
                    "account_id": {"type": "integer", "format": "int64", "description": "ID of the owning account."},
                    "team_id": {"type": "integer", "format": "int64", "description": "ID of the team this template is scoped to, or 0 for account-wide."},
                    "template_id": dict(OBJECT_ID, description="Template ID."),
                    "template_name": {"type": "string", "description": "Unique template name within the account."},
                    "description": {"type": "string", "description": "Free-form description."},
                    **CHANNEL_FIELDS_EN,
                    "status": {"type": "string", "description": "Template lifecycle status.", "enum": ["enabled", "disabled", "deleted"]},
                    "creator_id": {"type": "integer", "format": "int64", "description": "Member ID of the creator."},
                    "updated_by": {"type": "integer", "format": "int64", "description": "Member ID of the last editor."},
                    "deleted_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was soft-deleted. Absent (omitempty) when the template is live."},
                    "created_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was created."},
                    "updated_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was last updated."},
                },
            },
            "TemplateIDRequest": {
                "type": "object",
                "required": ["template_id"],
                "properties": {"template_id": dict(OBJECT_ID, description="Target template ID. Pass `000000000000000000000001` to address the built-in preset.")},
            },
            "TemplateListRequest": {
                "type": "object",
                "description": "Paginated list filters. Defaults: p=1, limit=20. Max limit=100.",
                "properties": {
                    "p": {"type": "integer", "description": "Page number, starting at 1.", "minimum": 1, "default": 1, "example": 1},
                    "limit": {"type": "integer", "description": "Page size. Capped at 100.", "minimum": 1, "maximum": 100, "default": 20, "example": 20},
                    "orderby": {"type": "string", "description": "Sort field.", "enum": ["created_at", "updated_at"]},
                    "asc": {"type": "boolean", "description": "Ascending sort order.", "default": False},
                    "is_my_team": {"type": "boolean", "description": "When true, only return templates scoped to teams the caller belongs to.", "default": False},
                    "team_ids": {"type": "array", "items": {"type": "integer", "format": "int64"}, "description": "Filter by specific team IDs."},
                    "creator_id": {"type": "integer", "format": "int64", "description": "Filter by creator member ID."},
                    "query": {"type": "string", "description": "Regex or substring match on template_name."},
                },
            },
            "TemplateListResponse": {
                "type": "object",
                "description": "Paginated template list.",
                "required": ["total", "has_next_page", "items"],
                "properties": {
                    "total": {"type": "integer", "format": "int64", "description": "Total number of templates matching the filter, across all pages.", "example": 47},
                    "has_next_page": {"type": "boolean", "description": "True if another page exists after the returned one.", "example": True},
                    "items": {"type": "array", "items": {"$ref": "#/components/schemas/TemplateItem"}},
                },
            },
            "TemplateCreateRequest": {
                "type": "object",
                "description": "Create a new notification template.",
                "required": ["template_name"],
                "properties": {
                    "team_id": {"type": "integer", "format": "int64", "description": "Team scope. 0 for account-wide.", "default": 0},
                    "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "Template name, unique per account. 1–39 characters.", "example": "Prod incident default"},
                    "description": {"type": "string", "maxLength": 500, "description": "Free-form description. Up to 500 characters."},
                    **CHANNEL_FIELDS_EN,
                },
            },
            "TemplateCreateResponse": {
                "type": "object",
                "required": ["template_id", "template_name"],
                "properties": {
                    "template_id": dict(OBJECT_ID, description="Newly created template ID."),
                    "template_name": {"type": "string", "description": "Template name echoed from the request.", "example": "Prod incident default"},
                },
            },
            "TemplateUpdateRequest": {
                "type": "object",
                "description": "Update an existing template.",
                "required": ["template_id", "template_name"],
                "properties": {
                    "template_id": dict(OBJECT_ID, description="Target template ID."),
                    "team_id": {"type": "integer", "format": "int64", "description": "Team scope. 0 for account-wide.", "default": 0},
                    "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "Template name. 1–39 characters."},
                    "description": {"type": "string", "maxLength": 500, "description": "Free-form description. Up to 500 characters."},
                    **CHANNEL_FIELDS_EN,
                },
            },
            "TemplatePreviewRequest": {
                "type": "object",
                "description": "Render a template against mock or real incident data.",
                "required": ["content", "type"],
                "properties": {
                    "content": {"type": "string", "description": "Template source to render."},
                    "type": {
                        "type": "string",
                        "description": "Channel type the template targets.",
                        "enum": ["email", "sms", "voice", "dingtalk", "wecom", "feishu", "zoom", "feishu_app", "dingtalk_app", "wecom_app", "slack_app", "teams_app", "telegram", "slack"],
                    },
                    "incident_id": dict(OBJECT_ID, description="Optional incident ID. When set, the template is rendered against that real incident."),
                },
            },
            "TemplatePreviewResponse": {
                "type": "object",
                "description": "Result of rendering a template. Parse/render failures return success:false — they are NOT returned as a 4xx.",
                "required": ["success"],
                "properties": {
                    "success": {"type": "boolean", "description": "Whether the template rendered cleanly.", "example": True},
                    "content": {"type": "string", "description": "Rendered output, present when success is true.", "example": "Incident Prod DB down on P1"},
                    "message": {"type": "string", "description": "Failure reason, present when success is false."},
                },
            },
        },
        "schemas_zh": {
            "TemplateItem": {
                "type": "object",
                "description": "一个通知模板。每个通道字段中存放该通道的模板源字符串；空字符串表示该通道没有自定义模板。",
                "required": ITEM_REQ,
                "properties": {
                    "account_id": {"type": "integer", "format": "int64", "description": "所属账户 ID。"},
                    "team_id": {"type": "integer", "format": "int64", "description": "所属团队 ID，0 表示账户全局共享。"},
                    "template_id": dict(OBJECT_ID_ZH, description="模板 ID。"),
                    "template_name": {"type": "string", "description": "模板名称，同一账户内唯一。"},
                    "description": {"type": "string", "description": "自定义描述。"},
                    **CHANNEL_FIELDS_ZH,
                    "status": {"type": "string", "description": "模板生命周期状态。", "enum": ["enabled", "disabled", "deleted"]},
                    "creator_id": {"type": "integer", "format": "int64", "description": "创建人成员 ID。"},
                    "updated_by": {"type": "integer", "format": "int64", "description": "最后修改人成员 ID。"},
                    "deleted_at": {"type": "integer", "format": "int64", "description": "软删除时间（Unix 秒）。模板未删除时字段缺省（omitempty）。"},
                    "created_at": {"type": "integer", "format": "int64", "description": "创建时间（Unix 秒）。"},
                    "updated_at": {"type": "integer", "format": "int64", "description": "最近更新时间（Unix 秒）。"},
                },
            },
            "TemplateIDRequest": {
                "type": "object",
                "required": ["template_id"],
                "properties": {"template_id": dict(OBJECT_ID_ZH, description="要操作的模板 ID。传入 `000000000000000000000001` 可访问系统预置模板。")},
            },
            "TemplateListRequest": {
                "type": "object",
                "description": "分页过滤条件。默认 p=1、limit=20，limit 上限为 100。",
                "properties": {
                    "p": {"type": "integer", "description": "页码，从 1 开始。", "minimum": 1, "default": 1, "example": 1},
                    "limit": {"type": "integer", "description": "分页大小，最大 100。", "minimum": 1, "maximum": 100, "default": 20, "example": 20},
                    "orderby": {"type": "string", "description": "排序字段。", "enum": ["created_at", "updated_at"]},
                    "asc": {"type": "boolean", "description": "升序排序。", "default": False},
                    "is_my_team": {"type": "boolean", "description": "为 true 时只返回当前成员所属团队范围内的模板。", "default": False},
                    "team_ids": {"type": "array", "items": {"type": "integer", "format": "int64"}, "description": "按团队 ID 列表过滤。"},
                    "creator_id": {"type": "integer", "format": "int64", "description": "按创建人成员 ID 过滤。"},
                    "query": {"type": "string", "description": "按模板名称做正则或子串匹配。"},
                },
            },
            "TemplateListResponse": {
                "type": "object",
                "description": "通知模板的分页列表。",
                "required": ["total", "has_next_page", "items"],
                "properties": {
                    "total": {"type": "integer", "format": "int64", "description": "符合过滤条件的模板总数。", "example": 47},
                    "has_next_page": {"type": "boolean", "description": "是否还有下一页。", "example": True},
                    "items": {"type": "array", "items": {"$ref": "#/components/schemas/TemplateItem"}},
                },
            },
            "TemplateCreateRequest": {
                "type": "object",
                "description": "创建通知模板。",
                "required": ["template_name"],
                "properties": {
                    "team_id": {"type": "integer", "format": "int64", "description": "团队归属。0 表示账户全局共享。", "default": 0},
                    "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "模板名称，同一账户内唯一，长度 1–39 个字符。", "example": "生产环境默认模板"},
                    "description": {"type": "string", "maxLength": 500, "description": "自定义描述。最多 500 字符。"},
                    **CHANNEL_FIELDS_ZH,
                },
            },
            "TemplateCreateResponse": {
                "type": "object",
                "required": ["template_id", "template_name"],
                "properties": {
                    "template_id": dict(OBJECT_ID_ZH, description="新创建的模板 ID。"),
                    "template_name": {"type": "string", "description": "从请求中回显的模板名称。", "example": "生产环境默认模板"},
                },
            },
            "TemplateUpdateRequest": {
                "type": "object",
                "description": "更新已存在的模板。",
                "required": ["template_id", "template_name"],
                "properties": {
                    "template_id": dict(OBJECT_ID_ZH, description="目标模板 ID。"),
                    "team_id": {"type": "integer", "format": "int64", "description": "团队归属。0 表示账户全局共享。", "default": 0},
                    "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "模板名称，长度 1–39 个字符。"},
                    "description": {"type": "string", "maxLength": 500, "description": "自定义描述。最多 500 字符。"},
                    **CHANNEL_FIELDS_ZH,
                },
            },
            "TemplatePreviewRequest": {
                "type": "object",
                "description": "使用 Mock 或真实故障数据渲染模板。",
                "required": ["content", "type"],
                "properties": {
                    "content": {"type": "string", "description": "待渲染的模板源。"},
                    "type": {
                        "type": "string",
                        "description": "模板对应的通道类型。",
                        "enum": ["email", "sms", "voice", "dingtalk", "wecom", "feishu", "zoom", "feishu_app", "dingtalk_app", "wecom_app", "slack_app", "teams_app", "telegram", "slack"],
                    },
                    "incident_id": dict(OBJECT_ID_ZH, description="可选的故障 ID。传入时按该真实故障渲染；否则使用内置 Mock 故障。"),
                },
            },
            "TemplatePreviewResponse": {
                "type": "object",
                "description": "模板渲染结果。注意：解析/渲染失败时以 success:false + message 的形式返回，而不是返回 4xx。",
                "required": ["success"],
                "properties": {
                    "success": {"type": "boolean", "description": "模板是否渲染成功。", "example": True},
                    "content": {"type": "string", "description": "渲染结果，success=true 时有值。", "example": "Incident 生产库宕机 on P1"},
                    "message": {"type": "string", "description": "失败原因，success=false 时有值。"},
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------


MAPPING_FILE = Path(__file__).parent.parent / "mapping.yaml"


def _slugify(label: str) -> str:
    """Turn a human label into a lowercase kebab URL slug.

    Mintlify derives doc URLs from group labels by default, which breaks for
    Chinese titles: CJK codepoints get preserved verbatim and parent-child
    segments can collapse without a separator. To make EN and ZH docs share
    the same URL, we emit an explicit `x-mint: { href }` override on every
    operation, derived from the Latin `tag_en` / `parent_en` labels.
    """
    import re
    s = label.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _camel_to_kebab(s: str) -> str:
    import re
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return s.lower()


def load_mapping() -> dict:
    """Load mapping.yaml — the single source of truth for tag names,
    icons, priorities, and parent grouping."""
    import yaml
    with open(MAPPING_FILE) as f:
        return yaml.safe_load(f)


def apply_mapping_overrides(modules: list[dict], mapping: dict) -> list[dict]:
    """Override tag_en / tag_zh on every module data file with the canonical
    values from mapping.yaml, prefixed with the parent label from
    module_parents. Module files that declare their own tag/parent are
    superseded here — mapping.yaml wins.

    Also attaches `_priority`, `_icon`, `_parent_en`, `_parent_zh` as
    underscored fields so downstream code (build_spec, build_docs_groups)
    can read them without having to re-load mapping.yaml.
    """
    mods_cfg = mapping.get("modules", {})
    parents = mapping.get("module_parents", {})

    out: list[dict] = []
    for m in modules:
        scope = m.get("scope")
        cfg = mods_cfg.get(scope)
        if cfg is None or cfg.get("hidden"):
            # Unknown scope — warn and keep with whatever the module file has.
            # Hidden scopes should not have been included in the first place,
            # but we tolerate them for forward-compat.
            print(f"  WARN: scope {scope!r} not in mapping.yaml (or hidden) — using module-file tags as-is")
            m.setdefault("_priority", 9999)
            m.setdefault("_icon", "file")
            out.append(m)
            continue

        parent_key = scope.split("/")[0] if "/" in scope else None
        parent_cfg = parents.get(parent_key, {}) if parent_key else {}

        tag_en = cfg["tag_en"]
        tag_zh = cfg["tag_zh"]

        parent_en = parent_cfg.get("en", "")
        parent_zh = parent_cfg.get("zh", "")

        # Construct the final slash-delimited tag string: "<parent>/<sub>".
        # For scopes without a parent (no slash), fall back to the bare tag.
        final_tag_en = f"{parent_en}/{tag_en}" if parent_en else tag_en
        final_tag_zh = f"{parent_zh}/{tag_zh}" if parent_zh else tag_zh

        # Override the module file's tag fields with the canonical values.
        m["tag_en"] = final_tag_en
        m["tag_zh"] = final_tag_zh
        m["_sub_tag_en"] = tag_en
        m["_sub_tag_zh"] = tag_zh
        m["_parent_en"] = parent_en
        m["_parent_zh"] = parent_zh
        m["_parent_key"] = parent_key
        m["_priority"] = cfg.get("priority", 9999)
        m["_icon"] = cfg.get("icon", "file")
        m["_subgroups"] = cfg.get("subgroups") or None
        m["_parent_slug"] = _slugify(parent_en) if parent_en else ""
        m["_sub_slug"] = _slugify(tag_en)
        out.append(m)

    # Sort by priority ascending — mapping.yaml controls the docs.json nav order.
    out.sort(key=lambda x: (x.get("_priority", 9999), x.get("scope", "")))
    return out


def load_registry_allowed() -> set[tuple[str, str]]:
    """Return the set of (METHOD, normalized_path) pairs with auth == 'all'.

    Normalization converts Go router params (`:id`) to OpenAPI braces (`{id}`)
    so registry entries match the paths stored in module data files.
    """
    import re
    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(
            f"Registry snapshot missing: {REGISTRY_FILE}. "
            f"Regenerate via parse_pgy_registry.py."
        )
    data = json.loads(REGISTRY_FILE.read_text())
    def norm(p: str) -> str:
        return re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", p)
    return {
        (r["method"].upper(), norm(r["path"]))
        for r in data
        if r.get("auth") == "all"
    }


def filter_modules_by_registry(modules: list[dict]) -> list[dict]:
    """Drop operations whose (method, path) isn't `auth == 'all'` in the registry.

    The registry (`pgy_registry.json`, a parsed snapshot of
    `fc-pgy/logic/api/api_test.go`) is the authoritative list of public APIs.
    Operations that fail this filter are either:
      - hallucinated paths the generator invented in an earlier round, or
      - paths whose registry auth was reclassified away from `all`.

    Modules left with zero operations are dropped from the output entirely.
    """
    allowed = load_registry_allowed()
    kept: list[dict] = []
    total_before = total_after = 0
    dropped_paths: list[str] = []
    for m in modules:
        ops = m.get("operations", [])
        total_before += len(ops)
        kept_ops = []
        for op in ops:
            method = op.get("method", "post").upper()
            path = op["path"]
            if (method, path) in allowed:
                kept_ops.append(op)
            else:
                dropped_paths.append(f"{method} {path}")
        total_after += len(kept_ops)
        if kept_ops:
            m2 = dict(m)
            m2["operations"] = kept_ops
            kept.append(m2)
    print(
        f"Registry filter: {total_before} ops -> {total_after} ops "
        f"({total_before - total_after} dropped, {len(modules) - len(kept)} empty modules removed)"
    )
    if dropped_paths:
        log = DOCS_ROOT / ".api-review" / "dropped-paths.log"
        log.write_text("\n".join(sorted(set(dropped_paths))) + "\n")
        print(f"  dropped-paths log: {log}")
    return kept


def collect_modules(scope_filter: str | None) -> list[dict]:
    """Load all module data files. Always include the pilot."""
    modules = [get_pilot_module()]
    if MODULES_DIR.exists():
        for f in sorted(MODULES_DIR.glob("*.json")):
            m = load_module(f)
            # skip pilot — already included
            if m.get("scope") == "on-call/template":
                continue
            if scope_filter and m.get("scope") != scope_filter and not m.get("scope", "").startswith(scope_filter):
                continue
            modules.append(m)
    return modules


def build_spec(modules: list[dict], lang: str) -> dict:
    info = (
        {
            "title": "Flashduty Open API",
            "description": (
                "Public HTTP API for the Flashduty incident management platform — incidents, "
                "notification templates, channels, schedules, monitors, RUM, and platform administration. "
                "Every operation is authenticated with an `app_key` query parameter issued from the "
                "Flashduty console under Account → APP Keys. Responses follow a uniform envelope: "
                "`{ request_id, data }` on success, `{ request_id, error }` on failure."
            ),
            "version": "1.0.0",
        }
        if lang == "en"
        else {
            "title": "Flashduty 开放 API",
            "description": (
                "Flashduty 事件管理平台的公开 HTTP API —— 覆盖故障、通知模板、协作空间、值班排班、监控、RUM、"
                "以及平台管理。每次调用都需在 query 中携带 `app_key`，该 key 在 Flashduty 控制台 "
                "账户 → APP Key 中签发。所有响应使用统一结构："
                "成功时为 `{ request_id, data }`，失败时为 `{ request_id, error }`。"
            ),
            "version": "1.0.0",
        }
    )
    sec_desc = (
        "App key issued from the Flashduty console under Account → APP Keys. Required on every "
        "public API call. Keep it secret — it grants the same access as the owning account."
        if lang == "en"
        else (
            "在 Flashduty 控制台 账户 → APP Key 中签发的 app_key。调用任何公开 API 时都必须携带。"
            "它等同于所属账户的身份凭证，请妥善保管。"
        )
    )

    schemas = envelope_schemas(lang)
    paths: dict = {}
    tags: list[dict] = []
    seen_tags: set = set()

    for mod in modules:
        tag = mod["tag_en"] if lang == "en" else mod["tag_zh"]
        if tag not in seen_tags:
            seen_tags.add(tag)
            tags.append({"name": tag, "description": mod.get(f"tag_desc_{lang}", "")})

        perms_index = mod.get("permissions_index", {})
        perms = mod.get("permissions", {})

        # Merge module schemas
        mod_schemas = mod.get(f"schemas_{lang}", {})
        schemas.update(mod_schemas)

        for op in mod.get("operations", []):
            ex_req_key = f"example_request_{lang}" if lang == "zh" and f"example_request_{lang}" in op else "example_request"
            ex_resp_key = f"example_response_data_{lang}" if lang == "zh" and f"example_response_data_{lang}" in op else "example_response_data"
            ex_req = op.get(ex_req_key, op.get("example_request", {}))
            ex_resp = op.get(ex_resp_key, op.get("example_response_data", {}))

            module_meta = {
                "parent_slug": mod.get("_parent_slug", ""),
                "sub_slug": mod.get("_sub_slug", ""),
            }
            path, item = build_operation(op, lang, tag, perms_index, perms, ex_req, ex_resp, module_meta)
            if path in paths:
                # Merge methods for the same path (e.g. GET+POST+DELETE on /oncall/schedules)
                paths[path].update(item)
            else:
                paths[path] = item

    # Prune orphan schemas — ones merged in from modules whose corresponding
    # operations got dropped by the registry filter (e.g. /template/preview is
    # auth=jwt so the op is filtered, but the pilot module still carries its
    # request/response schemas). Walk from paths + shared responses + always-
    # present envelope names to compute reachability, then drop everything
    # else. This keeps the spec honest and avoids surfacing dead schemas in
    # the generated Mintlify pages.
    responses = shared_responses(lang)
    seed: set = set(_ENVELOPE_ALWAYS)
    _collect_refs(paths, seed)
    _collect_refs(responses, seed)
    reachable = _reachable_schemas(seed, schemas)
    pruned = {name: schemas[name] for name in schemas if name in reachable}

    return {
        "openapi": "3.1.0",
        "info": info,
        "servers": [{"url": "https://api.flashcat.cloud", "description": "Flashduty Open API"}],
        "security": [{"AppKeyAuth": []}],
        "tags": tags,
        "paths": paths,
        "components": {
            "securitySchemes": {
                "AppKeyAuth": {
                    "type": "apiKey",
                    "in": "query",
                    "name": "app_key",
                    "description": sec_desc,
                }
            },
            "responses": responses,
            "schemas": pruned,
        },
    }


# Envelope schemas that must appear in every split file. Keep in sync with
# envelope_schemas() — these are what every operation's 200 and 4xx responses
# $ref into, so stripping them by reachability alone is not enough (the shared
# responses block references DutyError via ErrorResponse which we pull in via
# the allOf in build_operation).
_ENVELOPE_ALWAYS = (
    "ErrorCode",
    "DutyError",
    "SuccessEnvelope",
    "ErrorResponse",
    "EmptyObject",
    "EmptyRequest",
    "EmptyResponse",
)


def _collect_refs(node, acc: set) -> None:
    """Walk a spec subtree and collect every `#/components/schemas/<name>` ref."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/components/schemas/"):
                acc.add(v.rsplit("/", 1)[-1])
            else:
                _collect_refs(v, acc)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, acc)


def _reachable_schemas(seed: set, all_schemas: dict) -> set:
    """Given an initial set of schema names, walk their own $refs transitively."""
    seen = set(seed)
    frontier = list(seed)
    while frontier:
        name = frontier.pop()
        s = all_schemas.get(name)
        if not s:
            continue
        inner: set = set()
        _collect_refs(s, inner)
        for ref in inner:
            if ref not in seen:
                seen.add(ref)
                frontier.append(ref)
    return seen


def split_spec_by_parent(spec: dict, modules: list[dict]) -> dict[str, dict]:
    """Split the combined spec into per-parent specs.

    Produces `{parent_key: sub_spec}`. Each sub_spec contains only the paths
    whose operations belong to modules under that parent, plus the transitive
    closure of schemas those operations reference, plus the shared envelope
    schemas. The `tags`, `servers`, `info`, `components.responses`,
    `components.securitySchemes`, and `security` blocks are copied verbatim —
    they are tiny and shared, so duplicating them keeps each split file
    self-contained and directly usable by Mintlify.

    Modules without a parent (scopes with no slash) are skipped from the split
    — their operations stay only in the combined file. Every visible module in
    the current mapping has a parent, so this branch is defensive.
    """
    # Build a path-set per parent from the modules list. The operation's `path`
    # field in the module data file is the canonical key used by
    # build_operation() — it already matches spec['paths'] verbatim.
    paths_by_parent: dict[str, set] = {}
    for m in modules:
        pkey = m.get("_parent_key")
        if not pkey:
            continue
        bucket = paths_by_parent.setdefault(pkey, set())
        for op in m.get("operations", []):
            bucket.add(op["path"])

    all_schemas = spec["components"]["schemas"]
    results: dict[str, dict] = {}

    for pkey, paths in paths_by_parent.items():
        sub_paths: dict = {}
        seed: set = set()
        for p in paths:
            item = spec["paths"].get(p)
            if item is None:
                continue
            sub_paths[p] = item
            _collect_refs(item, seed)

        # Always include the envelope schemas — the allOf wrapper in every 200
        # response references SuccessEnvelope, and every error response
        # references ErrorResponse/DutyError/ErrorCode.
        seed.update(_ENVELOPE_ALWAYS)
        reachable = _reachable_schemas(seed, all_schemas)
        sub_schemas = {name: all_schemas[name] for name in sorted(reachable) if name in all_schemas}

        # Only carry tags that actually appear in this split's operations.
        used_tags: set = set()
        for item in sub_paths.values():
            for method, op in item.items():
                if isinstance(op, dict):
                    for t in op.get("tags", []):
                        used_tags.add(t)
        sub_tags = [t for t in spec.get("tags", []) if t.get("name") in used_tags]

        sub_spec = {
            "openapi": spec["openapi"],
            "info": copy.deepcopy(spec["info"]),
            "servers": copy.deepcopy(spec["servers"]),
            "security": copy.deepcopy(spec["security"]),
            "tags": sub_tags,
            "paths": sub_paths,
            "components": {
                "securitySchemes": copy.deepcopy(spec["components"]["securitySchemes"]),
                "responses": copy.deepcopy(spec["components"]["responses"]),
                "schemas": sub_schemas,
            },
        }
        results[pkey] = sub_spec

    return results


def validate_parity(en: dict, zh: dict) -> None:
    assert set(en["paths"].keys()) == set(zh["paths"].keys()), (
        f"path key sets differ:\n  EN only: {set(en['paths'])-set(zh['paths'])}\n  ZH only: {set(zh['paths'])-set(en['paths'])}"
    )
    assert set(en["components"]["schemas"].keys()) == set(zh["components"]["schemas"].keys()), (
        f"schema key sets differ"
    )
    for path, pi in en["paths"].items():
        for method, op in pi.items():
            if not isinstance(op, dict):
                continue
            zh_op = zh["paths"][path][method]
            assert op["operationId"] == zh_op["operationId"], f"operationId mismatch at {path}"
    for name, sch in en["components"]["schemas"].items():
        if "properties" in sch:
            en_props = set(sch["properties"].keys())
            zh_props = set(zh["components"]["schemas"][name].get("properties", {}).keys())
            assert en_props == zh_props, f"property mismatch in schema {name}: EN={en_props-zh_props} ZH={zh_props-en_props}"
    assert "ErrorCode" in en["components"]["schemas"]
    assert len(en["components"]["schemas"]["ErrorCode"]["enum"]) == 20


DOCS_JSON = DOCS_ROOT / "docs.json"


def build_docs_groups(modules: list[dict], mapping: dict, lang: str) -> list[dict]:
    """Rebuild the API Reference tab's `groups` array from mapping.yaml.

    Produces a strict 2-level structure:
      [{group: <parent>, icon: <parent-icon>, pages: [
          {group: <sub>, icon: <sub-icon>, pages: ["POST /foo/bar", ...]}
      ]}]

    Sub-modules with no parent (scopes without a slash) become top-level
    entries in the `groups` array.

    Modules are ordered by the priority value from mapping.yaml. Within each
    sub-module, operations are listed in the order they appear in the module
    data file (preserving intentional author ordering like info → list → CRUD).

    Any "sub-sub-groups" the earlier Sonnet subagents invented are discarded;
    mapping.yaml is the single source of navigation truth.
    """
    parents_cfg = mapping.get("module_parents", {})

    # Group modules by parent, preserving priority order.
    by_parent: dict[str | None, list[dict]] = {}
    for m in modules:
        # Skip the hardcoded pilot module when it has no parent_key metadata
        parent_key = m.get("_parent_key")
        by_parent.setdefault(parent_key, []).append(m)

    # Parents themselves also need a stable order. Use the smallest priority
    # of any child module under that parent — ensures developer-popular
    # parents come first even when sub-module priorities aren't globally
    # unique.
    parent_order: list[tuple[int, str | None]] = []
    for pkey, mods in by_parent.items():
        min_prio = min((mm.get("_priority", 9999) for mm in mods), default=9999)
        parent_order.append((min_prio, pkey))
    parent_order.sort()

    groups: list[dict] = []
    for _, parent_key in parent_order:
        parent_cfg = parents_cfg.get(parent_key, {}) if parent_key else None
        child_groups: list[dict] = []
        for m in by_parent[parent_key]:
            sub_label = m["_sub_tag_en"] if lang == "en" else m["_sub_tag_zh"]
            sub_icon = m.get("_icon", "file")

            ops = m.get("operations", [])
            if not ops:
                continue

            subgroups_cfg = m.get("_subgroups")
            if subgroups_cfg:
                # Mixed nav: ops matching a subgroup prefix go under that
                # subgroup; ops NOT matched stay at the module root as flat
                # pages alongside the subgroup folders. This lets callers put
                # CRUD at root and logically-related families in subgroups
                # without creating an artificial wrapper folder.
                buckets: list[list[str]] = [[] for _ in subgroups_cfg]
                root_pages: list[str] = []
                for op in ops:
                    method = op.get("method", "post").upper()
                    path = op["path"]
                    entry = f"{method} {path}"
                    chosen = None
                    for i, sg in enumerate(subgroups_cfg):
                        for prefix in sg.get("path_prefixes", []):
                            if path == prefix or path.startswith(prefix + "/"):
                                chosen = i
                                break
                        if chosen is not None:
                            break
                    if chosen is None:
                        root_pages.append(entry)
                    else:
                        buckets[chosen].append(entry)

                module_pages: list = list(root_pages)
                for i, sg in enumerate(subgroups_cfg):
                    if not buckets[i]:
                        continue
                    sg_label = sg.get(f"name_{lang}", sg.get("name_en", ""))
                    sg_icon = sg.get("icon", "file")
                    module_pages.append({
                        "group": sg_label,
                        "icon": sg_icon,
                        "pages": buckets[i],
                    })

                if not module_pages:
                    continue

                child_groups.append({
                    "group": sub_label,
                    "icon": sub_icon,
                    "pages": module_pages,
                })
            else:
                # Flat 2-level: one entry per operation.
                pages = [
                    f"{op.get('method', 'post').upper()} {op['path']}"
                    for op in ops
                ]
                child_groups.append({
                    "group": sub_label,
                    "icon": sub_icon,
                    "pages": pages,
                })

        if not child_groups:
            continue

        if parent_cfg is None:
            # Scope has no parent — promote its single child group to top level.
            groups.extend(child_groups)
        else:
            parent_label = parent_cfg.get("en" if lang == "en" else "zh", parent_key)
            parent_icon = parent_cfg.get("icon", "folder")
            # Point each parent group at its own split spec file. Mintlify's
            # navigation supports setting `openapi` at any level and children
            # inherit it — so only the parent needs the pointer. This keeps
            # each parent page's spec payload at 16%–35% of the combined size
            # instead of the full 1.5 MB.
            split_path = f"api-reference/{parent_key}.openapi.{lang}.json"
            groups.append({
                "group": parent_label,
                "icon": parent_icon,
                "openapi": split_path,
                "pages": child_groups,
            })

    return groups


def update_docs_json(modules: list[dict], mapping: dict) -> None:
    """Rewrite the API Reference tab in docs.json for both languages.

    IMPORTANT: we deliberately do NOT set an `openapi` field at the tab level.
    When a tab has `openapi` without covering every operation via explicit
    `pages`, Mintlify auto-generates an additional flat list of the remaining
    endpoints at the bottom of the sidebar — creating visible duplicates of
    operations that were already grouped. Each parent group below has its
    own `openapi` field pointing at its split spec file, and each sub-module
    group carries explicit `pages` entries, so Mintlify has a complete
    navigation picture without needing a tab-level fallback.
    """
    docs = json.loads(DOCS_JSON.read_text())

    for lang_entry in docs["navigation"]["languages"]:
        lang = lang_entry["language"]
        groups = build_docs_groups(modules, mapping, lang)

        api_tab = {
            "tab": "API 参考" if lang == "zh" else "API Reference",
            "icon": "terminal",
            "hidden": True,
            "groups": groups,
        }

        tabs = lang_entry.setdefault("tabs", [])
        replaced = False
        for i, t in enumerate(tabs):
            if t.get("tab") in ("API 参考", "API Reference") or (
                isinstance(t.get("openapi"), str) and t["openapi"].startswith("api-reference/openapi.")
            ):
                tabs[i] = api_tab
                replaced = True
                break
        if not replaced:
            tabs.append(api_tab)

    DOCS_JSON.write_text(json.dumps(docs, ensure_ascii=False, indent=2) + "\n")


def guard_no_path_drop(new_spec: dict, out_path, allow_drop: bool) -> None:
    """Abort if writing new_spec to out_path would remove any path present in
    the file already on disk. The module inputs under .api-review/ are
    gitignored and may be stale/incomplete, so the committed output spec is the
    source of truth — a rerun from incomplete inputs would silently drop
    endpoints (e.g. the hand-merged safari module). This makes that loud."""
    from pathlib import Path as _P
    p = _P(out_path)
    if not p.exists():
        return
    try:
        existing = json.loads(p.read_text())
    except Exception:
        return
    dropped = set(existing.get("paths", {})) - set(new_spec.get("paths", {}))
    if dropped and not allow_drop:
        raise SystemExit(
            f"\nERROR: regenerating {p.name} would DROP {len(dropped)} path(s) "
            f"present in the committed spec:\n"
            + "\n".join(f"  - {x}" for x in sorted(dropped))
            + "\n\nThe module inputs under .api-review/ are gitignored and may be "
            "stale/incomplete; the committed output spec is the source of truth. "
            "Rebuild the missing module inputs first, or pass --allow-drop to "
            "override (only if the removal is intentional).\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Flashduty OpenAPI specs")
    parser.add_argument("--scope", help="Only include modules matching this scope prefix")
    parser.add_argument("--validate", action="store_true", help="Validate only, don't write files")
    parser.add_argument("--skip-docs-json", action="store_true", help="Don't touch docs.json — only write openapi files")
    parser.add_argument("--allow-drop", action="store_true", help="permit removing paths present in the committed spec (use only when a removal is intentional)")
    args = parser.parse_args()

    mapping = load_mapping()
    modules = collect_modules(args.scope)
    modules = apply_mapping_overrides(modules, mapping)
    modules = filter_modules_by_registry(modules)
    print(f"Loaded {len(modules)} module(s) (sorted by priority):")
    for m in modules:
        print(f"  [{m.get('_priority', '?'):>4}] {m.get('scope', '?'):<30} {m.get('tag_zh', '?')}")

    en = build_spec(modules, "en")
    zh = build_spec(modules, "zh")

    validate_parity(en, zh)
    print(f"Parity OK: {len(en['paths'])} paths, {len(en['components']['schemas'])} schemas")

    if args.validate:
        print("--validate: no files written.")
        return

    guard_no_path_drop(en, OUT_EN, args.allow_drop)
    guard_no_path_drop(zh, OUT_ZH, args.allow_drop)
    OUT_EN.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n")
    OUT_ZH.write_text(json.dumps(zh, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {OUT_EN}: paths={len(en['paths'])} schemas={len(en['components']['schemas'])}")
    print(f"Wrote {OUT_ZH}: paths={len(zh['paths'])} schemas={len(zh['components']['schemas'])}")

    # Emit per-parent split spec files so Mintlify's docs.json can attach
    # smaller slices to each parent group — this is the performance
    # optimisation for the 558-endpoint API Reference tab.
    en_splits = split_spec_by_parent(en, modules)
    zh_splits = split_spec_by_parent(zh, modules)
    for pkey, sub in en_splits.items():
        out = SPLIT_DIR / f"{pkey}.openapi.en.json"
        guard_no_path_drop(sub, out, args.allow_drop)
        out.write_text(json.dumps(sub, ensure_ascii=False, indent=2) + "\n")
        print(f"Wrote {out}: paths={len(sub['paths'])} schemas={len(sub['components']['schemas'])}")
    for pkey, sub in zh_splits.items():
        out = SPLIT_DIR / f"{pkey}.openapi.zh.json"
        guard_no_path_drop(sub, out, args.allow_drop)
        out.write_text(json.dumps(sub, ensure_ascii=False, indent=2) + "\n")
        print(f"Wrote {out}: paths={len(sub['paths'])} schemas={len(sub['components']['schemas'])}")

    if not args.skip_docs_json:
        update_docs_json(modules, mapping)
        print(f"Rewrote API Reference tab in {DOCS_JSON}")


if __name__ == "__main__":
    main()
