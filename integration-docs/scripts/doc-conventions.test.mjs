import assert from 'node:assert/strict';
import test from 'node:test';

import {
  findPlaceholderErrors,
  findStepErrors,
  findTildeErrors,
  formatStepHeading,
  normalizeStepHeadings
} from './doc-conventions.mjs';

test('formatStepHeading uses the locale separator the console matches on', () => {
  assert.equal(formatStepHeading('zh', 2, '配置'), '### 步骤 2：配置');
  assert.equal(formatStepHeading('en', 2, 'Configure'), '### Step 2: Configure');
});

test('normalizeStepHeadings rewrites heading levels and separators', () => {
  const zh = ['#### 步骤 1 创建应用', '', '正文', '', '### 步骤 2、授权'].join('\n');
  assert.equal(normalizeStepHeadings(zh, 'zh'), ['### 步骤 1：创建应用', '', '正文', '', '### 步骤 2：授权'].join('\n'));

  const en = ['#### Step 1: Create app', '', '### Step 2: Authorize'].join('\n');
  assert.equal(normalizeStepHeadings(en, 'en'), ['### Step 1: Create app', '', '### Step 2: Authorize'].join('\n'));
});

test('normalizeStepHeadings promotes bold step labels', () => {
  assert.equal(normalizeStepHeadings('**步骤 1：配置 Webhook**\n\n**步骤 2：配置策略**', 'zh'), '### 步骤 1：配置 Webhook\n\n### 步骤 2：配置策略');
});

test('normalizeStepHeadings leaves docs whose step numbers repeat or skip', () => {
  const alternatives = ['#### 步骤 1 云版本', '#### 步骤 2 授权', '#### 步骤 1 私有化版本'].join('\n');
  assert.equal(normalizeStepHeadings(alternatives, 'zh'), alternatives);

  const gap = '### Step 1: A\n### Step 3: C';
  assert.equal(normalizeStepHeadings(gap, 'en'), gap);
});

test('normalizeStepHeadings ignores step-like lines inside code fences and docs without steps', () => {
  const fenced = '```\n### Step 1: not a heading\n```';
  assert.equal(normalizeStepHeadings(fenced, 'en'), fenced);
  assert.equal(normalizeStepHeadings('### Setup\n\ntext', 'en'), '### Setup\n\ntext');
});

test('findStepErrors accepts a 1..N sequence and docs without steps', () => {
  assert.deepEqual(findStepErrors('### Step 1: A\n\n### Step 2: B'), []);
  assert.deepEqual(findStepErrors('### 步骤 1：甲\n\n### 步骤 2：乙'), []);
  assert.deepEqual(findStepErrors('### Tab title\n\ntext'), []);
});

test('findStepErrors reports gaps, duplicates and leftover step labels', () => {
  assert.match(findStepErrors('### Step 1: A\n### Step 3: C')[0], /1, 3/);
  assert.match(findStepErrors('### 步骤 1：甲\n### 步骤 1：乙')[0], /1, 1/);
  assert.match(findStepErrors('### Step 1: A\n\n**Step 2: B**')[0], /lines 3/);
});

test('findPlaceholderErrors accepts canonical tokens and unrelated braces', () => {
  const doc = [
    '```yaml',
    "url: '{integration_url}'",
    '```',
    '```bash',
    "curl '{api_host}/event/push/alert/standard?integration_key={integration_key}'",
    'URL="${address}/event/push/alert/standard?integration_key=${INTEGRATION_KEY}"',
    'echo "${FLASHDUTY_PUSH_URL}" {{ template }}',
    '```'
  ].join('\n');
  assert.deepEqual(findPlaceholderErrors(doc), []);
});

test('findPlaceholderErrors rejects old spellings and hard-coded push URLs inside code blocks', () => {
  for (const line of [
    "url: '<push URL>'",
    'url: <Flashduty 推送地址>',
    'key: <integration key>',
    'key: <集成密钥>',
    'key: YOUR_INTEGRATION_KEY',
    'url: {您的推送地址}',
    'url: {push_url}',
    'url: https://api.flashcat.cloud/event/push/alert/standard?integration_key={integration_key}'
  ]) {
    assert.equal(findPlaceholderErrors(`\`\`\`\n${line}\n\`\`\``).length, 1, line);
  }
});

test('findPlaceholderErrors rejects a token preceded by $ anywhere in the doc', () => {
  for (const token of ['integration_url', 'integration_key', 'api_host']) {
    assert.equal(findPlaceholderErrors(`URL="\${${token}}/x"`).length, 1, token);
    assert.equal(findPlaceholderErrors(`\`\`\`\nURL="\${${token}}/x"\n\`\`\``).length, 1, token);
  }
  assert.deepEqual(findPlaceholderErrors('```\nURL="${INTEGRATION_KEY}"\n```'), []);
});

test('findPlaceholderErrors only looks inside code blocks', () => {
  assert.deepEqual(findPlaceholderErrors('形如 `<push URL>`，或 <span class="integration_url">推送地址</span>'), []);
});

test('findTildeErrors flags ranges written with ~ in prose and headings', () => {
  assert.equal(findTildeErrors('适用于 5.x~6.x\n或 3.x~4.x').length, 2);
  assert.equal(findTildeErrors('### Version 5.x~6.x').length, 1);
  assert.equal(findTildeErrors('![5.x~6.x](https://example.com/a.png)').length, 1);
});

test('findTildeErrors accepts en dashes, code, and spaced or leading tildes', () => {
  assert.deepEqual(findTildeErrors('适用于 5.x–6.x，路径 ~/bin，`3.x~6.x`'), []);
  assert.deepEqual(findTildeErrors('```\nversion 3.x~6.x\n```\n~~~text\na~b\n~~~'), []);
});
