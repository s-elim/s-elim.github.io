// Tests for the anonymous-message Worker. Run with: node --test
// Every network call goes through an injected fetch, so nothing leaves the machine.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handle, LIMITS } from '../src/worker.js';

const ORIGIN = 'https://s-elim.github.io';
const ENV = {
  ALLOWED_ORIGINS: 'https://s-elim.github.io, http://localhost:4000',
  TURNSTILE_SECRET: 'turnstile-secret',
  RESEND_API_KEY: 're_test_key',
  TO_EMAIL: 'owner@example.com',
};

function fakeFetch({ turnstile = { success: true, hostname: 's-elim.github.io' }, resendStatus = 200 } = {}) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url: String(url), init });
    if (String(url).includes('challenges.cloudflare.com')) {
      return new Response(JSON.stringify(turnstile), { status: 200 });
    }
    if (String(url).includes('api.resend.com')) {
      return new Response(JSON.stringify(resendStatus === 200 ? { id: 'email_1' } : { message: 'nope' }), { status: resendStatus });
    }
    throw new Error('unexpected fetch ' + url);
  };
  impl.calls = calls;
  return impl;
}

function post(body, { origin = ORIGIN, type = 'application/json', raw } = {}) {
  const headers = { 'Content-Type': type };
  if (origin) headers.Origin = origin;
  return new Request('https://contact.example.workers.dev/', {
    method: 'POST',
    headers,
    body: raw !== undefined ? raw : JSON.stringify(body),
  });
}

const GOOD = { message: 'Hello Selim, I enjoyed your V-JEPA teardown.', contact: '', website: '', token: 'tok', page: '/notes/v-jepa/' };

test('preflight from an allowed origin returns CORS headers', async () => {
  const res = await handle(new Request('https://x/', { method: 'OPTIONS', headers: { Origin: ORIGIN } }), ENV, fakeFetch());
  assert.equal(res.status, 204);
  assert.equal(res.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.match(res.headers.get('Access-Control-Allow-Methods'), /POST/);
});

test('requests from other origins are refused without CORS headers', async () => {
  const f = fakeFetch();
  const res = await handle(post(GOOD, { origin: 'https://evil.example' }), ENV, f);
  assert.equal(res.status, 403);
  assert.equal(res.headers.get('Access-Control-Allow-Origin'), null);
  assert.equal(f.calls.length, 0);
});

test('requests with no Origin header are refused', async () => {
  const res = await handle(post(GOOD, { origin: null }), ENV, fakeFetch());
  assert.equal(res.status, 403);
});

test('only POST is accepted', async () => {
  const res = await handle(new Request('https://x/', { method: 'GET', headers: { Origin: ORIGIN } }), ENV, fakeFetch());
  assert.equal(res.status, 405);
});

test('non-JSON bodies are rejected', async () => {
  const res = await handle(post(null, { type: 'text/plain', raw: 'hi' }), ENV, fakeFetch());
  assert.equal(res.status, 415);
});

test('oversized bodies are rejected before parsing', async () => {
  const res = await handle(post(null, { raw: 'x'.repeat(LIMITS.body + 1) }), ENV, fakeFetch());
  assert.equal(res.status, 413);
});

test('malformed JSON is a 400', async () => {
  const res = await handle(post(null, { raw: '{not json' }), ENV, fakeFetch());
  assert.equal(res.status, 400);
});

test('a filled honeypot is dropped silently and sends nothing', async () => {
  const f = fakeFetch();
  const res = await handle(post({ ...GOOD, website: 'http://spam.example' }), ENV, f);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true });
  assert.equal(f.calls.length, 0);
});

test('message length is enforced', async () => {
  for (const message of ['', '   ', 'hey', 'x'.repeat(LIMITS.message + 1)]) {
    const f = fakeFetch();
    const res = await handle(post({ ...GOOD, message }), ENV, f);
    assert.equal(res.status, 400, 'length ' + message.length);
    assert.equal(f.calls.length, 0);
  }
});

test('contact field length is enforced', async () => {
  const res = await handle(post({ ...GOOD, contact: 'a'.repeat(LIMITS.contact + 1) }), ENV, fakeFetch());
  assert.equal(res.status, 400);
});

test('a missing spam-check token is a 400', async () => {
  const res = await handle(post({ ...GOOD, token: '' }), ENV, fakeFetch());
  assert.equal(res.status, 400);
});

