import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  handle, issueToken, verifyToken, notionRow, typedProperty, markdownBlocks, LIMITS, DEFAULT_SOURCES,
} from '../src/worker.js';
import { fakeD1 } from './fake-d1.mjs';

const ORIGIN = 'https://s-elim.github.io';
const PASS = 'correct horse battery staple';
const T0 = Date.parse('2026-10-11T09:00:00Z');

function makeEnv(extra = {}) {
  return { DB: fakeD1(), ALLOWED_ORIGINS: ORIGIN, DESK_PASSPHRASE: PASS, ...extra };
}

const noFetch = async () => { throw new Error('unexpected upstream call'); };

async function call(env, method, path, { body, token, origin = ORIGIN, fetchImpl = noFetch, now = T0, ip = '1.2.3.4' } = {}) {
  const headers = { 'CF-Connecting-IP': ip };
  if (origin) headers.Origin = origin;
  if (token) headers.Authorization = 'Bearer ' + token;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const req = new Request('https://desk.example.workers.dev' + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const res = await handle(req, env, fetchImpl, now);
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* plain text */ }
  return { status: res.status, json, headers: res.headers, text };
}

async function signedIn(env) {
  const r = await call(env, 'POST', '/auth', { body: { passphrase: PASS } });
  assert.equal(r.status, 200, r.text);
  return r.json.token;
}

// ------------------------------------------------------------ CORS + health

test('rejects a foreign origin and answers preflight for the allowed one', async () => {
  const env = makeEnv();
  assert.equal((await call(env, 'GET', '/health', { origin: 'https://evil.example' })).status, 403);
  const pre = await call(env, 'OPTIONS', '/docs/entries');
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.match(pre.headers.get('Access-Control-Allow-Headers'), /Authorization/);
});

test('health reports which pieces are configured without needing a token', async () => {
  const r = await call(makeEnv({ NOTION_TOKEN: 'ntn_x' }), 'GET', '/health');
  assert.equal(r.status, 200);
  assert.deepEqual(r.json.configured, { db: true, passphrase: true, notion: true, google: false });
});

// ------------------------------------------------------------------- auth

test('refuses to run with a short or missing passphrase', async () => {
  const env = makeEnv({ DESK_PASSPHRASE: 'short' });
  const r = await call(env, 'POST', '/auth', { body: { passphrase: 'short' } });
  assert.equal(r.status, 503);
  assert.match(r.json.error, /DESK_PASSPHRASE/);
});

test('a wrong passphrase is refused and the right one returns a working token', async () => {
  const env = makeEnv();
  const bad = await call(env, 'POST', '/auth', { body: { passphrase: 'nope' } });
  assert.equal(bad.status, 401);
  const token = await signedIn(env);
  const ok = await call(env, 'GET', '/session', { token });
  assert.equal(ok.status, 200);
  assert.equal(ok.json.ok, true);
});

test('locks an address out after repeated failures, and only that address', async () => {
  const env = makeEnv();
  for (let i = 0; i < LIMITS.failuresPerKey; i++) {
    assert.equal((await call(env, 'POST', '/auth', { body: { passphrase: 'x' + i } })).status, 401);
  }
  const locked = await call(env, 'POST', '/auth', { body: { passphrase: PASS } });
  assert.equal(locked.status, 429);
  const other = await call(env, 'POST', '/auth', { body: { passphrase: PASS }, ip: '5.6.7.8' });
  assert.equal(other.status, 200);
  const later = await call(env, 'POST', '/auth', { body: { passphrase: PASS }, now: T0 + 16 * 60e3 });
  assert.equal(later.status, 200);
});

test('tokens expire, cannot be forged, and die when the passphrase changes', async () => {
  const { token, exp } = await issueToken(PASS, T0);
  assert.equal(await verifyToken(PASS, token, T0 + 1000), true);
  assert.equal(await verifyToken(PASS, token, exp + 1), false);
  assert.equal(await verifyToken('another passphrase entirely', token, T0), false);
  const [payload, sig] = token.split('.');
  const forged = btoa(JSON.stringify({ v: 1, iat: T0, exp: T0 + 9e12 })).replace(/=+$/, '') + '.' + sig;
  assert.equal(await verifyToken(PASS, forged, T0), false);
  assert.equal(await verifyToken(PASS, payload, T0), false);
  assert.equal(await verifyToken(PASS, 'garbage', T0), false);
});

test('every data route needs a token', async () => {
  const env = makeEnv();
  for (const [m, p] of [['GET', '/docs/entries'], ['GET', '/sync?from=2026-10-01&to=2026-10-31'], ['GET', '/export']]) {
    assert.equal((await call(env, m, p)).status, 401, p);
  }
});

