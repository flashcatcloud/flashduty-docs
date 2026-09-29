#!/usr/bin/env python3
"""Turn the OpenAPI spec into one plain-text search document per API operation.

Each document lists the operation's request body as flattened field paths:

    rule_configs.check_anydata.severity  string  Critical | Warning | Info — 有数据告警的事件级别

which is the shape a reader scans fastest, and the same path a client uses to
address the field. Documents are keyed by md5("openapi/<METHOD> <path>") and
tagged `source: openapi`, next to the `public` documents upload.sh builds from
the pages. They carry no `locale`: they are fetched by id, and a document
outside every locale stays out of the locale-filtered documentation search.

Usage: openapi_docs.py <spec.json>   (prints a JSON array of documents)
"""
import hashlib
import json
import sys

MAX_DEPTH = 8


def resolve(spec, node):
    seen = set()
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        cur = spec
        for part in ref.lstrip("#/").split("/"):
            cur = cur[part]
        node = cur
    return node if isinstance(node, dict) else {}


def type_of(node):
    t = node.get("type", "object" if "properties" in node else "")
    if isinstance(t, list):  # OpenAPI 3.1: ["string", "null"]
        t = "|".join(x for x in t if x != "null") or "null"
    return t


def one_line(text):
    return " ".join(str(text or "").split())


def walk(spec, node, path, out, depth=0):
    node = resolve(spec, node)
    if depth > MAX_DEPTH or not node:
        return
    for sub in node.get("allOf", []):
        walk(spec, sub, path, out, depth + 1)
    # Alternative shapes share one field path, so each is headed by its number:
    # listed flat, two shapes' constraints would read as one contradictory list.
    for i, sub in enumerate(node.get("oneOf") or node.get("anyOf") or [], 1):
        title = one_line(resolve(spec, sub).get("title"))
        out.append(f"{path or '(请求体)'}  形态 {i}{'：' + title if title else ''}")
        walk(spec, sub, path, out, depth + 1)
    required = set(node.get("required", []))
    for name, sub in node.get("properties", {}).items():
        child = f"{path}.{name}" if path else name
        sub_r = resolve(spec, sub)
        t = type_of(sub_r)
        items = resolve(spec, sub_r.get("items", {})) if t == "array" else {}
        if t == "array":
            t = f"array<{type_of(items) or 'object'}>"
        enum = sub_r.get("enum") or items.get("enum")
        parts = [child, t] + (["必填"] if name in required else []) + ([" | ".join(map(str, enum))] if enum else [])
        line = "  ".join(parts)
        desc = one_line(sub_r.get("description"))
        out.append(f"{line} — {desc}" if desc else line)
        if items:
            walk(spec, items, child + "[]", out, depth + 1)
        else:
            walk(spec, sub_r, child, out, depth + 1)


def documents(spec):
    for p, ops in spec.get("paths", {}).items():
        for m, op in ops.items():
            if m not in ("get", "post", "put", "patch", "delete"):
                continue
            operation = f"{m.upper()} {p}"
            summary = one_line(op.get("summary"))
            lines = [f"# {operation}", summary, one_line(op.get("description"))]
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body:
                fields = []
                walk(spec, body, "", fields)
                lines += ["", "## 请求体字段", *fields]
            text = "\n".join(lines).strip()
            path = f"openapi/{operation}"
            yield {
                "id": hashlib.md5(path.encode()).hexdigest(),
                "source": "openapi",
                "path": path,
                "title": summary or operation,
                "url": "",
                "content": " ".join(text.split()),
                "body": text,
            }


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        print(json.dumps(list(documents(json.load(f))), ensure_ascii=False))
