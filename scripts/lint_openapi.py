#!/usr/bin/env python3
"""Lint Flashduty public OpenAPI specs for documentation quality.

Stdlib-only. Lints every api-reference/*.openapi.*.json file (per-module and
consolidated) and fails on:

  missing-description  every schema property must carry a non-empty description
                       (recursively, including array item objects and inline
                       allOf members; pure $ref nodes are exempt)
  epoch-wording        integer fields named ts / timestamp / *_at / *_time must
                       mention Unix/epoch/timestamp/时间戳 in the description —
                       the go-flashduty SDK maps these fields by description text
  enum-undocumented    every value of a string enum must be mentioned in the
                       property description (backticked or bare), so readers
                       learn what each value means
  missing-example      every operation needs a request example (when it has a
                       request body) and a 200 response example
  int-enum-undocumented  every value of an integer enum must be mentioned in the
                       property description
  required-undeclared  a schema's `required` may only name its own properties
                       (schemas composed with allOf are exempt)
  missing-403          every operation documents the 403 response (APP Key
                       scopes can deny any operation)
  example-mismatch     request and 200 response examples must match their schema:
                       types, enum members, no undeclared keys, and required keys
                       present in responses
  description-too-long the operation description is the one-line subtitle;
                       longer prose belongs in x-mint.content

Usage:
  python3 scripts/lint_openapi.py            # lint all spec files, exit 1 on violations
  python3 scripts/lint_openapi.py --warn-only
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_GLOB = "api-reference/*.json"
# the legacy hand-maintained Apifox export is exempt — it is read-only reference
SPEC_EXCLUDE = ("openapi.legacy",)

EPOCH_RE = re.compile(r"\b(unix|epoch|timestamp)\b|时间戳", re.I)
EPOCH_NAME_RE = re.compile(r"^(ts|timestamp)$|_at$|_time$")
# duration-ish names that only look like timestamps
DURATION_HINT_RE = re.compile(r"timeout|interval|duration|delay|elapsed")

# enum value sets whose meaning is self-evident everywhere they appear;
# anything else must explain each value in the property description
WELL_KNOWN_ENUMS = [
    {"Critical", "Warning", "Info"},
    {"Critical", "Warning", "Info", "Ok"},
    {"enabled", "disabled"},
    {"success", "failed"},
]

# the operation `description` renders as the page subtitle
MAX_OP_DESCRIPTION = 220

# field-name exemptions: order-by enums list sortable field names, whose
# meaning lives on the referenced fields themselves
ENUM_EXEMPT_NAMES = re.compile(r"^(orderby|order_by)$")


def enum_is_well_known(values) -> bool:
    vals = {v for v in values if isinstance(v, str) and v}
    return any(vals <= s for s in WELL_KNOWN_ENUMS)


class Reporter:
    def __init__(self):
        self.violations = []

    def add(self, file, rule, where, detail):
        self.violations.append((file, rule, where, detail))

    def dump(self):
        by_rule = {}
        for f, rule, where, detail in self.violations:
            by_rule.setdefault(rule, []).append((f, where, detail))
        for rule, items in sorted(by_rule.items()):
            print(f"\n## {rule} ({len(items)})")
            for f, where, detail in items[:50]:
                print(f"  {f}: {where} — {detail}")
            if len(items) > 50:
                print(f"  ... and {len(items) - 50} more")
        print(f"\nTotal: {len(self.violations)} violation(s)")


def walk_properties(node, where, file, rep, seen):
    """Recursively check every property under a schema node."""
    if not isinstance(node, dict):
        return
    oid = id(node)
    if oid in seen:
        return
    seen.add(oid)

    for member in node.get("allOf", []):
        if isinstance(member, dict) and "$ref" not in member:
            walk_properties(member, where, file, rep, seen)

    if "allOf" not in node:
        undeclared = [r for r in node.get("required", []) if r not in node.get("properties", {})]
        if undeclared:
            rep.add(file, "required-undeclared", where, f"required names undeclared properties: {undeclared}")

    for name, prop in node.get("properties", {}).items():
        if not isinstance(prop, dict):
            continue
        pwhere = f"{where}.{name}"
        if "$ref" in prop:
            continue
        desc = prop.get("description")
        if not desc or not desc.strip():
            rep.add(file, "missing-description", pwhere, f"type={prop.get('type')}")
            desc = ""
        # epoch wording
        if prop.get("type") == "integer" and EPOCH_NAME_RE.search(name) \
                and not DURATION_HINT_RE.search(name):
            if not EPOCH_RE.search(desc):
                rep.add(file, "epoch-wording", pwhere,
                        "integer time field without Unix/epoch/timestamp wording")
        # enum values documented
        enum = prop.get("enum")
        if enum and prop.get("type") == "string" and desc and not enum_is_well_known(enum) \
                and not ENUM_EXEMPT_NAMES.match(name):
            missing = [v for v in enum if isinstance(v, str) and v and v not in desc]
            if missing:
                rep.add(file, "enum-undocumented", pwhere,
                        f"enum values not explained in description: {missing}")
        if enum and prop.get("type") == "integer":
            missing = [v for v in enum if str(v) not in desc]
            if missing:
                rep.add(file, "int-enum-undocumented", pwhere,
                        f"integer enum values not explained in description: {missing}")
        # recurse
        if prop.get("type") == "object" or "properties" in prop:
            walk_properties(prop, pwhere, file, rep, seen)
        items = prop.get("items")
        if isinstance(items, dict) and "$ref" not in items:
            walk_properties(items, pwhere + "[]", file, rep, seen)


def resolve(spec, node, depth=0):
    while isinstance(node, dict) and "$ref" in node and depth < 20:
        node = spec["components"]["schemas"].get(node["$ref"].split("/")[-1], {})
        depth += 1
    return node


def flatten(spec, schema):
    """Merge allOf members into one object schema (properties + required)."""
    s = resolve(spec, schema)
    if not isinstance(s, dict) or "allOf" not in s:
        return s
    merged = {"type": "object", "properties": {}, "required": []}
    for m in s["allOf"] + [{k: v for k, v in s.items() if k != "allOf"}]:
        m = flatten(spec, m)
        merged["properties"].update(m.get("properties", {}))
        merged["required"] += m.get("required", [])
        if m.get("additionalProperties"):
            merged["additionalProperties"] = m["additionalProperties"]
    return merged


def check_example(spec, schema, ex, file, where, rep, path="$", response=False, depth=0):
    s = flatten(spec, schema)
    if depth > 20 or not isinstance(s, dict) or "oneOf" in s or "anyOf" in s:
        return
    types = s.get("type")
    types = types if isinstance(types, list) else [types] if types else []
    if ex is None:
        if types and "null" not in types:
            rep.add(file, "example-mismatch", where, f"{path} is null but the schema is not nullable")
        return
    if "enum" in s and ex not in s["enum"]:
        rep.add(file, "example-mismatch", where, f"{path}={ex!r} is not an enum member")
    kind = next((t for t in types if t != "null"), "object" if "properties" in s else None)
    if kind == "object":
        if not isinstance(ex, dict):
            rep.add(file, "example-mismatch", where, f"{path} should be an object")
            return
        props, extra = s.get("properties", {}), s.get("additionalProperties")
        for k, v in ex.items():
            if k in props:
                check_example(spec, props[k], v, file, where, rep, f"{path}.{k}", response, depth + 1)
            elif isinstance(extra, dict):
                check_example(spec, extra, v, file, where, rep, f"{path}.{k}", response, depth + 1)
            elif props and not extra:
                rep.add(file, "example-mismatch", where, f"{path}.{k} is not declared in the schema")
        if response:
            for r in s.get("required", []):
                if r not in ex:
                    rep.add(file, "example-mismatch", where, f"{path}.{r} is required but missing")
    elif kind == "array":
        if not isinstance(ex, list):
            rep.add(file, "example-mismatch", where, f"{path} should be an array")
            return
        for i, v in enumerate(ex):
            check_example(spec, s.get("items", {}), v, file, where, rep, f"{path}[{i}]", response, depth + 1)
    elif kind in ("integer", "number", "string", "boolean"):
        ok = {"integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
              "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
              "string": lambda v: isinstance(v, str),
              "boolean": lambda v: isinstance(v, bool)}[kind](ex)
        if not ok:
            rep.add(file, "example-mismatch", where, f"{path}={ex!r} is not a {kind}")


def lint_operations(spec, file, rep):
    for path, pi in spec.get("paths", {}).items():
        if not isinstance(pi, dict):
            continue
        for method, op in pi.items():
            if not isinstance(op, dict):
                continue
            where = f"{method.upper()} {path}"
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            if body and "example" not in body and "examples" not in body:
                rep.add(file, "missing-example", where, "request body has no example")
            if body.get("schema") and "example" in body:
                check_example(spec, body["schema"], body["example"], file, where + " request", rep)
            if "403" not in op.get("responses", {}):
                rep.add(file, "missing-403", where, "no 403 response")
            if len(op.get("description", "")) > MAX_OP_DESCRIPTION:
                rep.add(file, "description-too-long", where,
                        f"{len(op['description'])} chars; move detail into x-mint.content")
            ok = op.get("responses", {}).get("200", {})
            if "$ref" not in ok:
                content = ok.get("content", {}).get("application/json", {})
                # only JSON responses can carry a JSON example; binary/ndjson
                # downloads and empty 200s are exempt
                if content and "example" not in content and "examples" not in content:
                    rep.add(file, "missing-example", where, "200 response has no example")
                if content.get("schema") and "example" in content:
                    check_example(spec, content["schema"], content["example"], file,
                                  where + " response", rep, response=True)


def lint_file(path, rep):
    spec = json.load(open(path))
    file = path.name
    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        walk_properties(schema, f"schema:{name}", file, rep, set())
    lint_operations(spec, file, rep)


def main():
    files = [f for f in sorted(ROOT.glob(SPEC_GLOB))
             if not any(x in f.name for x in SPEC_EXCLUDE)]
    if not files:
        print(f"no spec files matched {SPEC_GLOB} under {ROOT}", file=sys.stderr)
        return 2
    rep = Reporter()
    for f in files:
        lint_file(f, rep)
    if not rep.violations:
        print(f"OK: {len(files)} spec files, no violations")
        return 0
    rep.dump()
    if "--warn-only" in sys.argv:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
