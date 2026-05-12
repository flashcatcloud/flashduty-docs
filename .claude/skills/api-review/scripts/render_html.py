#!/usr/bin/env python3
"""Render an api-review findings file to a kami-styled HTML report.

The HTML is the human-readable companion to the YAML. YAML stays the
agent-readable source of truth; this script never modifies it.

Usage:
    render_html.py <findings.json|findings.yaml> [--out <html_path>]

Resolution:
    - If the input ends in .json, parse it directly.
    - If .yaml, prefer a sibling .json with the same stem. Otherwise import
      PyYAML; if unavailable, exit with a helpful error.

Expected shape:
    {
      "scope": "on-call/template",
      "generated_at": "...",
      "docs_path": "api-reference/on-call/template/",
      "tag_en": "Templates",
      "tag_zh": "模板管理",
      "providers": [...],
      "source_registry": "...",
      "source_registry_commit": "<sha>",
      "operations": [
        {id, method, path, name, name_cn, description, auth,
         is_dangerous, is_audit, handler: {repo, file, input_type, output_type, notes}}
      ],
      "unresolved": [
        {id, method, path, reason}
      ],
      "stats": {...}
    }
"""
import argparse
import html as html_mod
import json
import os
import sys
from collections import Counter


def load_doc(path: str):
    if path.endswith('.json'):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    json_sibling = path[:-5] + '.json' if path.endswith('.yaml') else path + '.json'
    if os.path.exists(json_sibling):
        with open(json_sibling, encoding='utf-8') as f:
            return json.load(f)
    try:
        import yaml  # type: ignore
    except ImportError:
        sys.exit(
            f"Cannot read YAML without PyYAML. Either install pyyaml or "
            f"ensure a JSON sidecar exists at {json_sibling}."
        )
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


