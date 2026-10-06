#!/usr/bin/env python3
"""Keep docs.json redirects from bare API paths to their reference pages.

Every API reference page embeds its operation path (for example
`/safari/mcp/server/update`) as a root-relative string in the rendered page
data. Crawlers resolve that string against docs.flashduty.com and request it,
which 404s because every page lives under `/zh/` or `/en/`. This script
redirects each such bare path to the Chinese (default locale) reference page
of that operation, as listed in the docs.json `zh` navigation.

Managed entries are the redirects whose source has no locale prefix and whose
destination is a `/zh/api-reference/` page; all other redirects are left as is.

Usage:
  python3 scripts/api_path_redirects.py           # rewrite docs.json
  python3 scripts/api_path_redirects.py --check   # exit 1 if docs.json is stale
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_JSON = ROOT / "docs.json"
LOCALE = "zh"
DEST_PREFIX = f"/{LOCALE}/api-reference/"
PAGE_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (/\S*)$")


def nav_operations(node, spec=None):
    """Yield (spec_file, method, path) for every OpenAPI page in a nav subtree."""
    if isinstance(node, dict):
        spec = node.get("openapi", spec)
        for key in ("tabs", "groups", "pages"):
            for child in node.get(key, []):
                yield from nav_operations(child, spec)
    elif isinstance(node, str):
        m = PAGE_RE.match(node)
        if m:
            yield spec, m.group(1).lower(), m.group(2)


def is_managed(redirect) -> bool:
    return not redirect["source"].startswith(("/zh/", "/en/")) and redirect[
        "destination"
    ].startswith(DEST_PREFIX)


def build_redirects(docs) -> list:
    lang = next(l for l in docs["navigation"]["languages"] if l["language"] == LOCALE)
    specs = {}
    by_source = {}
    for spec, method, path in nav_operations(lang):
        if spec not in specs:
            specs[spec] = json.loads((ROOT / spec).read_text(encoding="utf-8"))
        href = specs[spec]["paths"][path][method]["x-mint"]["href"]
        # a path served by several methods redirects to its first listed page
        by_source.setdefault(path, href)
    return [{"source": s, "destination": d} for s, d in sorted(by_source.items())]


def main() -> int:
    text = DOCS_JSON.read_text(encoding="utf-8")
    docs = json.loads(text)
    kept = [r for r in docs["redirects"] if not is_managed(r)]
    docs["redirects"] = kept + build_redirects(docs)
    out = json.dumps(docs, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv[1:]:
        if out != text:
            print("docs.json API path redirects are stale; run: python3 scripts/api_path_redirects.py")
            return 1
        return 0
    DOCS_JSON.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