// -------------------------------------------------------------- documents

test('documents carry versions, keep history, and refuse stale writes', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  const v1 = await call(env, 'PUT', '/docs/entries/idea-1', { token, body: { data: { title: 'First' } } });
  assert.equal(v1.status, 200);
  assert.equal(v1.json.doc.version, 1);
  const v2 = await call(env, 'PUT', '/docs/entries/idea-1', { token, body: { data: { title: 'Second' }, baseVersion: 1 } });
  assert.equal(v2.json.doc.version, 2);

  const stale = await call(env, 'PUT', '/docs/entries/idea-1', { token, body: { data: { title: 'Lost' }, baseVersion: 1 } });
  assert.equal(stale.status, 409);
  assert.equal(stale.json.doc.data.title, 'Second');

  const list = await call(env, 'GET', '/docs/entries', { token });
  assert.deepEqual(list.json.docs.map(d => d.data.title), ['Second']);

  const del = await call(env, 'DELETE', '/docs/entries/idea-1?base=2', { token });
  assert.equal(del.json.doc.deleted, true);
  assert.equal((await call(env, 'GET', '/docs/entries', { token })).json.docs.length, 0);
  assert.equal((await call(env, 'GET', '/docs/entries/idea-1', { token })).status, 404);

  const revs = await call(env, 'GET', '/docs/entries/idea-1/revisions', { token });
  assert.deepEqual(revs.json.revisions.map(r => [r.version, r.deleted]), [[3, true], [2, false], [1, false]]);
  const first = await call(env, 'GET', '/docs/entries/idea-1/revisions/1', { token });
  assert.equal(first.json.revision.data.title, 'First');

  // Restoring is an ordinary write of an old revision's data.
  const back = await call(env, 'PUT', '/docs/entries/idea-1', { token, body: { data: first.json.revision.data, baseVersion: 3 } });
  assert.equal(back.json.doc.version, 4);
  assert.equal((await call(env, 'GET', '/docs/entries', { token })).json.docs[0].data.title, 'First');
});

test('rejects unknown collections, bad ids and oversized documents', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  assert.equal((await call(env, 'GET', '/docs/secrets', { token })).status, 404);
  assert.equal((await call(env, 'PUT', '/docs/entries/bad%20id', { token, body: { data: {} } })).status, 400);
  const big = await call(env, 'PUT', '/docs/entries/big', { token, body: { data: { x: 'a'.repeat(LIMITS.doc) } } });
  assert.equal(big.status, 413);
  const noData = await call(env, 'PUT', '/docs/entries/x', { token, body: { title: 'missing wrapper' } });
  assert.equal(noData.status, 400);
});

test('images are stored without revision history and left out of a default export', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  await call(env, 'PUT', '/docs/images/img-1', { token, body: { data: { url: 'data:image/jpeg;base64,AAAA' } } });
  await call(env, 'PUT', '/docs/entries/e1', { token, body: { data: { title: 'E', images: ['img-1'] } } });
  const revs = await call(env, 'GET', '/docs/images/img-1/revisions', { token });
  assert.equal(revs.json.revisions.length, 0);
  const exp = await call(env, 'GET', '/export', { token });
  assert.equal(exp.json.format, 'desk-export-v1');
  assert.deepEqual(Object.keys(exp.json.docs), ['entries']);
  const full = await call(env, 'GET', '/export?images=1', { token });
  assert.deepEqual(Object.keys(full.json.docs).sort(), ['entries', 'images']);
});

test('import accepts an export, skips invalid rows and is idempotent', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  const payload = { format: 'desk-export-v1', docs: { entries: [{ id: 'a', data: { title: 'A' } }, { id: 'b', data: { title: 'B' } }] } };
  const first = await call(env, 'POST', '/import', { token, body: payload });
  assert.deepEqual([first.json.written, first.json.unchanged], [2, 0]);
  const again = await call(env, 'POST', '/import', { token, body: payload });
  assert.deepEqual([again.json.written, again.json.unchanged], [0, 2]);
  const flat = await call(env, 'POST', '/import', {
    token, body: { docs: [{ collection: 'entries', id: 'c', data: { title: 'C' } }, { collection: 'nope', id: 'd', data: {} }] },
  });
  assert.equal(flat.json.written, 1);
  assert.deepEqual(flat.json.skipped, ['d']);
  assert.equal((await call(env, 'GET', '/docs/entries', { token })).json.docs.length, 3);
});

// ------------------------------------------------------------------- sync