CSS = r"""
:root {
  --parchment: #f5f4ed;
  --ivory: #faf9f5;
  --warm-sand: #e8e6dc;
  --warm-sand-2: #ddd9c8;
  --near-black: #141413;
  --dark-warm: #3d3d3a;
  --olive: #504e49;
  --stone: #6b6a64;
  --border: #e8e6dc;
  --border-soft: #e5e3d8;
  --brand: #1B365D;
  --ink-light: #2D5A8A;
  --tag-bg: #EEF2F7;

  --sev-error: #7A2622;
  --sev-error-bg: #F4E6E2;
  --sev-warning: #7A5414;
  --sev-warning-bg: #F2EBD9;
  --sev-info: #1B365D;
  --sev-info-bg: #E4ECF5;

  --m-get:    #1B365D;  --m-get-bg:    #E4ECF5;
  --m-post:   #7A5414;  --m-post-bg:   #F2EBD9;
  --m-put:    #504e49;  --m-put-bg:    #E8E6DC;
  --m-delete: #7A2622;  --m-delete-bg: #F4E6E2;
  --m-patch:  #2D5A8A;  --m-patch-bg:  #E4ECF5;

  --serif: Charter, "TsangerJinKai02", "Source Han Serif SC",
           "Noto Serif CJK SC", "Songti SC", "STSong",
           Georgia, Palatino, "Times New Roman", serif;
  --mono: "JetBrains Mono", "SF Mono", "Fira Code", Consolas, Monaco,
          "TsangerJinKai02", "Source Han Serif SC", monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body {
  background: var(--parchment);
  color: var(--near-black);
  font-family: var(--serif);
  font-weight: 400;
  font-size: 14px;
  line-height: 1.55;
  letter-spacing: 0.1pt;
  -webkit-font-smoothing: antialiased;
}

header {
  background: var(--parchment);
  border-bottom: 0.5pt solid var(--border);
  padding: 28px 44px 18px;
  position: sticky; top: 0; z-index: 10;
}
header .eyebrow { font-size: 10px; letter-spacing: 1.4pt; text-transform: uppercase; color: var(--stone); margin-bottom: 6px; }
header h1 {
  font-family: var(--serif);
  font-size: 26px; font-weight: 500;
  margin: 0; letter-spacing: 0.2pt;
  color: var(--near-black);
  border-left: 2.5pt solid var(--brand);
  padding-left: 10px; border-radius: 1.5pt;
  line-height: 1.2;
}
header h1 .subtle { color: var(--stone); font-weight: 400; margin-left: 6px; }

.tallies { display: flex; gap: 28px; margin: 14px 0 0 12px; align-items: baseline; flex-wrap: wrap; }
.tally { display: flex; align-items: baseline; gap: 6px; }
.tally .num { font-size: 22px; font-weight: 500; }
.tally .lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 1.4pt; color: var(--stone); }
.tally.unresolved .num { color: var(--sev-error); }
.tally.danger .num     { color: var(--sev-error); }
.tally.audit .num      { color: var(--sev-warning); }

.meta-line { margin-top: 12px; font-size: 11px; color: var(--stone); letter-spacing: 0.2pt; }
.meta-line .sep { margin: 0 8px; color: var(--warm-sand-2); }
.meta-line code { font-family: var(--mono); font-size: 11px; }

.controls {
  display: flex; flex-wrap: wrap; gap: 8px 10px; align-items: center;
  margin-top: 14px; padding-top: 14px;
  border-top: 0.5pt solid var(--border);
}
.controls input[type=search], .controls select {
  background: var(--ivory); color: var(--near-black);
  border: 0.5pt solid var(--border-soft);
  padding: 5px 9px; border-radius: 4pt;
  font-size: 12px; font-family: var(--serif); letter-spacing: 0.1pt;
}
.controls input[type=search] { min-width: 240px; }
.controls input[type=search]:focus, .controls select:focus {
  outline: none; border-color: var(--brand);
  box-shadow: 0 0 0 2px rgba(27, 54, 93, 0.08);
}
.controls label { display: inline-flex; gap: 5px; align-items: center; font-size: 11px; color: var(--olive); letter-spacing: 0.2pt; }
.controls .btn {
  background: var(--warm-sand); color: var(--dark-warm);
  border: 0.5pt solid var(--border-soft);
  padding: 5px 12px; border-radius: 4pt;
  font-size: 11px; letter-spacing: 0.3pt; font-family: var(--serif);
  cursor: pointer;
}
.controls .btn:hover { background: var(--warm-sand-2); }
.controls .divider { width: 1px; height: 16px; background: var(--border); margin: 0 4px; }

.pager { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: 11px; color: var(--stone); letter-spacing: 0.2pt; }
.pager #count { color: var(--olive); }
.pager .spacer { flex: 1; }
.pager button {
  background: var(--ivory); color: var(--dark-warm);
  border: 0.5pt solid var(--border-soft);
  padding: 3px 9px; border-radius: 3pt; font-size: 11px;
  cursor: pointer; font-family: var(--serif);
}
.pager button:hover:not(:disabled) { background: var(--warm-sand); }
.pager button:disabled { opacity: 0.35; cursor: not-allowed; }

main { padding: 22px 44px 80px; }

.section-title {
  font-family: var(--serif);
  font-size: 14px; font-weight: 500;
  color: var(--near-black);
  margin: 22px 0 10px;
  border-left: 2.5pt solid var(--brand);
  padding-left: 10px; border-radius: 1.5pt;
  letter-spacing: 0.2pt;
}
.section-title.danger { border-left-color: var(--sev-error); }

.op {
  background: var(--ivory);
  border: 0.5pt solid var(--border);
  border-left: 2.5pt solid var(--brand);
  border-radius: 6pt;
  margin-bottom: 8px;
  transition: box-shadow 0.18s;
}
.op.dangerous { border-left-color: var(--sev-error); }
.op.audit { border-left-color: var(--sev-warning); }
.op.unresolved { border-left-color: var(--sev-error); background: var(--sev-error-bg); }
.op:hover { box-shadow: 0 4pt 18pt rgba(0, 0, 0, 0.04); }

.op-head {
  display: grid;
  grid-template-columns: 50px 70px 1fr 1fr auto 14px;
  gap: 12px; align-items: center;
  padding: 9px 14px;
  cursor: pointer; user-select: none;
}
.op-head .id { font-family: var(--mono); font-size: 11px; color: var(--stone); letter-spacing: 0.3pt; }
.op-head .method {
  font-family: var(--mono); font-size: 10px; font-weight: 500;
  letter-spacing: 0.6pt;
  padding: 3px 0; border-radius: 2pt; text-align: center;
}
.op-head .method.GET    { background: var(--m-get-bg);    color: var(--m-get); }
.op-head .method.POST   { background: var(--m-post-bg);   color: var(--m-post); }
.op-head .method.PUT    { background: var(--m-put-bg);    color: var(--m-put); }
.op-head .method.DELETE { background: var(--m-delete-bg); color: var(--m-delete); }
.op-head .method.PATCH  { background: var(--m-patch-bg);  color: var(--m-patch); }
.op-head .path {
  font-family: var(--mono); font-size: 12.5px;
  color: var(--near-black); letter-spacing: 0.1pt;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.op-head .name {
  font-size: 12.5px;
  color: var(--dark-warm);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.op-head .name .cn { color: var(--stone); margin-left: 6px; }
.op-head .flags { display: flex; gap: 4px; }
.op-head .flags .tag { margin: 0; }
.op-head .caret { color: var(--stone); transition: transform 0.15s; text-align: center; font-size: 11px; }
.op.open .caret { transform: rotate(90deg); }

.op-body { display: none; padding: 14px 18px 18px; border-top: 0.5pt dashed var(--border); }
.op.open .op-body { display: block; }

.kv { display: grid; grid-template-columns: 140px 1fr; column-gap: 18px; row-gap: 8px; margin: 0; }
.kv dt { font-size: 10px; text-transform: uppercase; letter-spacing: 1pt; color: var(--stone); padding-top: 2px; }
.kv dd { margin: 0; font-size: 13px; color: var(--near-black); }
.kv dd code {
  font-family: var(--mono); font-size: 12px;
  background: var(--parchment);
  border: 0.5pt solid var(--border-soft);
  padding: 1px 5px; border-radius: 2pt;
}

.tag {
  display: inline-block;
  background: var(--tag-bg); color: var(--brand);
  padding: 1px 6px; border-radius: 2pt;
  font-family: var(--mono); font-size: 10px;
  letter-spacing: 0.3pt; margin: 0 4px 2px 0;
}
.tag.warm { background: var(--sev-warning-bg); color: var(--sev-warning); }
.tag.danger { background: var(--sev-error-bg); color: var(--sev-error); }
.tag.olive { background: var(--warm-sand); color: var(--olive); }

details.raw {
  margin-top: 12px; border-top: 0.5pt dashed var(--border);
  padding-top: 10px;
}
details.raw summary {
  color: var(--stone); cursor: pointer;
  font-size: 10px; letter-spacing: 1pt; text-transform: uppercase;
  list-style: none;
}
details.raw summary::before { content: "▸ "; }
details.raw[open] summary::before { content: "▾ "; }
details.raw pre {
  font-family: var(--mono); font-size: 11px;
  background: var(--parchment);
  border: 0.5pt solid var(--border-soft);
  padding: 10px 12px; border-radius: 3pt;
  overflow-x: auto; margin-top: 8px; color: var(--olive);
}

.empty-state { padding: 60px 20px; text-align: center; color: var(--stone); font-size: 13px; letter-spacing: 0.2pt; }
.empty-state .h { font-size: 18px; color: var(--olive); margin-bottom: 4px; letter-spacing: 0.1pt; }

footer {
  border-top: 0.5pt solid var(--border);
  margin-top: 40px; padding: 18px 44px 30px;
  color: var(--stone); font-size: 10px;
  letter-spacing: 0.6pt; text-transform: uppercase;
}
footer .mark { color: var(--brand); letter-spacing: 0.8pt; }
"""


