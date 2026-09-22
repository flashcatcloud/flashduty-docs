// Shared OSS upload + CDN refresh helpers for the publishing scripts
// (upload-openapi.mjs, upload-docs-bundle.mjs). All of them read the same
// CDN_* env vars and publish under CDN_URL + CDN_DIR; only upload-openapi.mjs
// refreshes the CDN.

export const requiredEnv = [
  'CDN_ACCESS_KEY',
  'CDN_SECRET_KEY',
  'CDN_BUCKET',
  'CDN_REGION',
  'CDN_ENDPOINT',
  'CDN_URL',
  'CDN_DIR'
];

export function validateRequiredEnv(env = process.env) {
  return requiredEnv.filter((key) => !env[key]);
}

export function normalizeCdnDir(cdnDir) {
  const normalized = cdnDir.replace(/\/+$/g, '');
  return normalized || '/';
}

export async function createOssClient(env = process.env) {
  const { default: OSS } = await import('ali-oss');
  return new OSS({
    region: env.CDN_REGION,
    accessKeyId: env.CDN_ACCESS_KEY,
    accessKeySecret: env.CDN_SECRET_KEY,
    bucket: env.CDN_BUCKET
  });
}

export async function createCdnRuntime(env = process.env) {
  const { default: CDN } = await import('@alicloud/cdn20180510');
  const { default: OpenApi } = await import('@alicloud/openapi-client');
  const client = new CDN.default(new OpenApi.Config({
    accessKeyId: env.CDN_ACCESS_KEY,
    accessKeySecret: env.CDN_SECRET_KEY,
    endpoint: 'cdn.aliyuncs.com',
    regionId: 'cn-beijing'
  }));

  return { CDN, client };
}

export async function refreshCdnCache(cdnRuntime, url) {
  const request = new cdnRuntime.CDN.RefreshObjectCachesRequest({});
  request.objectPath = url;
  request.objectType = 'File';
  await cdnRuntime.client.refreshObjectCaches(request);
  console.log(`Refreshed CDN cache: ${url}`);
}

// Load .env for local runs. Tolerate 'dotenv' not being installed (e.g. a
// pruned install) rather than failing scripts that get their env from CI.
export async function loadDotenvIfAvailable() {
  try {
    const { default: dotenv } = await import('dotenv');
    dotenv.config();
  } catch (err) {
    if (err.code !== 'ERR_MODULE_NOT_FOUND') {
      throw err;
    }
  }
}