test('a failed spam check is a 403 and sends no email', async () => {
  const f = fakeFetch({ turnstile: { success: false } });
  const res = await handle(post(GOOD), ENV, f);
  assert.equal(res.status, 403);
  assert.equal(f.calls.filter(c => c.url.includes('resend')).length, 0);
});

test('a spam-check token issued for another hostname is refused', async () => {
  const f = fakeFetch({ turnstile: { success: true, hostname: 'evil.example' } });
  const res = await handle(post(GOOD), ENV, f);
  assert.equal(res.status, 403);
});

test('the spam check is sent the secret and token, and never the visitor IP', async () => {
  const f = fakeFetch();
  const req = post(GOOD);
  req.headers.set('CF-Connecting-IP', '203.0.113.9');
  await handle(req, ENV, f);
  const body = f.calls[0].init.body;
  assert.equal(body.get('secret'), 'turnstile-secret');
  assert.equal(body.get('response'), 'tok');
  assert.equal(body.get('remoteip'), null);
});

test('missing configuration is a 500 with a generic message', async () => {
  const res = await handle(post(GOOD), { ALLOWED_ORIGINS: ORIGIN }, fakeFetch());
  assert.equal(res.status, 500);
  const j = await res.json();
  assert.equal(j.ok, false);
  assert.doesNotMatch(j.error, /RESEND|TURNSTILE|TO_EMAIL/);
});

test('a delivery failure is a 502', async () => {
  const res = await handle(post(GOOD), ENV, fakeFetch({ resendStatus: 500 }));
  assert.equal(res.status, 502);
});

test('a good message is emailed as plain text to the configured inbox', async () => {
  const f = fakeFetch();
  const res = await handle(post(GOOD), ENV, f);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true });
  assert.equal(res.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  const send = f.calls.find(c => c.url === 'https://api.resend.com/emails');
  assert.ok(send);
  assert.equal(send.init.headers.Authorization, 'Bearer re_test_key');
  const mail = JSON.parse(send.init.body);
  assert.deepEqual(mail.to, ['owner@example.com']);
  assert.equal(mail.from, 'Homepage messages <onboarding@resend.dev>');
  assert.match(mail.subject, /message/i);
  assert.ok(!mail.subject.includes(GOOD.message), 'visitor text never goes in the subject');
  assert.ok(mail.text.includes(GOOD.message));
  assert.ok(mail.text.includes('/notes/v-jepa/'));
  assert.equal(mail.html, undefined);
  assert.equal(mail.reply_to, undefined);
});

test('a valid email in the contact field becomes reply_to', async () => {
  const f = fakeFetch();
  await handle(post({ ...GOOD, contact: 'visitor@example.org' }), ENV, f);
  const mail = JSON.parse(f.calls.find(c => c.url.includes('resend')).init.body);
  assert.equal(mail.reply_to, 'visitor@example.org');
  assert.ok(mail.text.includes('visitor@example.org'));
});

test('a non-email contact is kept in the body but not used as reply_to', async () => {
  const f = fakeFetch();
  await handle(post({ ...GOOD, contact: '@someone on LinkedIn' }), ENV, f);
  const mail = JSON.parse(f.calls.find(c => c.url.includes('resend')).init.body);
  assert.equal(mail.reply_to, undefined);
  assert.ok(mail.text.includes('@someone on LinkedIn'));
});

test('line breaks cannot smuggle headers through the contact field', async () => {
  const f = fakeFetch();
  await handle(post({ ...GOOD, contact: 'a@b.co\r\nBcc: x@y.z' }), ENV, f);
  const mail = JSON.parse(f.calls.find(c => c.url.includes('resend')).init.body);
  assert.equal(mail.reply_to, undefined);
});

test('an optional rate limiter blocks bursts before any network call', async () => {
  const f = fakeFetch();
  const env = { ...ENV, RATE_LIMITER: { limit: async () => ({ success: false }) } };
  const res = await handle(post(GOOD), env, f);
  assert.equal(res.status, 429);
  assert.equal(f.calls.length, 0);
});

test('FROM_EMAIL overrides the default sender', async () => {
  const f = fakeFetch();
  await handle(post(GOOD), { ...ENV, FROM_EMAIL: 'Site <hi@example.dev>' }, f);
  const mail = JSON.parse(f.calls.find(c => c.url.includes('resend')).init.body);
  assert.equal(mail.from, 'Site <hi@example.dev>');
});