JS = r"""
const DATA = JSON.parse(document.getElementById('data').textContent);
const ops = DATA.operations || [];
const unresolved = DATA.unresolved || [];
const list = document.getElementById('list');
const $ = id => document.getElementById(id);
let page = 0;
const state = { q: '', method: '', dangerous: false, audit: false, pageSize: 100 };

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
}

function renderOp(op) {
  const cls = [];
  if (op.is_dangerous) cls.push('dangerous');
  else if (op.is_audit) cls.push('audit');
  const flags = [];
  if (op.is_dangerous) flags.push('<span class="tag danger">danger</span>');
  if (op.is_audit) flags.push('<span class="tag warm">audit</span>');
  if (op.auth && op.auth !== 'all') flags.push(`<span class="tag olive">auth: ${esc(op.auth)}</span>`);

  const parts = [];
  parts.push(`<div class="op ${cls.join(' ')}" data-id="${esc(op.id||'')}">`);
  parts.push(`<div class="op-head">
    <span class="id">${esc(op.id||'')}</span>
    <span class="method ${esc((op.method||'').toUpperCase())}">${esc((op.method||'').toUpperCase())}</span>
    <span class="path">${esc(op.path||'')}</span>
    <span class="name">${esc(op.name||'')}${op.name_cn?`<span class="cn">${esc(op.name_cn)}</span>`:''}</span>
    <span class="flags">${flags.join('')}</span>
    <span class="caret">›</span>
  </div>`);

  parts.push(`<div class="op-body"><dl class="kv">`);
  if (op.description) parts.push(`<dt>description</dt><dd>${esc(op.description)}</dd>`);
  if (op.name) parts.push(`<dt>name</dt><dd><code>${esc(op.name)}</code></dd>`);
  if (op.name_cn) parts.push(`<dt>name (zh)</dt><dd>${esc(op.name_cn)}</dd>`);
  if (op.handler && typeof op.handler === 'object') {
    if (op.handler.repo) parts.push(`<dt>repo</dt><dd><code>${esc(op.handler.repo)}</code></dd>`);
    if (op.handler.file) parts.push(`<dt>handler file</dt><dd><code>${esc(op.handler.file)}</code></dd>`);
    if (op.handler.input_type) parts.push(`<dt>input type</dt><dd><code>${esc(op.handler.input_type)}</code></dd>`);
    if (op.handler.output_type) parts.push(`<dt>output type</dt><dd><code>${esc(op.handler.output_type)}</code></dd>`);
    if (op.handler.notes) parts.push(`<dt>notes</dt><dd>${esc(op.handler.notes)}</dd>`);
  }
  parts.push(`</dl>`);
  parts.push(`<details class="raw"><summary>raw JSON</summary><pre>${esc(JSON.stringify(op, null, 2))}</pre></details>`);
  parts.push(`</div></div>`);
  return parts.join('');
}

function renderUnresolved(r) {
  const parts = [];
  parts.push(`<div class="op unresolved" data-id="${esc(r.id||'')}">`);
  parts.push(`<div class="op-head">
    <span class="id">${esc(r.id||'')}</span>
    <span class="method ${esc((r.method||'').toUpperCase())}">${esc((r.method||'').toUpperCase())}</span>
    <span class="path">${esc(r.path||'')}</span>
    <span class="name">${esc(r.reason||'no handler found')}</span>
    <span class="flags"><span class="tag danger">unresolved</span></span>
    <span class="caret">›</span>
  </div>`);
  parts.push(`<div class="op-body"><dl class="kv">`);
  if (r.reason) parts.push(`<dt>reason</dt><dd>${esc(r.reason)}</dd>`);
  parts.push(`</dl>`);
  parts.push(`<details class="raw"><summary>raw JSON</summary><pre>${esc(JSON.stringify(r, null, 2))}</pre></details>`);
  parts.push(`</div></div>`);
  return parts.join('');
}

function filter() {
  const q = state.q.trim().toLowerCase();
  return ops.filter(op => {
    if (state.method && (op.method||'').toUpperCase() !== state.method) return false;
    if (state.dangerous && !op.is_dangerous) return false;
    if (state.audit && !op.is_audit) return false;
    if (q) {
      const blob = [op.id, op.method, op.path, op.name, op.name_cn, op.description,
                    JSON.stringify(op.handler||'')].filter(Boolean).join(' ').toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });
}

function render() {
  const filtered = filter();
  $('count').textContent = `${filtered.length} of ${ops.length} operations`;
  const ps = state.pageSize;
  const pages = Math.max(1, Math.ceil(filtered.length / ps));
  if (page >= pages) page = pages - 1;
  if (page < 0) page = 0;
  $('page').textContent = `${page+1} / ${pages}`;
  $('prev').disabled = page === 0;
  $('next').disabled = page >= pages - 1;
  const slice = filtered.slice(page*ps, page*ps + ps);

  let html = '';
  if (slice.length) {
    html += '<h2 class="section-title">operations</h2>';
    html += slice.map(renderOp).join('');
  } else {
    html += `<div class="empty-state"><div class="h">No operations match</div><div>Loosen the filters to see results.</div></div>`;
  }
  if (unresolved.length) {
    html += `<h2 class="section-title danger">unresolved (${unresolved.length})</h2>`;
    html += unresolved.map(renderUnresolved).join('');
  }
  list.innerHTML = html;
  list.querySelectorAll('.op-head').forEach(h => {
    h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
  });
}

$('search').addEventListener('input', e => { state.q = e.target.value; page = 0; render(); });
$('method').addEventListener('change', e => { state.method = e.target.value; page = 0; render(); });
$('dangerous').addEventListener('change', e => { state.dangerous = e.target.checked; page = 0; render(); });
$('audit').addEventListener('change', e => { state.audit = e.target.checked; page = 0; render(); });
$('pageSize').addEventListener('change', e => { state.pageSize = parseInt(e.target.value); page = 0; render(); });
$('prev').addEventListener('click', () => { page--; render(); });
$('next').addEventListener('click', () => { page++; render(); });
$('expandAll').addEventListener('click', () => list.querySelectorAll('.op').forEach(x => x.classList.add('open')));
$('collapseAll').addEventListener('click', () => list.querySelectorAll('.op').forEach(x => x.classList.remove('open')));

render();
"""


