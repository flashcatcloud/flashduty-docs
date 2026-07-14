import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCdnUrl } from './cdn-url.mjs';

test('buildCdnUrl replaces the OSS origin when CDN_URL includes protocol', () => {
  assert.equal(
    buildCdnUrl(
      'http://flashcat-docs.oss-cn-hangzhou.aliyuncs.com/test/docs/en.js',
      'flashcat-docs.oss-cn-hangzhou.aliyuncs.com',
      'https://docs-cdn.flashcat.cloud'
    ),
    'https://docs-cdn.flashcat.cloud/test/docs/en.js'
  );
});

test('buildCdnUrl accepts CDN_URL without trailing slash', () => {
  assert.equal(
    buildCdnUrl(
      'https://flashcat-docs.oss-cn-hangzhou.aliyuncs.com/docs/api-reference/openapi.en.json',
      'https://flashcat-docs.oss-cn-hangzhou.aliyuncs.com',
      'https://docs-cdn.flashcat.cloud/'
    ),
    'https://docs-cdn.flashcat.cloud/docs/api-reference/openapi.en.json'
  );
});

test('buildCdnUrl rejects OSS URLs outside the configured endpoint', () => {
  assert.throws(
    () => buildCdnUrl(
      'https://unexpected.example.com/docs/en.js',
      'flashcat-docs.oss-cn-hangzhou.aliyuncs.com',
      'https://docs-cdn.flashcat.cloud'
    ),
    /does not match CDN_ENDPOINT/
  );
});
