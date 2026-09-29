// Build flashduty-docs.tar.gz: an offline copy of the docs (zh/, en/,
// api-reference/, glossary.md) plus a generated INDEX.md per locale, for
// tools that grep/read Markdown directly instead of calling a search API.
//
// Page selection mirrors scripts/upload.sh (the Meilisearch sync): every
// .md/.mdx file under zh/ or en/, except index pages.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { listOpenapiJsonFiles } from './upload-openapi.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const defaultRepoRoot = path.resolve(packageRoot, '..');
const defaultBuildDir = path.join(defaultRepoRoot, '.docs-bundle-build');
const docsBaseUrl = 'https://docs.flashduty.com';
const locales = ['zh', 'en'];

export function listDocPages(repoRoot, locale) {
  const localeDir = path.join(repoRoot, locale);
  const pages = [];

  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const entryPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(entryPath);
        continue;
      }
      if (!entry.isFile() || !/\.mdx?$/.test(entry.name)) continue;
      if (entry.name === 'index.md' || entry.name === 'index.mdx') continue;
      pages.push(path.relative(repoRoot, entryPath).split(path.sep).join('/'));
    }
  };
  walk(localeDir);

  return pages.sort();
}

export function parseFrontmatter(text) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  const fields = {};
  if (!match) return fields;

  for (const line of match[1].split(/\r?\n/)) {
    const fieldMatch = /^([A-Za-z_]+):\s*(.*)$/.exec(line);
    if (!fieldMatch) continue;
    fields[fieldMatch[1]] = fieldMatch[2].trim().replace(/^["']|["']$/g, '');
  }

  return fields;
}

export function derivePublicUrl(relPath, frontmatter) {
  if (frontmatter.url) return frontmatter.url;
  return `${docsBaseUrl}/${relPath.replace(/\.mdx?$/, '')}`;
}

export function buildIndexLine(relPath, frontmatter) {
  const title = frontmatter.title || '';
  const description = frontmatter.description ? `: ${frontmatter.description}` : '';
  return `- \`${relPath}\` — ${title}${description} ${derivePublicUrl(relPath, frontmatter)}`;
}

export function buildLocaleIndex(repoRoot, locale) {
  const relPaths = listDocPages(repoRoot, locale);
  const lines = relPaths.map((relPath) => {
    const text = fs.readFileSync(path.join(repoRoot, relPath), 'utf8');
    return buildIndexLine(relPath, parseFrontmatter(text));
  });
  return { relPaths, lines };
}

export function buildDocsBundle({
  repoRoot,
  stagingDir,
  outDir,
  apiReferenceDir = path.join(repoRoot, 'api-reference'),
  tarBin = 'tar'
}) {
  fs.rmSync(stagingDir, { recursive: true, force: true });
  fs.mkdirSync(stagingDir, { recursive: true });
  fs.mkdirSync(outDir, { recursive: true });

  const pageCounts = {};
  for (const locale of locales) {
    const { relPaths, lines } = buildLocaleIndex(repoRoot, locale);
    for (const relPath of relPaths) {
      const dest = path.join(stagingDir, relPath);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(path.join(repoRoot, relPath), dest);
    }
    const header = `# Flashduty docs index (${locale})\n\nOne line per page: file path — title: description public URL.\n\n`;
    fs.writeFileSync(path.join(stagingDir, locale, 'INDEX.md'), `${header}${lines.join('\n')}\n`);
    pageCounts[locale] = relPaths.length;
  }

  const apiReferenceStagingDir = path.join(stagingDir, 'api-reference');
  fs.mkdirSync(apiReferenceStagingDir, { recursive: true });
  const apiReferenceFiles = listOpenapiJsonFiles(apiReferenceDir);
  for (const file of apiReferenceFiles) {
    fs.copyFileSync(path.join(apiReferenceDir, file), path.join(apiReferenceStagingDir, file));
  }

  fs.copyFileSync(path.join(repoRoot, 'glossary.md'), path.join(stagingDir, 'glossary.md'));

  const tarPath = path.join(outDir, 'flashduty-docs.tar.gz');
  execFileSync(tarBin, ['-czf', tarPath, '-C', stagingDir, 'zh', 'en', 'api-reference', 'glossary.md']);

  return {
    tarPath,
    size: fs.statSync(tarPath).size,
    zhPages: pageCounts.zh,
    enPages: pageCounts.en,
    apiReferenceFiles: apiReferenceFiles.length
  };
}

async function main() {
  const result = buildDocsBundle({
    repoRoot: defaultRepoRoot,
    stagingDir: path.join(defaultBuildDir, 'staging'),
    outDir: defaultBuildDir
  });
  console.log(
    `Built ${result.tarPath} (${result.size} bytes): `
    + `zh=${result.zhPages} en=${result.enPages} api-reference=${result.apiReferenceFiles}`
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
