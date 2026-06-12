import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { docMap, optionalMissingKeys } from '../src/doc-map.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..');
const distRoot = path.join(packageRoot, 'dist');

const expectedKeys = Object.keys(docMap);
const forbiddenPatterns = [
  /<Steps\b/,
  /<Step\b/,
  /<Tabs\b/,
  /<Tab\b/,
  /<Accordion\b/,
  /<AccordionGroup\b/,
  /<Card\b/,
  /<Note\b/,
  /<Tip\b/,
  /<Warning\b/,
  /<Video\b/,
  /{\s*\/\*/,
  /^:{3,}/m,
  /^---$/m,
  /class(?:Name)?=["'][^"']*\bhide\b[^"']*["']/,
  /]\(\/(?:zh|en)\//,
  /href=["']\/(?:zh|en)\//,
  /api\.flascat\.cloud/
];

async function loadDocs(locale) {
  const file = path.join(distRoot, 'esm', `${locale}.js`);
  if (!fs.existsSync(file)) {
    throw new Error(`Missing build output: ${file}`);
  }
  const mod = await import(`${pathToFileURL(file).href}?t=${Date.now()}`);
  return mod.default;
}

function getSourceDescription(locale, entry) {
  const source = typeof entry === 'string' ? entry : entry[locale];
  const absolute = entry?.legacy
    ? path.resolve(packageRoot, source)
    : path.resolve(repoRoot, locale, source);
  if (!fs.existsSync(absolute)) return '';

  const raw = fs.readFileSync(absolute, 'utf8');
  const frontmatter = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatter) return '';

  const match = frontmatter[1].match(/^description:\s*(?:"([^"]*)"|'([^']*)'|(.+?))\s*$/m);
  return (match?.[1] || match?.[2] || match?.[3] || '').trim();
}

function findIndentedMarkdown(value) {
  const lines = value.split('\n');
  const offenders = [];
  let inFence = false;

  lines.forEach((line, index) => {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      return;
    }
    if (!inFence && /^ {4,}\S/.test(line)) {
      offenders.push(index + 1);
    }
  });

  return offenders;
}

function findMarkdownTables(value) {
  const lines = value.split('\n');
  const offenders = [];
  let inFence = false;

  lines.forEach((line, index) => {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      return;
    }
    const next = lines[index + 1]?.trim() || '';
    if (!inFence && line.trim().includes('|') && /^(\|?\s*:?-{3,}:?\s*){2,}\|?$/.test(next)) {
      offenders.push(index + 1);
    }
  });

  return offenders;
}

function checkLocale(locale, docs) {
  const errors = [];
  const keys = Object.keys(docs);
  for (const key of expectedKeys) {
    if (!docs[key]) errors.push(`${locale}: missing key ${key}`);
  }
  for (const key of keys) {
    if (!expectedKeys.includes(key) && !optionalMissingKeys.includes(key)) {
      errors.push(`${locale}: unexpected key ${key}`);
    }
  }
  for (const [key, value] of Object.entries(docs)) {
    const firstLine = value.split('\n').find((line) => line.trim()) || '';
    if (getSourceDescription(locale, docMap[key]) && /^#{1,6}\s/.test(firstLine.trim())) {
      errors.push(`${locale}: ${key} starts with a heading before its description`);
    }

    for (const pattern of forbiddenPatterns) {
      if (pattern.test(value)) {
        errors.push(`${locale}: ${key} still contains ${pattern}`);
      }
    }
    const indentedLines = findIndentedMarkdown(value);
    if (indentedLines.length > 0) {
      errors.push(`${locale}: ${key} has indented Markdown outside code fences at lines ${indentedLines.slice(0, 5).join(', ')}`);
    }

    const tableLines = findMarkdownTables(value);
    if (tableLines.length > 0) {
      errors.push(`${locale}: ${key} still has Markdown tables at lines ${tableLines.slice(0, 5).join(', ')}`);
    }
  }
  return errors;
}

const zh = await loadDocs('zh');
const en = await loadDocs('en');
const errors = [...checkLocale('zh', zh), ...checkLocale('en', en)];

if (errors.length > 0) {
  console.error(errors.join('\n'));
  process.exit(1);
}

console.log(`Compatibility check passed: ${expectedKeys.length} keys for zh/en.`);
