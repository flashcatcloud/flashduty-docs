import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildCdnUrl } from './cdn-url.mjs';
import {
  createOssClient,
  loadDotenvIfAvailable,
  normalizeCdnDir,
  validateRequiredEnv
} from './oss-cdn.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..');
const defaultTarPath = path.join(repoRoot, '.docs-bundle-build', 'flashduty-docs.tar.gz');

export function buildOssFilePath(cdnDir) {
  return path.posix.join(normalizeCdnDir(cdnDir), 'flashduty-docs.tar.gz');
}

// ali-oss's timeout (default 60s) runs from socket connect until the response
// arrives, so it also covers sending the body. From a GitHub-hosted runner the
// ~3 MB tarball has taken 5.5 minutes to reach OSS (~9 KB/s).
const TAR_UPLOAD_TIMEOUT_MS = 30 * 60 * 1000;

// No CDN refresh after the upload: the static CDN follows the origin's
// Cache-Control, so a new tarball reaches readers within max-age.
function buildTarUploadOptions() {
  return {
    timeout: TAR_UPLOAD_TIMEOUT_MS,
    headers: {
      'Content-Type': 'application/gzip',
      'Cache-Control': 'public, max-age=300'
    }
  };
}

export async function uploadDocsBundle({
  tarPath = defaultTarPath,
  env = process.env,
  ossClient
} = {}) {
  const missing = validateRequiredEnv(env);
  if (missing.length > 0) {
    throw new Error(`Missing required env vars: ${missing.join(', ')}`);
  }
  if (!fs.existsSync(tarPath)) {
    throw new Error(`Docs bundle tarball does not exist: ${tarPath}`);
  }

  const resolvedOssClient = ossClient ?? await createOssClient(env);

  const ossFilePath = buildOssFilePath(env.CDN_DIR);
  const result = await resolvedOssClient.put(ossFilePath, tarPath, buildTarUploadOptions());
  const cdnUrl = buildCdnUrl(result.url, env.CDN_ENDPOINT, env.CDN_URL);
  console.log(`Uploaded ${path.basename(tarPath)} -> ${cdnUrl}`);

  return cdnUrl;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await loadDotenvIfAvailable();
  await uploadDocsBundle();
}