function notionPage(id, title, date, status) {
  return {
    id, url: 'https://www.notion.so/' + id, in_trash: false,
    properties: {
      Name: { type: 'title', title: [{ plain_text: title }] },
      Deadline: { type: 'date', date: date ? { start: date, end: null } : null },
      Status: { type: 'select', select: status ? { name: status } : null },
    },
  };
}

test('sync merges Google and Notion and isolates a failing source', async () => {
  const env = makeEnv({
    NOTION_TOKEN: 'ntn_test', GOOGLE_BRIDGE_URL: 'https://script.google.com/macros/s/X/exec', GOOGLE_BRIDGE_SECRET: 's'.repeat(32),
    NOTION_SOURCES: JSON.stringify([
      { id: 'aaaaaaaa-0000-0000-0000-000000000001', label: 'Publications', date: 'Deadline', status: 'Status', done: ['Accepted'] },
      { id: 'aaaaaaaa-0000-0000-0000-000000000002', label: 'Broken', date: 'Deadline' },
    ]),
  });
  const token = await signedIn(env);
  const seen = [];
  const fetchImpl = async (url, init) => {
    seen.push([url, init]);
    if (url.startsWith('https://script.google.com')) {
      const body = JSON.parse(init.body);
      assert.equal(body.secret, 's'.repeat(32));
      assert.equal(body.action, 'agenda');
      return new Response(JSON.stringify({ ok: true, events: [{ id: 'ev1', title: 'Lab meeting' }], tasks: [{ id: 't1', title: 'Rebuttal' }], calendars: [], tasklists: [] }));
    }
    if (url.endsWith('000000000001/query')) {
      const body = JSON.parse(init.body);
      assert.deepEqual(body.filter.and[0], { property: 'Deadline', date: { on_or_after: '2026-10-01' } });
      assert.equal(init.headers['Notion-Version'], '2025-09-03');
      return new Response(JSON.stringify({ results: [notionPage('p1', 'GaussVLA camera-ready', '2026-10-20', 'Camera-ready'), notionPage('p2', 'Old', '2026-10-05', 'Accepted')], has_more: false }));
    }
    return new Response(JSON.stringify({ message: 'Could not find data source' }), { status: 404 });
  };
  const r = await call(env, 'GET', '/sync?from=2026-10-01&to=2027-01-31&timeMin=2026-09-30T15:00:00Z&timeMax=2027-01-31T15:00:00Z&tz=Asia/Seoul', { token, fetchImpl });
  assert.equal(r.status, 200, r.text);
  assert.equal(r.json.google.ok, true);
  assert.equal(r.json.google.events[0].title, 'Lab meeting');
  assert.equal(r.json.notion.ok, true);
  const [pubs, broken] = r.json.notion.sources;
  assert.deepEqual(pubs.rows.map(x => [x.title, x.date, x.done]), [['GaussVLA camera-ready', '2026-10-20', false], ['Old', '2026-10-05', true]]);
  assert.match(broken.error, /Connections/);
  assert.equal(seen.filter(([u]) => u.includes('script.google.com'))[0][1].headers['Content-Type'], 'text/plain;charset=utf-8');
});

test('sync reports unconfigured integrations instead of failing', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  const r = await call(env, 'GET', '/sync?from=2026-10-01&to=2026-10-31', { token });
  assert.equal(r.status, 200);
  assert.deepEqual([r.json.google.configured, r.json.notion.configured], [false, false]);
});

test('sync validates its range', async () => {
  const env = makeEnv();
  const token = await signedIn(env);
  assert.equal((await call(env, 'GET', '/sync?from=2026-10-31&to=2026-10-01', { token })).status, 400);
  assert.equal((await call(env, 'GET', '/sync?from=2026-01-01&to=2028-01-01', { token })).status, 400);
  assert.equal((await call(env, 'GET', '/sync?from=yesterday&to=2026-10-01', { token })).status, 400);
});

test('a bridge that answers with HTML gets a fix-it message, not a crash', async () => {
  const env = makeEnv({ GOOGLE_BRIDGE_URL: 'https://script.google.com/x', GOOGLE_BRIDGE_SECRET: 'k'.repeat(32) });
  const token = await signedIn(env);
  const fetchImpl = async () => new Response('<html>Sign in</html>');
  const r = await call(env, 'GET', '/sync?from=2026-10-01&to=2026-10-31', { token, fetchImpl });
  assert.equal(r.json.google.ok, false);
  assert.match(r.json.google.error, /Anyone/);
});

// ----------------------------------------------------------------- google

