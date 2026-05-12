#!/usr/bin/env python3
"""Build the consolidated Flashduty openapi.en.json and openapi.zh.json.

Pilot scope: the 8 On-call / Templates operations. All operations, envelope
schemas, error enum, domain schemas, shared responses, and rich examples
live in one file per language. No per-submodule split.

This is the concrete pilot implementation of the api-review skill's
consolidated generate phase. When the skill is generalized, the merge logic
here becomes the generate-phase's scope-merge step.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import os

_DOCS_ROOT = Path(
    os.environ.get("FLASHDUTY_DOCS_ROOT", "")
    or Path(__file__).resolve().parents[6] / "flashduty-docs"
)
OUT_DIR = _DOCS_ROOT / "api-reference"
OUT_EN = OUT_DIR / "openapi.en.json"
OUT_ZH = OUT_DIR / "openapi.zh.json"

# --------------------------------------------------------------------------
# Rate limits & Permissions — data embedded from fc-pgy sources.
#
# Rate limits: for the template APIs none of the rows in fc-pgy api_test.go
# declare account-level limits (only a global Qps=100 which we do NOT
# expose). Per the pilot rule we fall back to the unified defaults from
# mapping.yaml (50/s, 1000/m per app_key).
#
# Permissions: scraped from fc-pgy/logic/permission/permission_test.go.
# Two entries reference any template:*:* factor (see lines 882-917).
# --------------------------------------------------------------------------

DEFAULT_RATE_LIMITS = {
    "per_second": 50,
    "per_minute": 1000,
}

# api_name -> list of permission entries. Each entry lists which permissions
# grant the API. None → no permission in the table → callable by anyone with
# a valid app_key.
PERMISSION_INDEX: dict = {
    # Read permissions — permission 1504
    "template:read:info":    ["templates_read"],
    "template:read:list":    ["templates_read", "templates_manage"],  # 1504 + 1505 dependency list
    "template:read:preview": ["templates_read", "templates_manage"],
    # Write permissions — permission 1505
    "template:write:create":  ["templates_manage"],
    "template:write:update":  ["templates_manage"],
    "template:write:delete":  ["templates_manage"],
    "template:write:enable":  ["templates_manage"],
    "template:write:disable": ["templates_manage"],
}

# Permission definitions, keyed by the synthetic id used in PERMISSION_INDEX.
# Sourced from fc-pgy/logic/permission/permission_test.go:882-917.
PERMISSIONS: dict = {
    "templates_read": {
        "name_zh": "模板查看",
        "name_en": "Templates Read",
        "desc_zh": "查看通知模板、故障模板等各类模板配置。",
        "desc_en": "View notification templates, incident templates and other template configurations.",
        "scope": "on-call",
    },
    "templates_manage": {
        "name_zh": "模板管理",
        "name_en": "Templates Manage",
        "desc_zh": "创建、编辑和删除各类模板，自定义模板内容和格式。必须对目标模板所在团队拥有数据权限。",
        "desc_en": "Create, edit and delete templates, customize template content and formats. Requires data permission on the target template's team.",
        "scope": "on-call",
    },
}


def rate_limits_cell(lang: str) -> str:
    """One-line rate-limit summary for the Restrictions table."""
    per_s = DEFAULT_RATE_LIMITS["per_second"]
    per_m = DEFAULT_RATE_LIMITS["per_minute"]
    if lang == "en":
        return f"**{per_m:,} requests/minute**; **{per_s} requests/second** per `app_key`"
    return f"每个 `app_key` **{per_m:,} 次/分钟**；**{per_s} 次/秒**"


def permissions_cell(api_name: str, lang: str) -> str:
    """One-cell permission summary for the Restrictions table."""
    keys = PERMISSION_INDEX.get(api_name)
    if not keys:
        return (
            "None — any valid `app_key` can call this operation"
            if lang == "en"
            else "无 —— 持有有效的 `app_key` 即可调用"
        )
    parts = []
    for key in keys:
        p = PERMISSIONS[key]
        if lang == "en":
            parts.append(f"**{p['name_en']}** (`{p['scope']}`)")
        else:
            parts.append(f"**{p['name_zh']}**（`{p['scope']}`）")
    sep = " or " if lang == "en" else " 或 "
    suffix = (
        ". Missing the permission → `403 AccessDenied`."
        if lang == "en"
        else "。缺少权限将返回 `403 AccessDenied`。"
    )
    return sep.join(parts) + suffix


def restrictions_table(op: dict, lang: str) -> str:
    """A compact 2-row table: rate limits + permissions."""
    if lang == "en":
        return (
            "## Restrictions\n\n"
            "| Aspect | Value |\n"
            "| ------ | ----- |\n"
            f"| Rate limits | {rate_limits_cell('en')} |\n"
            f"| Permissions | {permissions_cell(op['permission_key'], 'en')} |"
        )
    return (
        "## 限制说明\n\n"
        "| 项目 | 说明 |\n"
        "| ---- | ---- |\n"
        f"| 速率限制 | {rate_limits_cell('zh')} |\n"
        f"| 权限要求 | {permissions_cell(op['permission_key'], 'zh')} |"
    )


def usage_section(op: dict, lang: str) -> str:
    """A bulleted list of non-obvious behaviors. Only rendered when there's
    at least one bullet — no empty headers."""
    bullets: list[str] = list(op.get(f"usage_{lang}", []))

    # Auto-append flag-driven bullets so every audited / dangerous / deprecated
    # operation carries the same boilerplate without per-op duplication.
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
        # The Warning admonition already flags deprecation visually; here we
        # add one line with the recommended alternative if the op supplies it.
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


def compose_mint_content(op: dict, lang: str) -> str:
    """Build the x-mint.content MDX block for an operation.

    Layout (compact, to keep Authorization above the fold):
      1. Optional <Warning> admonition for deprecated operations.
      2. ## Restrictions — a 2-row table (rate limits, permissions).
      3. ## Usage — bulleted list of non-obvious behaviors. Skipped entirely
         when no bullets apply.
    """
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

    blocks.append(restrictions_table(op, lang))

    usage = usage_section(op, lang)
    if usage:
        blocks.append(usage)

    return "\n\n".join(blocks)

# --------------------------------------------------------------------------
# Error codes — EXACT wire values from go-pkg/srv/error.go:11-32
# --------------------------------------------------------------------------

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

# --------------------------------------------------------------------------
# Envelope schemas — identical structure across languages, only descriptions
# differ. Built separately per language so the human text is authored once.
# --------------------------------------------------------------------------


def envelope_schemas(lang: str) -> dict:
    if lang == "en":
        return {
            "ErrorCode": {
                "type": "string",
                "description": "Flashduty error code enum. Every failed API response sets `error.code` to one of these values. Stable wire strings — not localized messages, not numeric status. HTTP status is informational; see the error code table in the developer docs for the status mapped to each code.",
                "enum": ERROR_CODES,
                "example": "InvalidParameter",
            },
            "DutyError": {
                "type": "object",
                "description": "Error payload inside the response envelope. Present only on non-2xx responses.",
                "properties": {
                    "code": {"$ref": "#/components/schemas/ErrorCode"},
                    "message": {
                        "type": "string",
                        "description": "Human-readable error message, localized by the caller's Accept-Language. May contain field names, IDs, or other context from the failing request.",
                        "example": "The specified parameter template_id is not valid.",
                    },
                },
                "required": ["code", "message"],
            },
            "ResponseEnvelope": {
                "type": "object",
                "description": "Standard response envelope used by every Flashduty public API. On success `data` contains the endpoint-specific payload and `error` is absent. On failure `error` is present and `data` is absent. `request_id` is always present and is also mirrored in the `X-Request-Id` response header.",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Unique ID for this request. Mirrored in the X-Request-Id header. Include it when reporting issues.",
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "error": {"$ref": "#/components/schemas/DutyError"},
                    "data": {
                        "description": "Endpoint-specific payload. See each operation's 200 response schema."
                    },
                },
                "required": ["request_id"],
            },
            "ErrorResponse": {
                "type": "object",
                "description": "Response envelope for errors. `error` is required; `data` is absent.",
                "properties": {
                    "request_id": {"type": "string", "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4"},
                    "error": {"$ref": "#/components/schemas/DutyError"},
                },
                "required": ["request_id", "error"],
            },
            "EmptyObject": {
                "type": "object",
                "description": "An empty object. Returned as the `data` payload by operations whose success signal is simply the absence of an error.",
                "additionalProperties": False,
            },
        }
    else:
        return {
            "ErrorCode": {
                "type": "string",
                "description": "Flashduty 错误码枚举。每个失败响应的 `error.code` 都是下列值之一。枚举值是稳定的英文字符串，不会被本地化；HTTP 状态码仅作参考，具体映射可参考开发者文档中的错误码表。",
                "enum": ERROR_CODES,
                "example": "InvalidParameter",
            },
            "DutyError": {
                "type": "object",
                "description": "响应结构中的错误 payload，仅在非 2xx 响应时出现。",
                "properties": {
                    "code": {"$ref": "#/components/schemas/ErrorCode"},
                    "message": {
                        "type": "string",
                        "description": "用户可读的错误描述，语言会跟随调用方的 Accept-Language。可能包含字段名、ID 等请求上下文。",
                        "example": "The specified parameter template_id is not valid.",
                    },
                },
                "required": ["code", "message"],
            },
            "ResponseEnvelope": {
                "type": "object",
                "description": "Flashduty 公开 API 统一响应结构。成功时 `data` 包含具体 payload，`error` 不存在；失败时 `error` 包含错误详情，`data` 不存在。`request_id` 总是存在，且会同时出现在 `X-Request-Id` 响应头中。",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "本次请求的唯一 ID，也会在 X-Request-Id 响应头中返回。反馈问题时请一并附上。",
                        "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
                    },
                    "error": {"$ref": "#/components/schemas/DutyError"},
                    "data": {"description": "每个接口自己的业务 payload，详见各接口的 200 响应 schema。"},
                },
                "required": ["request_id"],
            },
            "ErrorResponse": {
                "type": "object",
                "description": "错误响应结构。`error` 必填，`data` 不存在。",
                "properties": {
                    "request_id": {"type": "string", "example": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4"},
                    "error": {"$ref": "#/components/schemas/DutyError"},
                },
                "required": ["request_id", "error"],
            },
            "EmptyObject": {
                "type": "object",
                "description": "空对象。当操作的成功信号就是不报错时，作为 `data` 返回。",
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
                    "examples": {example_key: {"value": {"request_id": rid, "error": example}}},
                }
            },
        }

    if lang == "en":
        return {
            "BadRequest": _resp(
                "Invalid request — usually a missing or malformed parameter.",
                "missingParameter",
                {
                    "code": "InvalidParameter",
                    "message": "The specified parameter template_id is not valid.",
},
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
                {
                    "code": "InvalidParameter",
                    "message": "The specified parameter template_id is not valid.",
},
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
                "命中限流。可能是全局 API 限流，也可能是账户级或集成级限流。",
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


# --------------------------------------------------------------------------
# Reusable primitives
# --------------------------------------------------------------------------

OBJECT_ID_EN = {
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

CHANNEL_FIELDS_EN = {
    "email": {"type": "string", "description": "Email body template source (Go `html/template` syntax)."},
    "sms": {"type": "string", "description": "SMS template source (Go `text/template` syntax)."},
    "voice": {"type": "string", "description": "Voice call script template source."},
    "dingtalk": {"type": "string", "description": "DingTalk robot message template source."},
    "wecom": {"type": "string", "description": "WeCom robot message template source."},
    "feishu": {"type": "string", "description": "Feishu robot message template source."},
    "feishu_app": {"type": "string", "description": "Feishu app message template source."},
    "dingtalk_app": {"type": "string", "description": "DingTalk app message template source."},
    "wecom_app": {"type": "string", "description": "WeCom app message template source."},
    "slack_app": {"type": "string", "description": "Slack app message template source."},
    "teams_app": {"type": "string", "description": "Microsoft Teams app message template source."},
    "telegram": {"type": "string", "description": "Telegram bot message template source."},
    "slack": {"type": "string", "description": "Slack robot message template source."},
    "zoom": {"type": "string", "description": "Zoom bot message template source."},
}

CHANNEL_FIELDS_ZH = {
    "email": {"type": "string", "description": "邮件正文模板源（Go `html/template` 语法）。"},
    "sms": {"type": "string", "description": "短信模板源（Go `text/template` 语法）。"},
    "voice": {"type": "string", "description": "语音呼叫脚本模板源。"},
    "dingtalk": {"type": "string", "description": "钉钉群机器人消息模板源。"},
    "wecom": {"type": "string", "description": "企业微信群机器人消息模板源。"},
    "feishu": {"type": "string", "description": "飞书群机器人消息模板源。"},
    "feishu_app": {"type": "string", "description": "飞书应用消息模板源。"},
    "dingtalk_app": {"type": "string", "description": "钉钉应用消息模板源。"},
    "wecom_app": {"type": "string", "description": "企业微信应用消息模板源。"},
    "slack_app": {"type": "string", "description": "Slack 应用消息模板源。"},
    "teams_app": {"type": "string", "description": "Microsoft Teams 应用消息模板源。"},
    "telegram": {"type": "string", "description": "Telegram 机器人消息模板源。"},
    "slack": {"type": "string", "description": "Slack 机器人消息模板源。"},
    "zoom": {"type": "string", "description": "Zoom 机器人消息模板源。"},
}

EXAMPLE_TEMPLATE_ID = "6605a1b2c3d4e5f6a7b8c9d0"
EXAMPLE_PRESET_TEMPLATE_ID = "000000000000000000000001"
EXAMPLE_TEMPLATE_ITEM = {
    "account_id": 10023,
    "team_id": 0,
    "template_id": EXAMPLE_TEMPLATE_ID,
    "template_name": "Prod incident default",
    "description": "Default template for production incidents.",
    "email": "Incident {{ .IncidentName }} on {{ .Severity }}",
    "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}",
    "voice": "",
    "dingtalk": "",
    "wecom": "",
    "feishu": "",
    "feishu_app": "",
    "dingtalk_app": "",
    "wecom_app": "",
    "slack_app": "",
    "teams_app": "",
    "telegram": "",
    "slack": "",
    "zoom": "",
    "status": "enabled",
    "creator_id": 80011,
    "updated_by": 80011,
    "deleted_at": 0,
    "created_at": 1712700000,
    "updated_at": 1712702400,
}

# --------------------------------------------------------------------------
# Template domain schemas
# --------------------------------------------------------------------------


def template_schemas(lang: str) -> dict:
    oid = OBJECT_ID_EN if lang == "en" else OBJECT_ID_ZH
    ch = CHANNEL_FIELDS_EN if lang == "en" else CHANNEL_FIELDS_ZH

    if lang == "en":
        template_item = {
            "type": "object",
            "description": "A notification template. Each channel field holds the template source string for that delivery channel; an empty string means 'no custom template for that channel'. Only `deleted_at` is optional — the other fields are always present in a successful response.",
            "required": [
                "account_id", "team_id", "template_id", "template_name", "description",
                "email", "sms", "voice", "dingtalk", "wecom", "feishu",
                "feishu_app", "dingtalk_app", "wecom_app", "slack_app", "teams_app",
                "telegram", "slack", "zoom",
                "status", "creator_id", "updated_by", "created_at", "updated_at",
            ],
            "properties": {
                "account_id": {"type": "integer", "format": "int64", "description": "ID of the owning account."},
                "team_id": {"type": "integer", "format": "int64", "description": "ID of the team this template is scoped to, or 0 for account-wide."},
                "template_id": dict(oid, description="Template ID."),
                "template_name": {"type": "string", "description": "Unique template name within the account."},
                "description": {"type": "string", "description": "Free-form description."},
                **ch,
                "status": {
                    "type": "string",
                    "description": "Template lifecycle status.",
                    "enum": ["enabled", "disabled", "deleted"],
                },
                "creator_id": {"type": "integer", "format": "int64", "description": "Member ID of the creator."},
                "updated_by": {"type": "integer", "format": "int64", "description": "Member ID of the last editor."},
                "deleted_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was soft-deleted, or 0 if live."},
                "created_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was created."},
                "updated_at": {"type": "integer", "format": "int64", "description": "Unix epoch seconds the template was last updated."},
            },
        }
    else:
        template_item = {
            "type": "object",
            "description": "一个通知模板。每个通道字段中存放该通道的模板源字符串；空字符串表示该通道没有自定义模板。除 `deleted_at` 外，其它字段在成功响应中始终存在。",
            "required": [
                "account_id", "team_id", "template_id", "template_name", "description",
                "email", "sms", "voice", "dingtalk", "wecom", "feishu",
                "feishu_app", "dingtalk_app", "wecom_app", "slack_app", "teams_app",
                "telegram", "slack", "zoom",
                "status", "creator_id", "updated_by", "created_at", "updated_at",
            ],
            "properties": {
                "account_id": {"type": "integer", "format": "int64", "description": "所属账户 ID。"},
                "team_id": {"type": "integer", "format": "int64", "description": "所属团队 ID，0 表示账户全局共享。"},
                "template_id": dict(oid, description="模板 ID（MongoDB ObjectID，24 位 16 进制）。"),
                "template_name": {"type": "string", "description": "模板名称，同一账户内唯一。"},
                "description": {"type": "string", "description": "自定义描述。"},
                **ch,
                "status": {
                    "type": "string",
                    "description": "模板生命周期状态。",
                    "enum": ["enabled", "disabled", "deleted"],
                },
                "creator_id": {"type": "integer", "format": "int64", "description": "创建人成员 ID。"},
                "updated_by": {"type": "integer", "format": "int64", "description": "最后修改人成员 ID。"},
                "deleted_at": {"type": "integer", "format": "int64", "description": "软删除时间（Unix 秒）；0 表示未删除。"},
                "created_at": {"type": "integer", "format": "int64", "description": "创建时间（Unix 秒）。"},
                "updated_at": {"type": "integer", "format": "int64", "description": "最近更新时间（Unix 秒）。"},
            },
        }

    template_id_req = {
        "type": "object",
        "properties": {
            "template_id": dict(
                oid,
                description=(
                    "Target template ID. Pass `000000000000000000000001` to address the built-in preset."
                    if lang == "en"
                    else "要操作的模板 ID。传入 `000000000000000000000001` 可访问系统预置模板。"
                ),
            )
        },
        "required": ["template_id"],
    }

    if lang == "en":
        template_list_req = {
            "type": "object",
            "description": "Paginated list filters. Defaults: p=1, limit=20. Max limit=100.",
            "properties": {
                "p": {"type": "integer", "description": "Page number, starting at 1.", "minimum": 1, "default": 1, "example": 1},
                "limit": {"type": "integer", "description": "Page size. Capped at 100.", "minimum": 1, "maximum": 100, "default": 20, "example": 20},
                "orderby": {"type": "string", "description": "Sort field. Leave unset to use the server default (updated_at desc).", "enum": ["created_at", "updated_at"]},
                "asc": {"type": "boolean", "description": "Ascending sort order.", "default": False},
                "is_my_team": {"type": "boolean", "description": "When true, only return templates scoped to teams the caller belongs to. Mutually exclusive with `team_ids`.", "default": False},
                "team_ids": {"type": "array", "items": {"type": "integer", "format": "int64"}, "description": "Filter by specific team IDs. Ignored when is_my_team is true."},
                "creator_id": {"type": "integer", "format": "int64", "description": "Filter by creator member ID."},
                "query": {"type": "string", "description": "Regex or substring match on template_name. Invalid regex is auto-escaped."},
            },
        }
        template_list_resp = {
            "type": "object",
            "description": "Paginated template list.",
            "properties": {
                "total": {"type": "integer", "format": "int64", "description": "Total number of templates matching the filter, across all pages.", "example": 47},
                "has_next_page": {"type": "boolean", "description": "True if another page exists after the returned one.", "example": True},
                "items": {"type": "array", "items": {"$ref": "#/components/schemas/TemplateItem"}},
            },
            "required": ["total", "has_next_page", "items"],
        }
        template_create_req = {
            "type": "object",
            "description": "Create a new notification template. `template_name` is required and must be unique within the account. Leave a channel field empty to skip configuring that channel.",
            "properties": {
                "team_id": {"type": "integer", "format": "int64", "description": "Team scope. 0 for account-wide.", "default": 0},
                "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "Template name, unique per account. 1–39 characters.", "example": "Prod incident default"},
                "description": {"type": "string", "maxLength": 500, "description": "Free-form description. Up to 500 characters."},
                **ch,
            },
            "required": ["template_name"],
        }
        template_create_resp = {
            "type": "object",
            "properties": {
                "template_id": dict(oid, description="Newly created template ID."),
                "template_name": {"type": "string", "description": "Template name echoed from the request.", "example": "Prod incident default"},
            },
            "required": ["template_id", "template_name"],
        }
        template_update_req = {
            "type": "object",
            "description": "Update an existing template. `template_id` and `template_name` are required; every channel field overwrites the stored value on this request (omit a field to clear the stored content for that channel).",
            "properties": {
                "template_id": dict(oid, description="Target template ID."),
                "team_id": {"type": "integer", "format": "int64", "description": "Team scope. 0 for account-wide.", "default": 0},
                "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "Template name. 1–39 characters."},
                "description": {"type": "string", "maxLength": 500, "description": "Free-form description. Up to 500 characters."},
                **ch,
            },
            "required": ["template_id", "template_name"],
        }
        template_preview_req = {
            "type": "object",
            "description": "Render a template against mock or real incident data. Use this to validate a template's syntax before saving it.",
            "properties": {
                "content": {"type": "string", "description": "Template source to render."},
                "type": {"type": "string", "description": "Channel type the template targets. Valid values: `email`, `sms`, `voice`, `dingtalk`, `wecom`, `feishu`, `feishu_app`, `dingtalk_app`, `wecom_app`, `slack_app`, `teams_app`, `telegram`, `slack`, `zoom`."},
                "incident_id": dict(oid, description="Optional incident ID. When set, the template is rendered against that real incident; otherwise a built-in mock incident is used."),
            },
            "required": ["content", "type"],
        }
        template_preview_resp = {
            "type": "object",
            "description": "Result of rendering a template. Parse/render failures return success:false with the reason in message — they are NOT returned as a 4xx.",
            "properties": {
                "success": {"type": "boolean", "description": "Whether the template rendered cleanly.", "example": True},
                "content": {"type": "string", "description": "Rendered output, present when success is true.", "example": "Incident Prod DB down on P1"},
                "message": {"type": "string", "description": "Failure reason, present when success is false."},
            },
            "required": ["success"],
        }
    else:
        template_list_req = {
            "type": "object",
            "description": "分页过滤条件。默认 p=1、limit=20，limit 上限为 100。",
            "properties": {
                "p": {"type": "integer", "description": "页码，从 1 开始。", "minimum": 1, "default": 1, "example": 1},
                "limit": {"type": "integer", "description": "分页大小，最大 100。", "minimum": 1, "maximum": 100, "default": 20, "example": 20},
                "orderby": {"type": "string", "description": "排序字段。留空时使用服务端默认（按 updated_at 倒序）。", "enum": ["created_at", "updated_at"]},
                "asc": {"type": "boolean", "description": "升序排序。", "default": False},
                "is_my_team": {"type": "boolean", "description": "为 true 时只返回当前成员所属团队范围内的模板。与 `team_ids` 互斥。", "default": False},
                "team_ids": {"type": "array", "items": {"type": "integer", "format": "int64"}, "description": "按团队 ID 列表过滤。当 is_my_team=true 时忽略本字段。"},
                "creator_id": {"type": "integer", "format": "int64", "description": "按创建人成员 ID 过滤。"},
                "query": {"type": "string", "description": "按模板名称做正则或子串匹配。非法正则会被自动转义。"},
            },
        }
        template_list_resp = {
            "type": "object",
            "description": "通知模板的分页列表。",
            "properties": {
                "total": {"type": "integer", "format": "int64", "description": "符合过滤条件的模板总数（跨全部分页）。", "example": 47},
                "has_next_page": {"type": "boolean", "description": "是否还有下一页。", "example": True},
                "items": {"type": "array", "items": {"$ref": "#/components/schemas/TemplateItem"}},
            },
            "required": ["total", "has_next_page", "items"],
        }
        template_create_req = {
            "type": "object",
            "description": "创建通知模板。`template_name` 必填且在账户内唯一。某个通道字段留空表示不为该通道配置自定义模板。",
            "properties": {
                "team_id": {"type": "integer", "format": "int64", "description": "团队归属。0 表示账户全局共享。", "default": 0},
                "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "模板名称，同一账户内唯一，长度 1–39 个字符。", "example": "生产环境默认模板"},
                "description": {"type": "string", "maxLength": 500, "description": "自定义描述。最多 500 字符。"},
                **ch,
            },
            "required": ["template_name"],
        }
        template_create_resp = {
            "type": "object",
            "properties": {
                "template_id": dict(oid, description="新创建的模板 ID。"),
                "template_name": {"type": "string", "description": "从请求中回显的模板名称。", "example": "生产环境默认模板"},
            },
            "required": ["template_id", "template_name"],
        }
        template_update_req = {
            "type": "object",
            "description": "更新已存在的模板。`template_id` 与 `template_name` 必填；请求中的每个通道字段会覆盖存储值——若想清空某个通道，直接留空该字段即可。",
            "properties": {
                "template_id": dict(oid, description="目标模板 ID。"),
                "team_id": {"type": "integer", "format": "int64", "description": "团队归属。0 表示账户全局共享。", "default": 0},
                "template_name": {"type": "string", "minLength": 1, "maxLength": 39, "description": "模板名称，长度 1–39 个字符。"},
                "description": {"type": "string", "maxLength": 500, "description": "自定义描述。最多 500 字符。"},
                **ch,
            },
            "required": ["template_id", "template_name"],
        }
        template_preview_req = {
            "type": "object",
            "description": "使用 Mock 或真实故障数据渲染模板。用于在保存前校验模板语法是否正确。",
            "properties": {
                "content": {"type": "string", "description": "待渲染的模板源。"},
                "type": {"type": "string", "description": "模板对应的通道类型。合法值：`email`、`sms`、`voice`、`dingtalk`、`wecom`、`feishu`、`feishu_app`、`dingtalk_app`、`wecom_app`、`slack_app`、`teams_app`、`telegram`、`slack`、`zoom`。"},
                "incident_id": dict(oid, description="可选的故障 ID。传入时按该真实故障渲染；否则使用内置 Mock 故障。"),
            },
            "required": ["content", "type"],
        }
        template_preview_resp = {
            "type": "object",
            "description": "模板渲染结果。注意：解析/渲染失败时以 success:false + message 的形式返回，而不是返回 4xx。",
            "properties": {
                "success": {"type": "boolean", "description": "模板是否渲染成功。", "example": True},
                "content": {"type": "string", "description": "渲染结果，success=true 时有值。", "example": "Incident 生产库宕机 on P1"},
                "message": {"type": "string", "description": "失败原因，success=false 时有值。"},
            },
            "required": ["success"],
        }

    return {
        "TemplateItem": template_item,
        "TemplateIDRequest": template_id_req,
        "TemplateListRequest": template_list_req,
        "TemplateListResponse": template_list_resp,
        "TemplateCreateRequest": template_create_req,
        "TemplateCreateResponse": template_create_resp,
        "TemplateUpdateRequest": template_update_req,
        "TemplatePreviewRequest": template_preview_req,
        "TemplatePreviewResponse": template_preview_resp,
    }


# --------------------------------------------------------------------------
# Request/response examples for each template operation
# --------------------------------------------------------------------------

REQUEST_EXAMPLES_EN = {
    "info": {"template_id": EXAMPLE_TEMPLATE_ID},
    "list": {"p": 1, "limit": 20, "orderby": "updated_at", "asc": False, "is_my_team": False},
    "create": {
        "team_id": 0,
        "template_name": "Prod incident default",
        "description": "Default template for production incidents.",
        "email": "Incident {{ .IncidentName }} on {{ .Severity }}",
        "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}",
    },
    "update": {
        "template_id": EXAMPLE_TEMPLATE_ID,
        "template_name": "Prod incident default",
        "description": "Updated description.",
        "email": "Incident {{ .IncidentName }} on {{ .Severity }}",
        "sms": "[Flashduty] {{ .IncidentName }} — {{ .Severity }}",
    },
    "delete": {"template_id": EXAMPLE_TEMPLATE_ID},
    "enable": {"template_id": EXAMPLE_TEMPLATE_ID},
    "disable": {"template_id": EXAMPLE_TEMPLATE_ID},
    "preview": {
        "content": "Incident {{ .IncidentName }} on {{ .Severity }}",
        "type": "email",
    },
}
REQUEST_EXAMPLES_ZH = copy.deepcopy(REQUEST_EXAMPLES_EN)
REQUEST_EXAMPLES_ZH["create"]["template_name"] = "生产环境默认模板"
REQUEST_EXAMPLES_ZH["create"]["description"] = "生产环境故障的默认模板。"
REQUEST_EXAMPLES_ZH["update"]["template_name"] = "生产环境默认模板"
REQUEST_EXAMPLES_ZH["update"]["description"] = "已更新的描述。"

RESPONSE_DATA_EN = {
    "info": EXAMPLE_TEMPLATE_ITEM,
    "list": {
        "total": 47,
        "has_next_page": True,
        "items": [EXAMPLE_TEMPLATE_ITEM],
    },
    "create": {"template_id": EXAMPLE_TEMPLATE_ID, "template_name": "Prod incident default"},
    "update": {},
    "delete": {},
    "enable": {},
    "disable": {},
    "preview": {"success": True, "content": "Incident Prod DB down on P1"},
}
RESPONSE_DATA_ZH = copy.deepcopy(RESPONSE_DATA_EN)
RESPONSE_DATA_ZH["create"]["template_name"] = "生产环境默认模板"
RESPONSE_DATA_ZH["list"]["items"] = [dict(EXAMPLE_TEMPLATE_ITEM, template_name="生产环境默认模板")]
RESPONSE_DATA_ZH["info"] = dict(EXAMPLE_TEMPLATE_ITEM, template_name="生产环境默认模板")
RESPONSE_DATA_ZH["preview"] = {"success": True, "content": "Incident 生产库宕机 on P1"}


# --------------------------------------------------------------------------
# Operations — the full 8-operation template catalogue
# --------------------------------------------------------------------------

OPERATIONS = [
    {
        "slug": "template-read-info",
        "op_key": "info",
        "path": "/template/info",
        "permission_key": "template:read:info",
        "audit": False,
        "dangerous": False,
        "request_ref": "TemplateIDRequest",
        "response_ref": "TemplateItem",
        "en": {
            "summary": "Get template detail",
            "description": "Return a single notification template by ID.",
        },
        "zh": {
            "summary": "查看模板详情",
            "description": "按 ID 返回单个通知模板。",
        },
        "usage_en": [
            "Pass `000000000000000000000001` as `template_id` to retrieve the built-in preset template for the caller's account locale.",
        ],
        "usage_zh": [
            "传入 `000000000000000000000001` 作为 `template_id` 可以获取当前账户语种下的系统预置模板。",
        ],
    },
    {
        "slug": "template-read-list",
        "op_key": "list",
        "path": "/template/list",
        "permission_key": "template:read:list",
        "audit": False,
        "dangerous": False,
        "request_ref": "TemplateListRequest",
        "response_ref": "TemplateListResponse",
        "en": {
            "summary": "List templates",
            "description": "Return a paginated list of notification templates.",
        },
        "zh": {
            "summary": "查看模板列表",
            "description": "分页返回当前账户下的通知模板列表。",
        },
        "usage_en": [
            "Pagination defaults to page 1 with 20 rows. The response's `has_next_page` tells you whether another page exists without needing a separate count request.",
            "When `is_my_team` is `true`, `team_ids` is ignored.",
        ],
        "usage_zh": [
            "默认返回第 1 页、每页 20 条。响应中的 `has_next_page` 可以直接告知是否还有下一页，无需额外计数请求。",
            "当 `is_my_team=true` 时 `team_ids` 字段会被忽略。",
        ],
    },
    {
        "slug": "template-write-create",
        "op_key": "create",
        "path": "/template/create",
        "permission_key": "template:write:create",
        "audit": True,
        "dangerous": False,
        "request_ref": "TemplateCreateRequest",
        "response_ref": "TemplateCreateResponse",
        "en": {
            "summary": "Create a template",
            "description": "Create a new notification template.",
        },
        "zh": {
            "summary": "创建模板",
            "description": "创建一个新的通知模板。",
        },
        "usage_en": [
            "`template_name` must be unique within the account; duplicates return `InvalidParameter`.",
            "The server validates every non-empty channel template by rendering it against a mock incident — a syntactic error in any channel fails the whole request with `InvalidParameter`.",
        ],
        "usage_zh": [
            "`template_name` 必须在账户内唯一，重名会返回 `InvalidParameter`。",
            "服务端会对所有非空通道按 Mock 故障做一次渲染校验，任何通道的语法错误都会导致整个请求返回 `InvalidParameter`。",
        ],
    },
    {
        "slug": "template-write-update",
        "op_key": "update",
        "path": "/template/update",
        "permission_key": "template:write:update",
        "audit": True,
        "dangerous": False,
        "request_ref": "TemplateUpdateRequest",
        "response_ref": "EmptyObject",
        "extra_responses": ["Forbidden"],
        "en": {
            "summary": "Update a template",
            "description": "Replace the content of every channel on an existing template.",
        },
        "zh": {
            "summary": "变更模板信息",
            "description": "替换指定模板在所有通道上的内容。",
        },
        "usage_en": [
            "Every channel field in the request overwrites the stored value — send an empty string to clear a channel.",
            "The caller needs data-permission on the template's team; otherwise the response is `AccessDenied`.",
            "The new state is visible via `POST /template/info` immediately after success.",
        ],
        "usage_zh": [
            "请求中的每个通道字段会覆盖存储值——想清空某通道时，把该字段设置为空字符串即可。",
            "调用者必须对目标模板所属团队拥有数据权限，否则返回 `AccessDenied`。",
            "更新成功后可立即通过 `POST /template/info` 查看新状态。",
        ],
    },
    {
        "slug": "template-write-delete",
        "op_key": "delete",
        "path": "/template/delete",
        "permission_key": "template:write:delete",
        "audit": True,
        "dangerous": False,
        "request_ref": "TemplateIDRequest",
        "response_ref": "EmptyObject",
        "extra_responses": ["Forbidden"],
        "en": {
            "summary": "Delete a template",
            "description": "Soft-delete a template by ID.",
        },
        "zh": {
            "summary": "删除模板",
            "description": "按 ID 软删除一个模板。",
        },
        "usage_en": [
            "Fails with `400 ReferenceExist` if the template is still referenced by any channel, escalation rule, or notification subscription. The blocking references are listed in the response body so you can clean them up first.",
            "Deletion is soft — `deleted_at` is set. The record remains for audit, but the template stops appearing in listings and cannot be referenced again.",
        ],
        "usage_zh": [
            "若模板仍被任何协作空间、分派策略或通知订阅引用，会返回 `400 ReferenceExist`，响应中会列出阻塞的引用项，方便先行清理。",
            "删除是软删除（`deleted_at` 被置值），记录仍保留用于审计，但模板不会再出现在列表中，也不能再被引用。",
        ],
    },
    {
        "slug": "template-write-enable",
        "op_key": "enable",
        "path": "/template/enable",
        "permission_key": "template:write:enable",
        "audit": True,
        "dangerous": False,
        "request_ref": "TemplateIDRequest",
        "response_ref": "EmptyObject",
        "extra_responses": ["Forbidden"],
        "deprecated": True,
        "en": {
            "summary": "Enable a template",
            "description": "Flip a template from `disabled` to `enabled`.",
        },
        "zh": {
            "summary": "启用模板",
            "description": "将模板从 `disabled` 切换为 `enabled`。",
        },
        "deprecated_alt_en": "New templates are enabled by default. Delete templates you no longer use instead of disabling them.",
        "deprecated_alt_zh": "新建模板默认启用。若不再使用某个模板，请直接删除，而不是禁用它。",
    },
    {
        "slug": "template-write-disable",
        "op_key": "disable",
        "path": "/template/disable",
        "permission_key": "template:write:disable",
        "audit": True,
        "dangerous": False,
        "request_ref": "TemplateIDRequest",
        "response_ref": "EmptyObject",
        "extra_responses": ["Forbidden"],
        "deprecated": True,
        "en": {
            "summary": "Disable a template",
            "description": "Flip a template from `enabled` to `disabled`.",
        },
        "zh": {
            "summary": "禁用模板",
            "description": "将模板从 `enabled` 切换为 `disabled`。",
        },
        "deprecated_alt_en": "Delete templates you no longer use instead of disabling them.",
        "deprecated_alt_zh": "若不再使用某个模板，请直接删除，而不是禁用它。",
    },
    {
        "slug": "template-read-preview",
        "op_key": "preview",
        "path": "/template/preview",
        "permission_key": "template:read:preview",
        "audit": False,
        "dangerous": False,
        "request_ref": "TemplatePreviewRequest",
        "response_ref": "TemplatePreviewResponse",
        "en": {
            "summary": "Preview a template",
            "description": "Render a template source against mock or real incident data.",
        },
        "zh": {
            "summary": "预览模板",
            "description": "使用 Mock 或指定的真实故障渲染模板源。",
        },
        "usage_en": [
            "**Parse and render failures return `200` with `success: false`**, not a 4xx. The failure reason is in `message`. A true 4xx only happens when the request itself is invalid (missing `content` or `type`).",
            "Pass `incident_id` to render against a real incident from your account; leave it empty to use the built-in mock incident.",
        ],
        "usage_zh": [
            "**模板解析与渲染失败会返回 `200` + `success: false`**，而不是 4xx。失败原因在 `message` 字段中。只有非法参数（例如 `content` 或 `type` 缺失）才会返回 4xx。",
            "传入 `incident_id` 可以按账户中的真实故障渲染；留空则使用内置 Mock 故障。",
        ],
    },
]


# --------------------------------------------------------------------------
# Per-operation builder
# --------------------------------------------------------------------------


def build_operation(op: dict, lang: str, tag: str) -> tuple[str, dict]:
    req_examples = REQUEST_EXAMPLES_EN if lang == "en" else REQUEST_EXAMPLES_ZH
    resp_data = RESPONSE_DATA_EN if lang == "en" else RESPONSE_DATA_ZH

    success_desc = (
        {"en": "Success", "zh": "成功"}[lang]
        if op["op_key"] != "preview"
        else {
            "en": "Success. Render errors come back here as `success: false` with the reason in `message`, NOT as a 4xx.",
            "zh": "成功。渲染错误会在此处以 `success: false` + `message` 的形式返回，而**不是** 4xx。",
        }[lang]
    )

    request_example = req_examples[op["op_key"]]
    response_example = {
        "request_id": "01HK8XQE3Z7JM2NTFQ5YJ8P9R4",
        "data": resp_data[op["op_key"]],
    }

    responses = {
        "200": {
            "description": success_desc,
            "content": {
                "application/json": {
                    "schema": {
                        "allOf": [
                            {"$ref": "#/components/schemas/ResponseEnvelope"},
                            {
                                "type": "object",
                                "properties": {
                                    "data": {"$ref": f"#/components/schemas/{op['response_ref']}"}
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
        code = {"Forbidden": "403", "NotFound": "404", "TooManyRequests": "429"}[extra]
        responses[code] = {"$ref": f"#/components/responses/{extra}"}
    responses["429"] = {"$ref": "#/components/responses/TooManyRequests"}
    responses["500"] = {"$ref": "#/components/responses/ServerError"}

    op_body = {
        "operationId": op["slug"],
        "summary": op[lang]["summary"],
        "description": op[lang]["description"],
        "tags": [tag],
        "x-mint": {
            "content": compose_mint_content(op, lang),
        },
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{op['request_ref']}"},
                    "example": request_example,
                }
            },
        },
        "responses": responses,
    }
    if op.get("deprecated"):
        op_body["deprecated"] = True
    return op["path"], {"post": op_body}


# --------------------------------------------------------------------------
# Top-level build
# --------------------------------------------------------------------------


def build_spec(lang: str) -> dict:
    if lang == "en":
        info = {
            "title": "Flashduty Open API",
            "description": (
                "Public HTTP API for the Flashduty incident management platform — incidents, "
                "notification templates, channels, schedules, monitors, RUM, and platform administration. "
                "Every operation is authenticated with an `app_key` query parameter issued from the "
                "Flashduty console under Account → API Keys. Responses follow a uniform envelope: "
                "`{ request_id, data }` on success, `{ request_id, error }` on failure."
            ),
            "version": "1.0.0",
        }
        tag = "On-call/Templates"
        tag_desc = "Notification templates for email, SMS, voice, and chat integrations."
        sec_desc = (
            "App key issued from the Flashduty console under Account → API Keys. Required on every "
            "public API call. Keep it secret — it grants the same access as the owning account."
        )
    else:
        info = {
            "title": "Flashduty 开放 API",
            "description": (
                "Flashduty 事件管理平台的公开 HTTP API —— 覆盖故障、通知模板、协作空间、值班排班、监控、RUM、"
                "以及平台管理。每次调用都需在 query 中携带 `app_key`，该 key 在 Flashduty 控制台 "
                "账户 → API Key 中签发。所有响应使用统一结构："
                "成功时为 `{ request_id, data }`，失败时为 `{ request_id, error }`。"
            ),
            "version": "1.0.0",
        }
        tag = "On-call/模板管理"
        tag_desc = "用于邮件、短信、语音及各类 IM 集成的通知模板。"
        sec_desc = (
            "在 Flashduty 控制台 账户 → API Key 中签发的 app_key。调用任何公开 API 时都必须携带。"
            "它等同于所属账户的身份凭证，请妥善保管。"
        )

    schemas = {**envelope_schemas(lang), **template_schemas(lang)}

    paths: dict = {}
    for op in OPERATIONS:
        path, item = build_operation(op, lang, tag)
        paths[path] = item

    return {
        "openapi": "3.1.0",
        "info": info,
        "servers": [{"url": "https://api.flashcat.cloud", "description": "Flashduty Open API"}],
        "security": [{"AppKeyAuth": []}],
        "tags": [{"name": tag, "description": tag_desc}],
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
            "responses": shared_responses(lang),
            "schemas": schemas,
        },
    }


def main() -> None:
    en = build_spec("en")
    zh = build_spec("zh")

    assert set(en["paths"].keys()) == set(zh["paths"].keys()), "path keys differ"
    assert set(en["components"]["schemas"].keys()) == set(zh["components"]["schemas"].keys()), "schema keys differ"
    for path, pi in en["paths"].items():
        for method, op in pi.items():
            if not isinstance(op, dict):
                continue
            zh_op = zh["paths"][path][method]
            assert op["operationId"] == zh_op["operationId"], f"operationId mismatch at {path}"
    for name, sch in en["components"]["schemas"].items():
        if "properties" in sch:
            assert set(sch["properties"].keys()) == set(
                zh["components"]["schemas"][name].get("properties", {}).keys()
            ), f"props differ in {name}"

    # ErrorCode enum must be present and the full 20-value list
    assert "ErrorCode" in en["components"]["schemas"]
    assert len(en["components"]["schemas"]["ErrorCode"]["enum"]) == 20

    OUT_EN.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n")
    OUT_ZH.write_text(json.dumps(zh, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT_EN}: paths={len(en['paths'])} schemas={len(en['components']['schemas'])}")
    print(f"wrote {OUT_ZH}: paths={len(zh['paths'])} schemas={len(zh['components']['schemas'])}")


if __name__ == "__main__":
    main()
