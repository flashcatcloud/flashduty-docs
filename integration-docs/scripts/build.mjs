import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { docMap, optionalMissingKeys } from '../src/doc-map.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..');
const distRoot = path.join(packageRoot, 'dist');
const docsBaseUrl = 'https://docs.flashduty.com';

function readSource(locale, entry) {
  const source = typeof entry === 'string' ? entry : entry[locale];
  const absolute = entry?.legacy
    ? path.resolve(packageRoot, source)
    : path.resolve(repoRoot, locale, source);
  if (!fs.existsSync(absolute)) {
    throw new Error(`Missing ${locale} source: ${source}`);
  }
  return fs.readFileSync(absolute, 'utf8');
}

function stripFrontmatter(content) {
  return content.replace(/^---\n[\s\S]*?\n---\n?/, '');
}

function getFrontmatterAttr(content, name) {
  const frontmatter = content.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatter) return '';
  const match = frontmatter[1].match(new RegExp(`^${name}:\\s*(?:"([^"]*)"|'([^']*)'|(.+?))\\s*$`, 'm'));
  return (match?.[1] || match?.[2] || match?.[3] || '').trim();
}

// The leading `^[ \t]*` matters when the block is indented inside a list item:
// without it the indentation survives as a stray whitespace-only line, which
// turns the surrounding tight list loose. Blocks at column zero are unaffected.
function removeHiddenBlocks(content) {
  return content.replace(
    /^[ \t]*<div\b(?=[^>]*\bclass(?:Name)?=["'][^"']*\bhide\b[^"']*["'])[^>]*>[\s\S]*?<\/div>/gm,
    '\n',
  );
}

function convertAnchorSpans(content) {
  return content
    .replace(/<span\b([^>]*)>\s*<\/span>/g, (_tag, attrs) => {
      const id = getAttr(attrs, 'id');
      return id ? `<a id="${id}"></a>` : '';
    })
    .replace(/<span\b([^>]*)>/g, (_tag, attrs) => {
      const id = getAttr(attrs, 'id');
      return id ? `<a id="${id}"></a>` : '';
    })
    .replace(/<\/span>/g, '');
}

function getAttr(attrs, name) {
  const match = attrs.match(new RegExp(`${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|{\\s*["']([^"']*)["']\\s*})`));
  return match?.[1] || match?.[2] || match?.[3] || '';
}

function directiveLabel(kind) {
  const labels = {
    caution: 'Caution',
    danger: 'Danger',
    info: 'Info',
    note: 'Note',
    success: 'Success',
    tip: 'Tip',
    tips: 'Tip',
    warning: 'Warning'
  };
  return labels[kind?.toLowerCase()] || kind || 'Note';
}

function absoluteDocsUrl(url) {
  if (!url) return url;
  if (/^\/(?:zh|en)\//.test(url)) return `${docsBaseUrl}${url}`;
  return url;
}

function stripComponentIndent(content) {
  const lines = content.trim().split('\n');
  const nonEmpty = lines.filter((line) => line.trim());
  const minIndent = nonEmpty.reduce((min, line) => {
    const indent = line.match(/^\s*/)[0].length;
    return Math.min(min, indent);
  }, Infinity);
  const trimBy = Number.isFinite(minIndent) ? minIndent : 0;
  return lines.map((line) => line.slice(Math.min(trimBy, line.match(/^\s*/)[0].length))).join('\n').trim();
}

function blockquoteContent(content) {
  const body = stripComponentIndent(content);
  if (!body) return '';
  return body
    .split('\n')
    .map((line) => (line.trim() ? `> ${line}` : '>'))
    .join('\n');
}

function convertAccordions(content) {
  return content.replace(/<Accordion\b([^>]*)>([\s\S]*?)<\/Accordion>/g, (_tag, attrs, body) => {
    const title = getAttr(attrs, 'title') || 'Details';
    return `\n\n<details>\n<summary>${title}</summary>\n\n${stripComponentIndent(body)}\n\n</details>\n\n`;
  });
}

function convertCards(content) {
  return content.replace(/<Card\b([^>]*)>([\s\S]*?)<\/Card>/g, (_tag, attrs, body) => {
    const title = getAttr(attrs, 'title');
    const href = absoluteDocsUrl(getAttr(attrs, 'href'));
    const cardBody = stripComponentIndent(body);
    const label = href && title ? `[${title}](${href})` : title;
    if (!label && !cardBody) return '\n';
    if (!label) return `\n${cardBody}\n`;
    if (!cardBody) return `\n- ${label}\n`;
    return `\n- ${label}\n${cardBody}\n`;
  });
}

function convertCallouts(content) {
  return content.replace(/<(Note|Tip|Warning|Info|Check)\b[^>]*>([\s\S]*?)<\/\1>/g, (_tag, _kind, body) => {
    const quote = blockquoteContent(body);
    return quote ? `\n\n${quote}\n\n` : '\n';
  });
}

function convertDirectiveContainers(content) {
  const lines = content.split('\n');
  const result = [];
  let directive = null;

  for (const line of lines) {
    const marker = line.match(/^:{3,}\s*([A-Za-z][\w-]*)?\s*(.*?)\s*$/);
    if (marker) {
      const kind = marker[1];
      if (kind) {
        const title = marker[2];
        directive = { kind, title };
        const label = title || directiveLabel(kind);
        result.push(`> **${label}:**`);
      } else {
        directive = null;
      }
      continue;
    }

    if (directive) {
      result.push(line.trim() ? `> ${line}` : '>');
    } else {
      result.push(line);
    }
  }

  return result.join('\n');
}

function normalizeMarkdownIndentation(content) {
  const lines = content.split('\n');
  const result = [];
  let inFence = false;
  let fenceIndent = '';

  for (const line of lines) {
    const trimmed = line.trimStart();
    if (trimmed.startsWith('```')) {
      if (!inFence) {
        fenceIndent = line.match(/^\s*/)[0];
        inFence = true;
      } else {
        inFence = false;
        fenceIndent = '';
      }
      result.push(trimmed);
      continue;
    }

    if (inFence) {
      result.push(fenceIndent && line.startsWith(fenceIndent) ? line.slice(fenceIndent.length) : line);
      continue;
    }

    if (/^ {2,}([-*+] |\d+\. )/.test(line)) {
      result.push(line);
      continue;
    }

    result.push(line.match(/^ {2,}\S/) ? trimmed : line);
  }

  return result.join('\n');
}

function splitTableRow(line) {
  return line.trim().replace(/^>\s*/, '').replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
}

function isTableSeparator(line) {
  const cells = splitTableRow(line);
  return cells.length >= 2 && cells.every((cell) => /^:?-+:?$/.test(cell));
}

function isTableRow(line) {
  const trimmed = line.trim().replace(/^>\s*/, '');
  return trimmed.includes('|') && !trimmed.startsWith('```');
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderTableCell(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
}

function markdownTableToHtml(rows) {
  const header = splitTableRow(rows[0]);
  const body = rows.slice(2).map(splitTableRow);
  const headHtml = header.map((cell) => `<th>${renderTableCell(cell)}</th>`).join('');
  const bodyHtml = body
    .map((row) => `<tr>${row.map((cell) => `<td>${renderTableCell(cell)}</td>`).join('')}</tr>`)
    .join('\n');
  return `<table>\n<thead>\n<tr>${headHtml}</tr>\n</thead>\n<tbody>\n${bodyHtml}\n</tbody>\n</table>`;
}

function convertMarkdownTables(content) {
  const lines = content.split('\n');
  const result = [];
  let inFence = false;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      result.push(line);
      continue;
    }

    if (!inFence && isTableRow(line) && isTableSeparator(lines[index + 1] || '')) {
      const tableRows = [line, lines[index + 1]];
      index += 2;
      while (index < lines.length && isTableRow(lines[index]) && lines[index].trim()) {
        tableRows.push(lines[index]);
        index += 1;
      }
      index -= 1;
      result.push(markdownTableToHtml(tableRows));
      continue;
    }

    result.push(line);
  }

  return result.join('\n');
}

function shouldPrefixDescription(output, description) {
  if (!description) return false;
  if (output.includes(description)) return false;
  const first = output.split('\n').find((line) => line.trim()) || '';
  return /^(#{1,6}\s|>|<details\b)/.test(first.trim());
}

function mdxToMarkdown(content) {
  const description = getFrontmatterAttr(content, 'description');
  let output = convertAnchorSpans(removeHiddenBlocks(stripFrontmatter(content)));

  output = convertDirectiveContainers(convertCallouts(convertCards(convertAccordions(output))))
    // Counterpart to removeHiddenBlocks: a `{/* console: ... */}` block is an MDX
    // comment, so the docs site renders nothing, while the console gets its
    // contents. Use it for text that only makes sense inside the product, such
    // as a value the console substitutes per deployment. The opening and closing
    // lines are consumed whole so the captured lines land at the same
    // indentation they were written at, with no blank line on either side.
    // Must run before the generic comment strip below, which would discard it.
    .replace(/^[ \t]*{[ \t]*\/\*[ \t]*console:[ \t]*\r?\n([\s\S]*?)\r?\n[ \t]*\*\/[ \t]*}[ \t]*(\r?\n)/gm, '$1$2')
    .replace(/{\s*\/\*[\s\S]*?\*\/\s*}/g, '')
    .replace(/^\s*import\s+.*$/gm, '')
    .replace(/^\s*export\s+.*$/gm, '')
    .replace(/<Step\b([^>]*)>/g, (_tag, attrs) => `\n\n### ${getAttr(attrs, 'title') || 'Step'}\n\n`)
    .replace(/<\/Step>/g, '\n')
    .replace(/<Tab\b([^>]*)>/g, (_tag, attrs) => `\n\n### ${getAttr(attrs, 'title') || 'Tab'}\n\n`)
    .replace(/<\/Tab>/g, '\n')
    .replace(/<Card\b([^>]*)\/>/g, (_tag, attrs) => {
      const title = getAttr(attrs, 'title');
      const href = absoluteDocsUrl(getAttr(attrs, 'href'));
      if (title && href) return `\n- [${title}](${href})\n`;
      if (title) return `\n- ${title}\n`;
      return '\n';
    })
    .replace(/<Card\b([^>]*)>/g, (_tag, attrs) => {
      const title = getAttr(attrs, 'title');
      const href = absoluteDocsUrl(getAttr(attrs, 'href'));
      if (title && href) return `\n\n### [${title}](${href})\n\n`;
      if (title) return `\n\n### ${title}\n\n`;
      return '\n';
    })
    .replace(/<\/Card>/g, '\n')
    .replace(/<(Note|Tip|Warning|Info|Check|Warning)\b[^>]*>/g, '\n\n> ')
    .replace(/<\/(Note|Tip|Warning|Info|Check|Warning)>/g, '\n')
    .replace(/<\/?(Steps|Tabs|AccordionGroup|CardGroup|CodeGroup|Frame)\b[^>]*>/g, '\n');

  output = convertMarkdownTables(normalizeMarkdownIndentation(output))
    .replace(/<img\b([^>]*)>/g, (_tag, attrs) => {
      const alt = getAttr(attrs, 'alt') || 'image';
      const src = getAttr(attrs, 'src');
      return src ? `![${alt}](${src})` : '';
    })
    .replace(/]\(\/(zh|en)\//g, `](${docsBaseUrl}/$1/`)
    .replace(/href=(["'])\/(zh|en)\//g, `href=$1${docsBaseUrl}/$2/`)
    .replace(/api\.flascat\.cloud/g, 'api.flashcat.cloud')
    .replace(/<br\s*\/?>/g, '\n')
    .replace(/<\/?span\b[^>]*>/g, '')
    .replace(/<\/?div\b[^>]*>/g, '\n')
    .replace(/^[ \t]+$/gm, '')
    .replace(/^\s*---\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  if (shouldPrefixDescription(output, description)) {
    output = `${description}\n\n${output}`;
  }

  return `${output}\n`;
}

function buildLocale(locale) {
  const docs = {};
  const legacyKeys = [];

  for (const [key, entry] of Object.entries(docMap)) {
    const raw = readSource(locale, entry);
    docs[key] = mdxToMarkdown(raw);
    if (entry?.legacy) legacyKeys.push(key);
  }

  return { docs, legacyKeys };
}

function writeLocale(locale, globalName, docs) {
  fs.mkdirSync(path.join(distRoot, 'esm'), { recursive: true });
  fs.mkdirSync(path.join(distRoot, 'iife'), { recursive: true });

  const json = JSON.stringify(docs, null, 2);
  fs.writeFileSync(
    path.join(distRoot, 'esm', `${locale}.js`),
    `const docs = ${json};\nexport default docs;\n`,
    'utf8'
  );
  fs.writeFileSync(
    path.join(distRoot, 'iife', `${locale}.js`),
    `(function (global) {\n  const docs = ${json};\n  global.${globalName} = docs;\n})(window);\n`,
    'utf8'
  );
}

function writeTypes() {
  fs.writeFileSync(
    path.join(distRoot, 'index.d.ts'),
    'declare const docs: Record<string, string>;\nexport default docs;\n',
    'utf8'
  );
}

fs.rmSync(distRoot, { recursive: true, force: true });

const zh = buildLocale('zh');
const en = buildLocale('en');
writeLocale('zh', 'FlashDocsZh', zh.docs);
writeLocale('en', 'FlashDocsEn', en.docs);
writeTypes();

const keys = Object.keys(docMap);
const report = {
  generatedAt: new Date().toISOString(),
  totalKeys: keys.length,
  keys,
  optionalMissingKeys,
  legacyFallbackKeys: [...new Set([...zh.legacyKeys, ...en.legacyKeys])]
};

fs.writeFileSync(path.join(distRoot, 'build-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');

console.log(`Built ${keys.length} documentation keys for zh/en.`);
if (report.legacyFallbackKeys.length > 0) {
  console.log(`Legacy fallback keys: ${report.legacyFallbackKeys.join(', ')}`);
}