test('google actions are whitelisted and forwarded with the secret', async () => {
  const env = makeEnv({ GOOGLE_BRIDGE_URL: 'https://script.google.com/x', GOOGLE_BRIDGE_SECRET: 'k'.repeat(32) });
  const token = await signedIn(env);
  assert.equal((await call(env, 'POST', '/google', { token, body: { action: 'agenda' } })).status, 400);
  let forwarded;
  const fetchImpl = async (url, init) => {
    forwarded = JSON.parse(init.body);
    return new Response(JSON.stringify({ ok: true, task: { id: 't9', title: forwarded.title } }));
  };
  const r = await call(env, 'POST', '/google', { token, fetchImpl, body: { action: 'createTask', title: 'Email Prof. Kim', due: '2026-10-12' } });
  assert.equal(r.status, 200);
  assert.equal(r.json.task.id, 't9');
  assert.equal(forwarded.secret, 'k'.repeat(32));
  assert.equal(forwarded.action, 'createTask');
});

// ----------------------------------------------------------------- notion

test('notionRow reads the title column, the configured date and the done states', () => {
  const src = DEFAULT_SOURCES[0];
  const row = notionRow(notionPage('p', 'Paper', '2026-11-16', 'Accepted'), src);
  assert.deepEqual([row.title, row.date, row.status, row.done, row.source], ['Paper', '2026-11-16', 'Accepted', true, 'Publications']);
  const untitled = notionRow({ id: 'q', properties: {} }, { id: 'x', label: 'L' });
  assert.equal(untitled.title, '(untitled)');
});

test('typedProperty maps plain strings onto Notion property shapes', () => {
  assert.deepEqual(typedProperty('select', 'High'), { select: { name: 'High' } });
  assert.deepEqual(typedProperty('multi_select', 'VLA, World Models'), { multi_select: [{ name: 'VLA' }, { name: 'World Models' }] });
  assert.deepEqual(typedProperty('date', '2027-07-30'), { date: { start: '2027-07-30' } });
  assert.equal(typedProperty('date', 'soon'), null);
  assert.equal(typedProperty('url', 'javascript:alert(1)'), null);
  assert.equal(typedProperty('rich_text', '   '), null);
  assert.equal(typedProperty('rich_text', 'x'.repeat(5000)).rich_text[0].text.content.length, 2000);
});

test('markdownBlocks turns headings, bullets and paragraphs into blocks', () => {
  const blocks = markdownBlocks('## Thesis\n\nOne claim.\n\n- a\n- b');
  assert.deepEqual(blocks.map(b => b.type), ['heading_2', 'paragraph', 'bulleted_list_item', 'bulleted_list_item']);
});

test('creating a Notion row types each field from the live schema', async () => {
  const env = makeEnv({ NOTION_TOKEN: 'ntn_test' });
  const token = await signedIn(env);
  let created;
  const fetchImpl = async (url, init) => {
    if (url.endsWith('/data_sources/5df9a8fe-83bc-4b35-865c-186120e4b97d')) {
      return new Response(JSON.stringify({
        title: [{ plain_text: 'Ideas' }],
        properties: { Idea: { type: 'title' }, Stage: { type: 'select', select: { options: [{ name: 'Seed' }] } }, Concept: { type: 'rich_text' } },
      }));
    }
    if (url.endsWith('/pages')) {
      created = JSON.parse(init.body);
      return new Response(JSON.stringify({ id: 'new', url: 'https://www.notion.so/new' }));
    }
    throw new Error('unexpected ' + url);
  };
  const schema = await call(env, 'GET', '/notion/schema?id=5df9a8fe-83bc-4b35-865c-186120e4b97d', { token, fetchImpl });
  assert.deepEqual(schema.json.fields.map(f => f.name), ['Idea', 'Stage', 'Concept']);
  const r = await call(env, 'POST', '/notion/pages', {
    token, fetchImpl,
    body: { target: '5df9a8fe-83bc-4b35-865c-186120e4b97d', title: 'World model plan', fields: { Stage: 'Seed', Concept: 'WM', Unknown: 'x' }, body: '## Thesis\n\nClaim.' },
  });
  assert.equal(r.status, 200, r.text);
  assert.equal(r.json.url, 'https://www.notion.so/new');
  assert.deepEqual(created.parent, { type: 'data_source_id', data_source_id: '5df9a8fe-83bc-4b35-865c-186120e4b97d' });
  assert.deepEqual(Object.keys(created.properties).sort(), ['Concept', 'Idea', 'Stage']);
  assert.equal(created.children[0].type, 'heading_2');
  const unknown = await call(env, 'POST', '/notion/pages', { token, fetchImpl, body: { target: 'not-a-target', title: 'x' } });
  assert.equal(unknown.status, 400);
});
