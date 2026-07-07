export function buildCdnUrl(ossUrl, cdnEndpoint, cdnUrl) {
  const endpointHost = cdnEndpoint
    .replace(/^https?:\/\//, '')
    .replace(/\/+$/g, '');
  const normalizedCdnUrl = cdnUrl.replace(/\/+$/g, '');
  const parsedUrl = new URL(ossUrl);

  if (parsedUrl.host === endpointHost || parsedUrl.host.endsWith(`.${endpointHost}`)) {
    return `${normalizedCdnUrl}${parsedUrl.pathname}`;
  }

  throw new Error(`OSS URL host ${parsedUrl.host} does not match CDN_ENDPOINT ${endpointHost}`);
}
