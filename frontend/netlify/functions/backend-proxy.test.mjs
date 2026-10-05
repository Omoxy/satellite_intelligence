import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { test } from 'node:test';

import backendProxy from './backend-proxy.mjs';

const backendUrl = 'https://backend.example.test';
const apiKey = 'test-only-server-secret-with-at-least-32-characters';
const functionPrefix = '/.netlify/functions/backend-proxy';

async function runWithNetlify(fetchImplementation, run) {
  const previousNetlify = globalThis.Netlify;
  const previousFetch = globalThis.fetch;
  globalThis.Netlify = {
    env: {
      get(name) {
        return {
          BACKEND_URL: backendUrl,
          API_ACCESS_KEY: apiKey,
        }[name];
      },
    },
  };
  globalThis.fetch = fetchImplementation;
  try {
    return await run();
  } finally {
    if (previousNetlify === undefined) {
      delete globalThis.Netlify;
    } else {
      globalThis.Netlify = previousNetlify;
    }
    globalThis.fetch = previousFetch;
  }
}

test('anonymous protected writes are rejected without contacting the backend', async () => {
  const protectedRequests = [
    { method: 'POST', path: '/api/areas', body: '{"name":"unauthorized"}' },
    { method: 'DELETE', path: '/api/areas/custom-area' },
    { method: 'POST', path: '/api/analysis', body: '{"aoi_id":"custom-area"}' },
  ];

  await runWithNetlify(
    async () => {
      assert.fail('Protected requests must not be forwarded.');
    },
    async () => {
      for (const { method, path, body } of protectedRequests) {
        const response = await backendProxy(
          new Request(`https://site.example.test${functionPrefix}${path}`, {
            method,
            headers: {
              'content-type': 'application/json',
              'x-api-key': apiKey,
              authorization: `Bearer ${apiKey}`,
            },
            body,
          })
        );
        assert.equal(response.status, 403, `${method} ${path}`);
      }
    }
  );
});

test('approved read-only requests work without forwarding client credentials', async () => {
  let upstreamRequest;
  await runWithNetlify(
    async (url, options) => {
      upstreamRequest = { url: new URL(url), options };
      return new Response('{"data":{"areas":[]}}', {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'must-not-be-forwarded=1',
        },
      });
    },
    async () => {
      const response = await backendProxy(
        new Request(`https://site.example.test${functionPrefix}/api/areas`, {
          headers: {
            authorization: 'Bearer client-supplied-token',
            'x-api-key': 'client-supplied-key',
            'x-nf-client-connection-ip': '203.0.113.9',
          },
        })
      );
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), { data: { areas: [] } });
      assert.equal(upstreamRequest.url.href, `${backendUrl}/api/areas`);
      assert.equal(upstreamRequest.options.method, 'GET');
      assert.equal(upstreamRequest.options.headers.get('x-api-key'), null);
      assert.equal(upstreamRequest.options.headers.get('authorization'), null);
      assert.equal(response.headers.get('set-cookie'), null);

      const timestamp = upstreamRequest.options.headers.get('x-proxy-timestamp');
      const expectedSignature = createHmac('sha256', apiKey)
        .update(`${timestamp}:203.0.113.9`)
        .digest('hex');
      assert.equal(upstreamRequest.options.headers.get('x-proxy-signature'), expectedSignature);
    }
  );
});

test('arbitrary paths and unsupported methods are not proxied', async () => {
  let upstreamCalls = 0;
  await runWithNetlify(
    async () => {
      upstreamCalls += 1;
      return new Response('unexpected');
    },
    async () => {
      const unknownPath = await backendProxy(
        new Request(`https://site.example.test${functionPrefix}/api/admin`)
      );
      const unsupportedMethod = await backendProxy(
        new Request(`https://site.example.test${functionPrefix}/api/areas`, {
          method: 'PUT',
        })
      );
      assert.equal(unknownPath.status, 404);
      assert.equal(unsupportedMethod.status, 405);
      assert.equal(unsupportedMethod.headers.get('allow'), 'GET');
      assert.equal(upstreamCalls, 0);
    }
  );
});

test('location inspection rejects invalid and unexpected query parameters', async () => {
  let upstreamCalls = 0;
  await runWithNetlify(
    async () => {
      upstreamCalls += 1;
      return new Response('{}');
    },
    async () => {
      const invalidCoordinate = await backendProxy(
        new Request(
          `https://site.example.test${functionPrefix}/api/location?lat=91&lng=0`
        )
      );
      const unexpectedQuery = await backendProxy(
        new Request(
          `https://site.example.test${functionPrefix}/api/location?lat=0&lng=0&url=https://evil.test`
        )
      );
      assert.equal(invalidCoordinate.status, 404);
      assert.equal(unexpectedQuery.status, 404);
      assert.equal(upstreamCalls, 0);
    }
  );
});
