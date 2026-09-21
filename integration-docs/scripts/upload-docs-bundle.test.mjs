import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { buildOssFilePath, uploadDocsBundle } from './upload-docs-bundle.mjs';

test('buildOssFilePath appends the tarball name under the environment prefix', () => {
  assert.equal(buildOssFilePath('/docs'), '/docs/flashduty-docs.tar.gz');
  assert.equal(buildOssFilePath('/test/docs/'), '/test/docs/flashduty-docs.tar.gz');
});

test('uploadDocsBundle reports every missing env var and never touches OSS', async () => {
  await assert.rejects(
    () => uploadDocsBundle({ tarPath: '/nonexistent.tar.gz', env: {} }),
    /Missing required env vars/
  );
});

test('uploadDocsBundle rejects a tarball that was never built', async () => {
  const env = {
    CDN_ACCESS_KEY: 'access-key',
    CDN_SECRET_KEY: 'secret-key',
    CDN_BUCKET: 'bucket',
    CDN_REGION: 'oss-cn-hangzhou',
    CDN_ENDPOINT: 'bucket.oss-cn-hangzhou.aliyuncs.com',
    CDN_URL: 'https://docs-cdn.flashcat.cloud',
    CDN_DIR: '/docs'
  };

  await assert.rejects(
    () => uploadDocsBundle({ tarPath: '/nonexistent.tar.gz', env }),
    /Docs bundle tarball does not exist/
  );
});

test('uploadDocsBundle uploads the tarball with gzip headers and refreshes the CDN', async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'docs-bundle-upload-'));
  const tarPath = path.join(tempDir, 'flashduty-docs.tar.gz');
  fs.writeFileSync(tarPath, 'fake tarball');

  const env = {
    CDN_ACCESS_KEY: 'access-key',
    CDN_SECRET_KEY: 'secret-key',
    CDN_BUCKET: 'bucket',
    CDN_REGION: 'oss-cn-hangzhou',
    CDN_ENDPOINT: 'bucket.oss-cn-hangzhou.aliyuncs.com',
    CDN_URL: 'https://docs-cdn.flashcat.cloud',
    CDN_DIR: '/docs'
  };

  const uploaded = [];
  const refreshed = [];
  const ossClient = {
    async put(ossFilePath, localFilePath, options) {
      uploaded.push({ ossFilePath, localFilePath, options });
      return { url: `https://bucket.oss-cn-hangzhou.aliyuncs.com${ossFilePath}` };
    }
  };
  const cdnRuntime = {
    CDN: { RefreshObjectCachesRequest: class RefreshObjectCachesRequest {} },
    client: {
      async refreshObjectCaches(request) {
        refreshed.push(request.objectPath);
      }
    }
  };

  const cdnUrl = await uploadDocsBundle({ tarPath, env, ossClient, cdnRuntime });

  assert.equal(cdnUrl, 'https://docs-cdn.flashcat.cloud/docs/flashduty-docs.tar.gz');
  assert.deepEqual(uploaded.map((item) => item.ossFilePath), ['/docs/flashduty-docs.tar.gz']);
  assert.equal(uploaded[0].localFilePath, tarPath);
  assert.equal(uploaded[0].options.headers['Content-Type'], 'application/gzip');
  assert.equal(uploaded[0].options.headers['Cache-Control'], 'public, max-age=300');
  assert.equal(uploaded[0].options.timeout, 10 * 60 * 1000);
  assert.deepEqual(refreshed, ['https://docs-cdn.flashcat.cloud/docs/flashduty-docs.tar.gz']);
});