def build_html(doc):
    ops = doc.get('operations') or []
    unresolved = doc.get('unresolved') or []
    stats = doc.get('stats') or {}

    METHOD_RANK = {'GET': 0, 'POST': 1, 'PUT': 2, 'PATCH': 3, 'DELETE': 4}
    def sort_key(op):
        return (op.get('path', ''), METHOD_RANK.get((op.get('method') or '').upper(), 9), op.get('id', ''))
    ops = sorted(ops, key=sort_key)

    method_counts = Counter((op.get('method') or '').upper() for op in ops)
    dangerous_n = sum(1 for op in ops if op.get('is_dangerous'))
    audit_n = sum(1 for op in ops if op.get('is_audit'))

    scope = doc.get('scope') or '—'
    generated_at = doc.get('generated_at') or '—'
    tag_en = doc.get('tag_en') or ''
    tag_zh = doc.get('tag_zh') or ''
    providers = doc.get('providers') or []
    source_registry = doc.get('source_registry') or ''
    sr_commit = doc.get('source_registry_commit') or ''
    docs_path = doc.get('docs_path') or ''

    method_options = '\n'.join(
        f'      <option value="{m}">{m} ({method_counts[m]})</option>'
        for m in sorted(method_counts) if m
    )

    data_payload = {'operations': ops, 'unresolved': unresolved}
    data_json = json.dumps(data_payload, ensure_ascii=False).replace('</', '<\\/')

    parts = ['<!doctype html>', '<html lang="en">', '<head>',
        '  <meta charset="utf-8">',
        '  <meta name="generator" content="Kami">',
        f'  <title>api-review · {html_mod.escape(scope)}</title>',
        '  <style>', CSS, '  </style>', '</head>', '<body>',
        '<header>',
        f'  <div class="eyebrow">api review · scope {html_mod.escape(scope)}</div>',
        f'  <h1>{html_mod.escape(tag_en or scope)}{(" · " + html_mod.escape(tag_zh)) if tag_zh else ""} <span class="subtle">— {html_mod.escape(generated_at)}</span></h1>',
        '  <div class="tallies">',
        f'    <div class="tally"><span class="num">{len(ops)}</span><span class="lbl">operations</span></div>',
    ]
    if dangerous_n:
        parts.append(f'    <div class="tally danger"><span class="num">{dangerous_n}</span><span class="lbl">dangerous</span></div>')
    if audit_n:
        parts.append(f'    <div class="tally audit"><span class="num">{audit_n}</span><span class="lbl">audit-logged</span></div>')
    if unresolved:
        parts.append(f'    <div class="tally unresolved"><span class="num">{len(unresolved)}</span><span class="lbl">unresolved</span></div>')
    parts.append('  </div>')

    meta_bits = []
    if providers:
        meta_bits.append(f'providers <code>{html_mod.escape(", ".join(providers))}</code>')
    if docs_path:
        meta_bits.append(f'docs <code>{html_mod.escape(docs_path)}</code>')
    if source_registry:
        meta_bits.append(f'registry <code>{html_mod.escape(os.path.basename(source_registry))}</code>')
    if sr_commit:
        meta_bits.append(f'@<code>{html_mod.escape(sr_commit[:8] if isinstance(sr_commit, str) else str(sr_commit))}</code>')
    if meta_bits:
        parts.append('  <div class="meta-line">' + '<span class="sep">·</span>'.join(meta_bits) + '</div>')

    parts.extend([
        '  <div class="controls">',
        '    <input type="search" id="search" placeholder="Search path, name, handler…" autocomplete="off">',
        '    <label>method <select id="method"><option value="">all</option>', method_options, '    </select></label>',
        '    <span class="divider"></span>',
        '    <label><input type="checkbox" id="dangerous"> dangerous only</label>',
        '    <label><input type="checkbox" id="audit"> audit-logged only</label>',
        '    <span class="divider"></span>',
        '    <button class="btn" id="expandAll">expand all</button>',
        '    <button class="btn" id="collapseAll">collapse</button>',
        '  </div>',
        '  <div class="pager">',
        '    <span id="count">—</span><span class="spacer"></span>',
        '    <button id="prev">‹ prev</button><span id="page">1 / 1</span><button id="next">next ›</button>',
        '    <label>per page <select id="pageSize"><option>50</option><option selected>100</option><option>250</option><option value="9999">all</option></select></label>',
        '  </div>',
        '</header>',
        '<main><div id="list"></div></main>',
        '<footer><span class="mark">Kami</span> · api-review report · generated by analyze.md</footer>',
        '<script id="data" type="application/json">' + data_json + '</script>',
        '<script>', JS, '</script>',
        '</body></html>',
    ])
    return '\n'.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('findings_path')
    ap.add_argument('--out')
    args = ap.parse_args()
    doc = load_doc(args.findings_path)
    html_text = build_html(doc)
    if args.out:
        out_path = args.out
    else:
        base = args.findings_path
        for ext in ('.yaml', '.yml', '.json'):
            if base.endswith(ext):
                base = base[:-len(ext)]; break
        out_path = base + '.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_text)
    ops_count = len(doc.get('operations') or [])
    unr_count = len(doc.get('unresolved') or [])
    print(f'wrote {out_path} ({os.path.getsize(out_path)/1024:.1f} KB, {ops_count} operations, {unr_count} unresolved)')


if __name__ == '__main__':
    main()
