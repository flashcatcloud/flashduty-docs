#!/usr/bin/env python3
"""
parse_pgy_registry.py — deterministic parser for fc-pgy's API catalog.

The catalog lives as Go struct literals inside
`fc-pgy/logic/api/api_test.go`. Commented rows are existing production
APIs already in the DB; uncommented rows are new additions awaiting
deployment (left active for `go test` to upsert them). Both represent
live APIs. This script extracts all rows into structured JSON so the
rest of the api-review skill can work with a clean data model.

Usage:
  parse_pgy_registry.py <path-to-api_test.go> [--json | --summary]

Default emits JSON to stdout and a short summary to stderr.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# A row looks like:
#   {Product: "Platform", Method: "POST", Path: "/access/external-exchange",
#    Name: "access:read:externalExchange", NameCN: "外部认证交换",
#    Description: "...", Auth: "none", IsDangerous: false, IsAudit: false,
#    Qps: 100, Provider: "pgy", Domain: "http://127.0.0.1:11482"},
# Older rows can start with `ID: <number>,`; current name-keyed rows do not.
#
# Rows can be prefixed with `//` (commented-out). The convention:
# - Commented rows = existing production APIs already persisted in the DB.
# - Uncommented rows = new additions not yet deployed, left active so
#   `go test` can upsert them into the DB.
# Both are equally valid — a commented row is NOT deleted or inactive.
# The file is a cumulative ledger; nothing deletes a row once registered.

ROW_RE = re.compile(
    r"""^\s*(?P<commented>//\s*)?\{(?:ID:\s*(?P<id>\d+)\s*,\s*|(?=\s*Product:))(?P<fields>.*)\},?\s*$""",
    re.VERBOSE,
)

# Field extractor. Each field is `<Key>: <value>` where the value is either
# a quoted string, a bool, or a number. We rely on the fact that Go's struct
# literal syntax has no escaped braces inside these rows.
FIELD_RE = re.compile(
    r"""(?P<key>[A-Za-z]+)\s*:\s*
        (?:"(?P<str>(?:[^"\\]|\\.)*)"
          |(?P<bool>true|false)
          |(?P<num>-?\d+))""",
    re.VERBOSE,
)

# We only care about these keys. Everything else is ignored silently.
KEEP_KEYS = {
    "Method",
    "Path",
    "Name",
    "NameCN",
    "Description",
    "Auth",
    "Provider",
    "IsDangerous",
    "IsAudit",
}


def parse_file(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as f:
        for lineno, line in enumerate(f, start=1):
            m = ROW_RE.match(line)
            if not m:
                continue

            row: dict = {
                "commented": m.group("commented") is not None,
                "line": lineno,
            }
            if m.group("id") is not None:
                row["id"] = int(m.group("id"))

            for fm in FIELD_RE.finditer(m.group("fields")):
                key = fm.group("key")
                if key not in KEEP_KEYS:
                    continue
                if fm.group("str") is not None:
                    row[snake(key)] = _unescape_go(fm.group("str"))
                elif fm.group("bool") is not None:
                    row[snake(key)] = fm.group("bool") == "true"
                else:
                    row[snake(key)] = int(fm.group("num"))

            # A row is only usable if at minimum it has method/path/auth/provider.
            missing = [k for k in ("method", "path", "auth", "provider") if k not in row]
            if missing:
                row["_warning"] = f"missing fields: {','.join(missing)}"

            rows.append(row)

    return rows


def snake(camel: str) -> str:
    # Keep it simple — our whitelist is small.
    return {
        "Method": "method",
        "Path": "path",
        "Name": "name",
        "NameCN": "name_cn",
        "Description": "description",
        "Auth": "auth",
        "Provider": "provider",
        "IsDangerous": "is_dangerous",
        "IsAudit": "is_audit",
    }[camel]


def _unescape_go(s: str) -> str:
    # Go string escapes we care about in this catalog are \" and \\.
    return s.replace('\\"', '"').replace("\\\\", "\\")


def summarize(rows: list[dict]) -> str:
    total = len(rows)
    commented = sum(1 for r in rows if r.get("commented"))
    warnings = [r for r in rows if "_warning" in r]

    lines: list[str] = []
    lines.append(f"parsed {total} rows ({total - commented} uncommented, {commented} commented)")
    if warnings:
        lines.append(f"  {len(warnings)} row(s) had parser warnings — check --json output")

    by_auth = Counter(r.get("auth", "?") for r in rows)
    lines.append("by auth:")
    for auth, n in sorted(by_auth.items(), key=lambda x: -x[1]):
        lines.append(f"  {auth:<12} {n}")

    by_provider = Counter(r.get("provider", "?") for r in rows)
    lines.append("by provider:")
    for provider, n in sorted(by_provider.items(), key=lambda x: -x[1]):
        lines.append(f"  {provider:<12} {n}")

    public = [r for r in rows if r.get("auth") in ("all", "optional")]
    lines.append(f"public rows (auth in all|optional): {len(public)}")

    top_segments = Counter(
        r["path"].split("/")[1] for r in public if r.get("path", "").startswith("/")
    )
    lines.append("public path prefixes:")
    for seg, n in sorted(top_segments.items(), key=lambda x: -x[1]):
        lines.append(f"  /{seg:<16} {n}")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="path to fc-pgy/logic/api/api_test.go")
    ap.add_argument(
        "--format",
        choices=("json", "summary", "both"),
        default="both",
        help="what to emit. `both` writes JSON to stdout and summary to stderr (default)",
    )
    args = ap.parse_args()

    if not args.path.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2

    rows = parse_file(args.path)

    if args.format in ("json", "both"):
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    if args.format in ("summary", "both"):
        print(summarize(rows), file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
