import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { docMap, optionalMissingKeys } from '../src/doc-map.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..');
const distRoot = path.join(packageRoot, 'dist');
const docsBaseUrl = 'https://docs.flashcat.cloud';

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

function removeHiddenBlocks(content) {
  return content.replace(/<div\b(?=[^>]*\bclass(?:Name)?=["'][^"']*\bhide\b[^"']*["'])[^>]*>[\s\S]*?<\/div>/g, '\n');
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

function convertAccordions(content) {
  return content.replace(/<Accordion\b([^>]*)>([\s\S]*?)<\/Accordion>/g, (_tag, attrs, body) => {
    const title = getAttr(attrs, 'title') || 'Details';
    return `\n\n<details>\n<summary>${title}</summary>\n\n${body.trim()}\n\n</details>\n\n`;
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

function mdxToMarkdown(content) {
  let output = removeHiddenBlocks(stripFrontmatter(content));

  output = convertDirectiveContainers(convertAccordions(output))
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

  output = output
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
    .replace(/^\s*---\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

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
