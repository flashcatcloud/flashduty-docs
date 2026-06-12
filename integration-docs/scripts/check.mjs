import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { docMap, optionalMissingKeys } from '../src/doc-map.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
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
  /^:{3,}/m
];

async function loadDocs(locale) {
  const file = path.join(distRoot, 'esm', `${locale}.js`);
  if (!fs.existsSync(file)) {
    throw new Error(`Missing build output: ${file}`);
  }
  const mod = await import(`${pathToFileURL(file).href}?t=${Date.now()}`);
  return mod.default;
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
    for (const pattern of forbiddenPatterns) {
      if (pattern.test(value)) {
        errors.push(`${locale}: ${key} still contains ${pattern}`);
      }
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
