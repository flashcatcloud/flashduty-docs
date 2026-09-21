#!/usr/bin/env python3
"""Build the Meilisearch documents for the docs Q&A index.

Every page under zh/ and en/ (its frontmatter description, then its body) is
packed into chunks of whole headings and paragraphs, so that the whole page is
searchable and each chunk fits the index embedder's documentTemplateMaxBytes
(4000) together with the page title. A paragraph longer than a chunk is split
at line boundaries, never inside a UTF-8 character. A chunk starts with a
breadcrumb line ("Page title > Section > Subsection") naming where it starts,
so it stays understandable on its own.

Output: one JSON document per line on stdout, fields id/title/content/locale/url.
Document ids are "<md5 of the page path>-<chunk index>", so a page that shrinks
leaves stale ids behind for upload.sh's reconcile step to delete.

Usage: python3 scripts/build_index_docs.py [FILE ...]   (default: all of zh/ and en/)
Env:   BASE_URL  docs base URL (default: https://docs.flashduty.com)
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

BASE_URL = os.environ.get("BASE_URL", "https://docs.flashduty.com").rstrip("/")

# Content bytes per chunk. The embedder template adds the page title and ~30
# bytes of fixed text, and the whole rendered template must stay under 4000.
MAX_CHUNK_BYTES = 3000

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# MDX components are CamelCase (<Card>, <Step>), HTML tags are lowercase
# (<br>, <img>). ALL_CAPS placeholders such as <YOUR_APP_KEY> are content.
TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9.]*)((?:\s[^<>]*)?)/?>")
TITLE_ATTR_RE = re.compile(r"""\btitle=(?:"([^"]*)"|'([^']*)'|\{["']([^"']*)["']\})""")


def page_id(path):
    rel = re.sub(r"\.mdx?$", "", path)
    return hashlib.md5(rel.encode("utf-8")).hexdigest()


def split_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            meta = {}
            for line in lines[1:i]:
                m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip("\"'")
            return meta, "\n".join(lines[i + 1 :])
    return {}, text


def page_title(meta, path):
    if meta.get("title"):
        return meta["title"]
    stem = re.sub(r"\.mdx?$", "", os.path.basename(path))
    return re.sub(r"^[0-9.]*\s*", "", stem)


def page_url(meta, path):
    url = meta.get("url", "")
    if url.startswith("/"):
        return BASE_URL + url
    if url:
        return url
    return BASE_URL + "/" + re.sub(r"\.mdx?$", "", path)


def strip_tag(m):
    name = m.group(1)
    if name.isupper() or "_" in name:
        return m.group(0)
    if not (name[0].isupper() or name.islower()):
        return m.group(0)
    if m.group(0).startswith("</"):
        return ""
    t = TITLE_ATTR_RE.search(m.group(2) or "")
    if t:
        return "\n" + next(g for g in t.groups() if g is not None) + "\n"
    return ""


def clean_body(body):
    """Drop MDX imports and component/HTML tags outside code fences."""
    out, prose, in_fence = [], [], False

    def flush_prose():
        if prose:
            text = TAG_RE.sub(strip_tag, "\n".join(prose))
            out.extend(line.rstrip() for line in text.split("\n"))
            prose.clear()

    for line in body.split("\n"):
        if FENCE_RE.match(line):
            if not in_fence:
                flush_prose()
            in_fence = not in_fence
            out.append(line.rstrip())
        elif in_fence:
            out.append(line.rstrip())
        elif not line.startswith(("import ", "export ")):
            prose.append(line)
    flush_prose()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")


def blocks(body):
    """Yield (heading_level, heading_text) for headings and (0, text) for
    paragraphs. A fenced code block is one paragraph."""
    para, in_fence = [], False
    for line in body.split("\n"):
        if FENCE_RE.match(line):
            para.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            para.append(line)
            continue
        h = HEADING_RE.match(line)
        if h:
            if para:
                yield 0, "\n".join(para)
                para = []
            yield len(h.group(1)), h.group(2)
        elif line.strip():
            para.append(line)
        elif para:
            yield 0, "\n".join(para)
            para = []
    if para:
        yield 0, "\n".join(para)


def utf8_len(s):
    return len(s.encode("utf-8"))


def split_oversized(text, limit):
    """Split text into pieces of at most limit UTF-8 bytes, preferring line
    boundaries and never cutting inside a character."""
    pieces, cur = [], ""
    for line in text.split("\n"):
        while utf8_len(line) > limit:
            head = line.encode("utf-8")[:limit].decode("utf-8", "ignore")
            if cur:
                pieces.append(cur)
                cur = ""
            pieces.append(head)
            line = line[len(head) :]
        candidate = line if not cur else cur + "\n" + line
        if utf8_len(candidate) > limit:
            pieces.append(cur)
            cur = line
        else:
            cur = candidate
    if cur:
        pieces.append(cur)
    return pieces


def chunk_page(title, body):
    """Return the list of chunk contents for one page."""
    chunks = []
    h2 = h3 = ""
    # The open chunk: its breadcrumb, its parts, and the bytes they take
    # including the blank lines between them. It fits while size <= budget.
    crumb, parts, size, budget = "", [], 0, 0

    def breadcrumb():
        return " > ".join(p for p in (title, h2, h3) if p)

    for level, text in blocks(body):
        if level:
            if level <= 2:
                h2, h3 = (text if level == 2 else ""), ""
            elif level == 3:
                h3 = text
            text = "#" * level + " " + text
        # Size pieces for a chunk that would start here, the tightest case.
        limit = MAX_CHUNK_BYTES - utf8_len(breadcrumb()) - 2
        for piece in split_oversized(text, limit) if utf8_len(text) > limit else [text]:
            if parts and size + 2 + utf8_len(piece) > budget:
                chunks.append(crumb + "\n\n" + "\n\n".join(parts))
                parts = []
            if not parts and 0 < level <= 3:
                continue  # the breadcrumb of the chunk that starts here names it
            if parts:
                size += 2 + utf8_len(piece)
            else:
                crumb = breadcrumb()
                budget = MAX_CHUNK_BYTES - utf8_len(crumb) - 2
                size = utf8_len(piece)
            parts.append(piece)
    if parts:
        chunks.append(crumb + "\n\n" + "\n\n".join(parts))
    return chunks


def build(path):
    locale = "zh-CN" if path.startswith("zh/") else "en-US"
    meta, body = split_frontmatter(Path(path).read_text(encoding="utf-8"))
    title = page_title(meta, path)
    url = page_url(meta, path)
    pid = page_id(path)
    body = clean_body(body)
    if meta.get("description"):
        body = meta["description"] + "\n\n" + body
    for i, content in enumerate(chunk_page(title, body)):
        yield {
            "id": f"{pid}-{i:03d}",
            "title": title,
            "content": content,
            "locale": locale,
            "url": url,
        }


def doc_files():
    files = []
    for root in ("zh", "en"):
        for p in Path(root).rglob("*"):
            if p.suffix in (".md", ".mdx") and p.stem != "index" and p.is_file():
                files.append(p.as_posix())
    return sorted(files)


def main(argv):
    files = argv[1:] or doc_files()
    for path in files:
        for doc in build(path):
            sys.stdout.write(json.dumps(doc, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv)
