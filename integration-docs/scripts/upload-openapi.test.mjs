import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  buildOssFilePath,
  listOpenapiJsonFiles,
  uploadOpenapiJsonFiles,
  validateRequiredEnv
} from './upload-openapi.mjs';

test('listOpenapiJsonFiles returns only direct JSON files sorted by name', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'openapi-upload-'));
  const apiReferenceDir = path.join(tempDir, 'api-reference');
  fs.mkdirSync(apiReferenceDir);
  fs.mkdirSync(path.join(apiReferenceDir, 'nested'));
  fs.writeFileSync(path.join(apiReferenceDir, 'rum.openapi.en.json'), '{}\n');
  fs.writeFileSync(path.join(apiReferenceDir, 'on-call.openapi.en.json'), '{}\n');
  fs.writeFileSync(path.join(apiReferenceDir, 'README.md'), '# docs\n');
  fs.writeFileSync(path.join(apiReferenceDir, 'nested', 'ignored.json'), '{}\n');

  assert.deepEqual(listOpenapiJsonFiles(apiReferenceDir), [
    'on-call.openapi.en.json',
    'rum.openapi.en.json'
  ]);
});

test('buildOssFilePath keeps the environment prefix and adds api-reference', () => {
  assert.equal(
    buildOssFilePath('/docs', 'on-call.openapi.en.json'),
    '/docs/api-reference/on-call.openapi.en.json'
  );
  assert.equal(
    buildOssFilePath('/test/docs/', 'openapi.zh.json'),
    '/test/docs/api-reference/openapi.zh.json'
  );
});

test('validateRequiredEnv reports every missing upload credential', () => {
  assert.deepEqual(validateRequiredEnv({}), [
    'CDN_ACCESS_KEY',
    'CDN_SECRET_KEY',
    'CDN_BUCKET',
    'CDN_REGION',
    'CDN_ENDPOINT',
    'CDN_URL',
    'CDN_DIR'
  ]);
});

test('uploadOpenapiJsonFiles uploads every JSON file and refreshes each CDN URL', async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'openapi-upload-'));
  const apiReferenceDir = path.join(tempDir, 'api-reference');
  fs.mkdirSync(apiReferenceDir);
  fs.writeFileSync(path.join(apiReferenceDir, 'openapi.en.json'), '{"openapi":"3.1.0"}\n');
  fs.writeFileSync(path.join(apiReferenceDir, 'openapi.zh.json'), '{"openapi":"3.1.0"}\n');
  fs.writeFileSync(path.join(apiReferenceDir, 'ignored.txt'), 'not json\n');

  const uploaded = [];
  const refreshed = [];
  const env = {
    CDN_ACCESS_KEY: 'access-key',
    CDN_SECRET_KEY: 'secret-key',
    CDN_BUCKET: 'bucket',
    CDN_REGION: 'oss-cn-hangzhou',
    CDN_ENDPOINT: 'bucket.oss-cn-hangzhou.aliyuncs.com',
    CDN_URL: 'https://docs-cdn.flashcat.cloud',
    CDN_DIR: '/docs'
  };
  const ossClient = {
    async put(ossFilePath, localFilePath, options) {
      uploaded.push({ ossFilePath, localFilePath, options });
      return { url: `https://bucket.oss-cn-hangzhou.aliyuncs.com${ossFilePath}` };
    }
  };
  const cdnRuntime = {
    CDN: {
      RefreshObjectCachesRequest: class RefreshObjectCachesRequest {}
    },
    client: {
      async refreshObjectCaches(request) {
        refreshed.push(request.objectPath);
      }
    }
  };

  await uploadOpenapiJsonFiles({ apiReferenceDir, env, ossClient, cdnRuntime });

  assert.deepEqual(
    uploaded.map((item) => item.ossFilePath),
    [
      '/docs/api-reference/openapi.en.json',
      '/docs/api-reference/openapi.zh.json'
    ]
  );
  assert.deepEqual(
    refreshed,
    [
      'https://docs-cdn.flashcat.cloud/docs/api-reference/openapi.en.json',
      'https://docs-cdn.flashcat.cloud/docs/api-reference/openapi.zh.json'
    ]
  );
  assert.equal(uploaded[0].options.headers['Content-Type'], 'application/json; charset=utf-8');
});
