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
        # recurse
        if prop.get("type") == "object" or "properties" in prop:
            walk_properties(prop, pwhere, file, rep, seen)
        items = prop.get("items")
        if isinstance(items, dict) and "$ref" not in items:
            walk_properties(items, pwhere + "[]", file, rep, seen)


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
            ok = op.get("responses", {}).get("200", {})
            if "$ref" not in ok:
                content = ok.get("content", {}).get("application/json", {})
                # only JSON responses can carry a JSON example; binary/ndjson
                # downloads and empty 200s are exempt
                if content and "example" not in content and "examples" not in content:
                    rep.add(file, "missing-example", where, "200 response has no example")


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
