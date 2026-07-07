import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import OSS from 'ali-oss';
import CDN from '@alicloud/cdn20180510';
import OpenApi from '@alicloud/openapi-client';
import dotenv from 'dotenv';
import { buildCdnUrl } from './cdn-url.mjs';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const localDir = path.join(packageRoot, 'dist', 'iife');

const requiredEnv = ['CDN_ACCESS_KEY', 'CDN_SECRET_KEY', 'CDN_BUCKET', 'CDN_REGION', 'CDN_ENDPOINT', 'CDN_URL', 'CDN_DIR'];
const missing = requiredEnv.filter((key) => !process.env[key]);
if (missing.length > 0) {
  throw new Error(`Missing required env vars: ${missing.join(', ')}`);
}

const ossClient = new OSS({
  region: process.env.CDN_REGION,
  accessKeyId: process.env.CDN_ACCESS_KEY,
  accessKeySecret: process.env.CDN_SECRET_KEY,
  bucket: process.env.CDN_BUCKET
});

const cdnClient = new CDN.default(new OpenApi.Config({
  accessKeyId: process.env.CDN_ACCESS_KEY,
  accessKeySecret: process.env.CDN_SECRET_KEY,
  endpoint: 'cdn.aliyuncs.com',
  regionId: 'cn-beijing'
}));

async function refreshCdnCache(url) {
  const request = new CDN.RefreshObjectCachesRequest({});
  request.objectPath = url;
  request.objectType = 'File';
  await cdnClient.refreshObjectCaches(request);
  console.log(`Refreshed CDN cache: ${url}`);
}

async function uploadFile(file) {
  const localFilePath = path.join(localDir, file);
  const ossFilePath = path.join(process.env.CDN_DIR, file).replace(/\\/g, '/');
  const result = await ossClient.put(ossFilePath, localFilePath);
  const cdnUrl = buildCdnUrl(result.url, process.env.CDN_ENDPOINT, process.env.CDN_URL);
  console.log(`Uploaded ${file} -> ${cdnUrl}`);
  await refreshCdnCache(cdnUrl);
}

if (!fs.existsSync(localDir)) {
  throw new Error(`Build output does not exist: ${localDir}`);
}

for (const file of fs.readdirSync(localDir)) {
  if (file.endsWith('.js')) {
    await uploadFile(file);
  }
}
