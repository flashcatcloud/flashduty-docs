import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import test from 'node:test';

import {
  buildDocsBundle,
  buildIndexLine,
  derivePublicUrl,
  listDocPages,
  parseFrontmatter
} from './build-docs-bundle.mjs';

test('parseFrontmatter reads quoted and unquoted fields', () => {
  const text = [
    '---',
    'title: "飞书/Lark"',
    'description: "通过集成飞书自建应用"',
    'url: https://status.flashcat.cloud',
    '---',
    '',
    '# body'
  ].join('\n');

  assert.deepEqual(parseFrontmatter(text), {
    title: '飞书/Lark',
    description: '通过集成飞书自建应用',
    url: 'https://status.flashcat.cloud'
  });
});

test('parseFrontmatter returns no fields without a frontmatter block', () => {
  assert.deepEqual(parseFrontmatter('# just a heading\n'), {});
});

test('derivePublicUrl prefers frontmatter url, else derives from the path', () => {
  assert.equal(
    derivePublicUrl('zh/on-call/integration/instant-messaging/lark.mdx', {}),
    'https://docs.flashduty.com/zh/on-call/integration/instant-messaging/lark'
  );
  assert.equal(
    derivePublicUrl('zh/stsatuspage.mdx', { url: 'https://status.flashcat.cloud' }),
    'https://status.flashcat.cloud'
  );
});

test('buildIndexLine omits the description separator when there is none', () => {
  assert.equal(
    buildIndexLine('zh/foo.mdx', { title: '标题', description: '描述' }),
    '- `zh/foo.mdx` — 标题: 描述 https://docs.flashduty.com/zh/foo'
  );
  assert.equal(
    buildIndexLine('zh/foo.mdx', { title: '标题' }),
    '- `zh/foo.mdx` — 标题 https://docs.flashduty.com/zh/foo'
  );
});

test('listDocPages selects only .md/.mdx pages, excludes index pages and media', () => {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'docs-bundle-pages-'));
  fs.mkdirSync(path.join(repoRoot, 'zh', 'on-call'), { recursive: true });
  fs.writeFileSync(path.join(repoRoot, 'zh', 'a.mdx'), '# a\n');
  fs.writeFileSync(path.join(repoRoot, 'zh', 'on-call', 'b.md'), '# b\n');
  fs.writeFileSync(path.join(repoRoot, 'zh', 'index.mdx'), '# index\n');
  fs.writeFileSync(path.join(repoRoot, 'zh', 'on-call', 'diagram.png'), 'not a page');
  fs.writeFileSync(path.join(repoRoot, 'zh', '.DS_Store'), 'junk');

  assert.deepEqual(listDocPages(repoRoot, 'zh'), ['zh/a.mdx', 'zh/on-call/b.md']);
});

function hasTar() {
  try {
    execFileSync('tar', ['--version']);
    return true;
  } catch {
    return false;
  }
}

test('buildDocsBundle produces the fixed archive layout with no media files', { skip: !hasTar() }, () => {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'docs-bundle-repo-'));
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'docs-bundle-work-'));

  fs.mkdirSync(path.join(repoRoot, 'zh', 'on-call'), { recursive: true });
  fs.mkdirSync(path.join(repoRoot, 'en'), { recursive: true });
  fs.mkdirSync(path.join(repoRoot, 'api-reference'), { recursive: true });

  fs.writeFileSync(
    path.join(repoRoot, 'zh', 'on-call', 'lark.mdx'),
    '---\ntitle: "飞书/Lark"\ndescription: "接入飞书"\n---\n\nbody\n'
  );
  fs.writeFileSync(path.join(repoRoot, 'zh', 'on-call', 'diagram.png'), 'not a page');
  fs.writeFileSync(
    path.join(repoRoot, 'en', 'lark.mdx'),
    '---\ntitle: "Lark"\n---\n\nbody\n'
  );
  fs.writeFileSync(path.join(repoRoot, 'api-reference', 'on-call.openapi.zh.json'), '{}\n');
  fs.writeFileSync(path.join(repoRoot, 'api-reference', 'README.md'), 'not json\n');
  fs.writeFileSync(path.join(repoRoot, 'glossary.md'), '# glossary\n');

  const stagingDir = path.join(work, 'staging');
  const outDir = path.join(work, 'out');
  const result = buildDocsBundle({ repoRoot, stagingDir, outDir });

  assert.equal(result.zhPages, 1);
  assert.equal(result.enPages, 1);
  assert.equal(result.apiReferenceFiles, 1);
  assert.ok(result.size > 0);

  const extractDir = path.join(work, 'extract');
  fs.mkdirSync(extractDir, { recursive: true });
  execFileSync('tar', ['-xzf', result.tarPath, '-C', extractDir]);

  assert.deepEqual(fs.readdirSync(extractDir).sort(), ['api-reference', 'en', 'glossary.md', 'zh']);
  assert.deepEqual(fs.readdirSync(path.join(extractDir, 'api-reference')), ['on-call.openapi.zh.json']);
  assert.ok(fs.existsSync(path.join(extractDir, 'zh', 'INDEX.md')));
  assert.ok(fs.existsSync(path.join(extractDir, 'en', 'INDEX.md')));
  assert.ok(!fs.existsSync(path.join(extractDir, 'zh', 'on-call', 'diagram.png')));

  const zhIndex = fs.readFileSync(path.join(extractDir, 'zh', 'INDEX.md'), 'utf8');
  assert.match(zhIndex, /`zh\/on-call\/lark\.mdx` — 飞书\/Lark: 接入飞书 https:\/\/docs\.flashduty\.com\/zh\/on-call\/lark/);
});
