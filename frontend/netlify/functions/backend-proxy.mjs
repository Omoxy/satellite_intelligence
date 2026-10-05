import { createHmac } from 'node:crypto';

const FUNCTION_PREFIX = '/.netlify/functions/backend-proxy';
const ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;
const JSON_HEADERS = { 'Content-Type': 'application/json' };

function errorResponse(status, detail, headers = {}) {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { ...JSON_HEADERS, ...headers },
  });
}

function getBackendPath(pathname) {
  if (pathname === FUNCTION_PREFIX) {
    return '/';
  }
  if (!pathname.startsWith(`${FUNCTION_PREFIX}/`)) {
    return null;
  }
  return decodeURIComponent(pathname.slice(FUNCTION_PREFIX.length));
}

function isProtectedWrite(method, path) {
  return (
    (method === 'POST' && (path === '/api/areas' || path === '/api/analysis')) ||
    (method === 'DELETE' && /^\/api\/areas\/[A-Za-z0-9_-]{1,128}$/.test(path))
  );
}

function allowedReadPath(path, searchParams) {
  const hasNoQuery = [...searchParams.keys()].length === 0;
  if (
    hasNoQuery &&
    (path === '/health' ||
      path === '/api/areas' ||
      /^\/api\/areas\/[A-Za-z0-9_-]{1,128}$/.test(path) ||
      /^\/api\/analysis\/[A-Za-z0-9_-]{1,128}$/.test(path))
  ) {
    return true;
  }

  if (path !== '/api/location') {
    return false;
  }

  const allowedNames = new Set(['lat', 'lng', 'analysis_id']);
  if ([...searchParams.keys()].some((name) => !allowedNames.has(name))) {
    return false;
  }

  const latValues = searchParams.getAll('lat');
  const lngValues = searchParams.getAll('lng');
  const analysisIds = searchParams.getAll('analysis_id');
  if (latValues.length !== 1 || lngValues.length !== 1 || analysisIds.length > 1) {
    return false;
  }

  const lat = Number(latValues[0]);
  const lng = Number(lngValues[0]);
  return (
    Number.isFinite(lat) &&
    lat >= -90 &&
    lat <= 90 &&
    Number.isFinite(lng) &&
    lng >= -180 &&
    lng <= 180 &&
    (analysisIds.length === 0 || ID_PATTERN.test(analysisIds[0]))
  );
}

export default async (request) => {
  let requestUrl;
  let path;
  try {
    requestUrl = new URL(request.url);
    path = getBackendPath(requestUrl.pathname);
  } catch {
    return errorResponse(400, 'Invalid request path.');
  }

  if (path === null) {
    return errorResponse(404, 'Not found.');
  }
  if (isProtectedWrite(request.method, path)) {
    return errorResponse(403, 'Write operations are unavailable until user authentication is implemented.');
  }
  if (request.method !== 'GET') {
    return errorResponse(405, 'Only approved read-only requests are available.', { Allow: 'GET' });
  }
  if (!allowedReadPath(path, requestUrl.searchParams)) {
    return errorResponse(404, 'Not found.');
  }
  if (request.body !== null) {
    await request.body.cancel();
    return errorResponse(400, 'Request bodies are not accepted.');
  }

  let backendOrigin;
  try {
    backendOrigin = new URL(globalThis.Netlify.env.get('BACKEND_URL') ?? '');
  } catch {
    return errorResponse(503, 'Backend service is not configured.');
  }
  if (
    backendOrigin.protocol !== 'https:' ||
    backendOrigin.username ||
    backendOrigin.password ||
    backendOrigin.pathname !== '/' ||
    backendOrigin.search ||
    backendOrigin.hash
  ) {
    return errorResponse(503, 'Backend service must be configured as an HTTPS origin.');
  }

  const apiKey = globalThis.Netlify.env.get('API_ACCESS_KEY') ?? '';
  if (apiKey.length < 32) {
    return errorResponse(503, 'Backend access is not configured.');
  }

  const clientIp = request.headers.get('x-nf-client-connection-ip') ?? 'unknown';
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = createHmac('sha256', apiKey).update(`${timestamp}:${clientIp}`).digest('hex');
  const headers = new Headers({
    Accept: 'application/json',
    'x-proxy-client-ip': clientIp,
    'x-proxy-timestamp': timestamp,
    'x-proxy-signature': signature,
  });
  const backendUrl = new URL(path, backendOrigin);
  backendUrl.search = requestUrl.search;

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers,
      redirect: 'manual',
    });
    const responseHeaders = new Headers();
    for (const name of ['cache-control', 'content-type', 'etag', 'last-modified', 'vary']) {
      const value = response.headers.get(name);
      if (value) {
        responseHeaders.set(name, value);
      }
    }
    return new Response(await response.arrayBuffer(), {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    console.error('Backend read request failed.');
    return errorResponse(502, 'Backend service is temporarily unavailable.');
  }
};
