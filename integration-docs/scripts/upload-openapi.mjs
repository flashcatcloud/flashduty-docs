import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildCdnUrl } from './cdn-url.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..');
const defaultApiReferenceDir = path.join(repoRoot, 'api-reference');
const docsBaseUrl = 'https://docs.flashcat.cloud';
const httpMethods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'];

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

export function listOpenapiJsonFiles(apiReferenceDir = defaultApiReferenceDir) {
  if (!fs.existsSync(apiReferenceDir)) {
    throw new Error(`OpenAPI directory does not exist: ${apiReferenceDir}`);
  }

  return fs.readdirSync(apiReferenceDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .sort();
}

function normalizeCdnDir(cdnDir) {
  const normalized = cdnDir.replace(/\/+$/g, '');
  return normalized || '/';
}

export function buildOssFilePath(cdnDir, file) {
  return path.posix.join(normalizeCdnDir(cdnDir), 'api-reference', file);
}

export function validateJsonFile(filePath) {
  JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function buildOpenapiReferenceIndex(openapi) {
  const result = {};

  for (const [apiPath, pathItem] of Object.entries(openapi.paths ?? {})) {
    const operation = httpMethods
      .map((method) => pathItem?.[method])
      .find(Boolean);
    const href = operation?.['x-mint']?.href;
    const label = operation?.summary || operation?.['x-mint']?.metadata?.sidebarTitle || operation?.operationId;

    if (href && label) {
      result[apiPath] = {
        label,
        url: new URL(href, docsBaseUrl).toString()
      };
    }
  }

  return result;
}

function buildJsonUploadOptions() {
  return {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=300'
    }
  };
}

async function createOssClient(env = process.env) {
  const { default: OSS } = await import('ali-oss');
  return new OSS({
    region: env.CDN_REGION,
    accessKeyId: env.CDN_ACCESS_KEY,
    accessKeySecret: env.CDN_SECRET_KEY,
    bucket: env.CDN_BUCKET
  });
}

async function createCdnRuntime(env = process.env) {
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

async function refreshCdnCache(cdnRuntime, url) {
  const request = new cdnRuntime.CDN.RefreshObjectCachesRequest({});
  request.objectPath = url;
  request.objectType = 'File';
  await cdnRuntime.client.refreshObjectCaches(request);
  console.log(`Refreshed CDN cache: ${url}`);
}

async function uploadJsonAsset({
  env,
  ossClient,
  cdnRuntime,
  ossFilePath,
  payload,
  label
}) {
  const result = await ossClient.put(ossFilePath, payload, buildJsonUploadOptions());
  const cdnUrl = buildCdnUrl(result.url, env.CDN_ENDPOINT, env.CDN_URL);
  console.log(`Uploaded ${label} -> ${cdnUrl}`);
  await refreshCdnCache(cdnRuntime, cdnUrl);
}

export async function uploadOpenapiJsonFiles({
  apiReferenceDir = defaultApiReferenceDir,
  env = process.env,
  ossClient,
  cdnRuntime
} = {}) {
  const missing = validateRequiredEnv(env);
  if (missing.length > 0) {
    throw new Error(`Missing required env vars: ${missing.join(', ')}`);
  }

  const files = listOpenapiJsonFiles(apiReferenceDir);
  if (files.length === 0) {
    throw new Error(`No OpenAPI JSON files found in ${apiReferenceDir}`);
  }

  for (const file of files) {
    validateJsonFile(path.join(apiReferenceDir, file));
  }

  const resolvedOssClient = ossClient ?? await createOssClient(env);
  const resolvedCdnRuntime = cdnRuntime ?? await createCdnRuntime(env);

  for (const file of files) {
    const localFilePath = path.join(apiReferenceDir, file);
    const ossFilePath = buildOssFilePath(env.CDN_DIR, file);
    const uploadPayload = Buffer.from(`${JSON.stringify(
      buildOpenapiReferenceIndex(JSON.parse(fs.readFileSync(localFilePath, 'utf8'))),
      null,
      2
    )}\n`);
    await uploadJsonAsset({
      env,
      ossClient: resolvedOssClient,
      cdnRuntime: resolvedCdnRuntime,
      ossFilePath,
      payload: uploadPayload,
      label: file
    });
  }

  const manifestPayload = Buffer.from(`${JSON.stringify({ files }, null, 2)}\n`);
  await uploadJsonAsset({
    env,
    ossClient: resolvedOssClient,
    cdnRuntime: resolvedCdnRuntime,
    ossFilePath: buildOssFilePath(env.CDN_DIR, 'manifest.json'),
    payload: manifestPayload,
    label: 'manifest.json'
  });

  console.log(`Uploaded ${files.length} OpenAPI JSON files and manifest from ${apiReferenceDir}`);
}

async function loadDotenvIfAvailable() {
  try {
    const { default: dotenv } = await import('dotenv');
    dotenv.config();
  } catch (err) {
    if (err.code !== 'ERR_MODULE_NOT_FOUND') {
      throw err;
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await loadDotenvIfAvailable();
  await uploadOpenapiJsonFiles();
}
