// Private research desk for s-elim.github.io/research-ideas/.
//
// The page is public; everything it shows from here is not. Every route except
// /health and /auth needs a bearer token, and a token is only issued for the
// passphrase. Entries live in D1 with a revision row per change, Notion rows
// arrive through an internal integration token, and Google Calendar and Tasks
// arrive through a small Apps Script bridge that runs as the owner (see
// ../bridge/). All of it fits the free tiers.
//
// Settings (Cloudflare dashboard > Worker > Settings):
//   DB                    D1 binding  the desk database (tables are created on first use)
//   ALLOWED_ORIGINS       text        comma-separated, e.g. "https://s-elim.github.io"
//   DESK_PASSPHRASE       secret      at least 12 characters; changing it signs out every device
//   NOTION_TOKEN          secret      optional, internal integration secret ("ntn_...")
//   GOOGLE_BRIDGE_URL     secret      optional, the Apps Script web app URL (".../exec")
//   GOOGLE_BRIDGE_SECRET  secret      optional, the DESK_SECRET printed by the bridge's setup()
//   NOTION_SOURCES        text        optional JSON list replacing DEFAULT_SOURCES
//   NOTION_TARGETS        text        optional JSON list replacing DEFAULT_TARGETS

export const VERSION = '2026.10.11';
export const LIMITS = {
  body: 4 * 1024 * 1024,
  doc: 256 * 1024,
  image: 1536 * 1024,
  importDocs: 500,
  rangeDays: 400,
  passphrase: 12,
  failuresPerKey: 8,
  failuresGlobal: 60,
};
const TOKEN_DAYS = 120;
const NOTION_API = 'https://api.notion.com/v1';
const NOTION_VERSION = '2025-09-03';
const COLLECTION_RE = /^(entries|tasks|settings|images)$/;
const ID_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const GOOGLE_ACTIONS = ['createEvent', 'createTask', 'setTask'];

// Notion data sources whose dated rows become deadlines on the desk. `done`
// lists the status values after which a date no longer needs attention.
export const DEFAULT_SOURCES = [
  { id: 'e53afef4-a52d-4aa6-a0c2-23a2490a7fde', label: 'Publications', date: 'Deadline', status: 'Status', done: ['Accepted', 'Rejected'] },
  { id: '7b63f21a-ea6a-4f9b-b91d-3769c4e02fcf', label: 'Opportunities', date: 'Deadline', status: 'Status',
    done: ['Applied', 'Interviewing', 'Offer', 'Accepted', 'Waitlisted', 'Rejected', 'Declined'] },
  { id: '21116060-ed74-4ba6-a9e4-f8a952d6424a', label: 'Projects', date: 'Deadline', status: 'Stage', done: ['Shipped'] },
  { id: '086a6332-af9f-401b-b025-32bcd01e6c05', label: 'Milestones', date: 'Target', status: 'Status', done: ['Done', 'Dropped'] },
  { id: '70ab5a2e-e301-47f9-b857-93b2b41b48dd', label: 'Follow-ups', date: 'Next Follow-up' },
];
// Notion data sources an entry can be sent to.
export const DEFAULT_TARGETS = [
  { id: '5df9a8fe-83bc-4b35-865c-186120e4b97d', label: 'Ideas' },
  { id: '412a7892-d1d1-43e0-a3b6-ed61c456680d', label: 'Research Roadmap' },
  { id: '086a6332-af9f-401b-b025-32bcd01e6c05', label: 'Career Milestones' },
];

export default {
  fetch(request, env) {
    return handle(request, env, fetch);
  },
};

class HttpError extends Error {
  constructor(status, message, extra) {
    super(message);
    this.status = status;
    this.extra = extra;
  }
}

// ---------------------------------------------------------------- routing --

export async function handle(request, env, fetchImpl, now = Date.now()) {
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
  if (origin && !allowed.includes(origin)) return new Response('Forbidden', { status: 403 });
  const cors = origin ? {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  } : {};
  const reply = (status, body) => new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

  const url = new URL(request.url);
  const parts = url.pathname.split('/').filter(Boolean);
  const ctx = { request, env, fetchImpl, now, url, parts };
  try {
    if (parts[0] === 'health' && request.method === 'GET') return reply(200, health(env));
    if (parts[0] === 'auth' && request.method === 'POST') return reply(200, await login(ctx));
    await requireToken(ctx);
    return reply(200, await route(ctx));
  } catch (err) {
    if (err instanceof HttpError) return reply(err.status, { ok: false, error: err.message, ...(err.extra || {}) });
    console.error('desk: unhandled', err && err.stack ? err.stack : err);
    return reply(500, { ok: false, error: 'The desk server failed. Check Worker > Logs.' });
  }
}

async function route(ctx) {
  const { request, parts } = ctx;
  const m = request.method;
  const [head, a, b, c, d] = parts;
  if (head === 'session' && m === 'GET') return { ok: true, configured: configured(ctx.env) };
  if (head === 'sync' && m === 'GET') return sync(ctx);
  if (head === 'export' && m === 'GET') return exportAll(ctx);
  if (head === 'import' && m === 'POST') return importDocs(ctx);
  if (head === 'google' && m === 'POST') return googleAction(ctx);
  if (head === 'notion' && a === 'targets' && m === 'GET') return notionTargets(ctx);
  if (head === 'notion' && a === 'schema' && m === 'GET') return notionSchema(ctx, ctx.url.searchParams.get('id'));
  if (head === 'notion' && a === 'pages' && m === 'POST') return notionCreate(ctx);
  if (head === 'docs' && a) {
    checkCollection(a);
    if (!b && m === 'GET') return listDocs(ctx, a);
    checkId(b);
    if (!c && m === 'GET') return { ok: true, doc: await getDoc(ctx.env.DB, a, b) };
    if (!c && m === 'PUT') return putDoc(ctx, a, b);
    if (!c && m === 'DELETE') return deleteDoc(ctx, a, b);
    if (c === 'revisions' && !d && m === 'GET') return listRevisions(ctx, a, b);
    if (c === 'revisions' && d && m === 'GET') return getRevision(ctx, a, b, Number(d));
  }
  throw new HttpError(404, 'No such route.');
}

function health(env) {
  return { ok: true, service: 'desk', version: VERSION, configured: configured(env) };
}

function configured(env) {
  return {
    db: !!env.DB,
    passphrase: String(env.DESK_PASSPHRASE || '').length >= LIMITS.passphrase,
    notion: !!env.NOTION_TOKEN,
    google: !!(env.GOOGLE_BRIDGE_URL && env.GOOGLE_BRIDGE_SECRET),
  };
}

async function readJson(request, limit = LIMITS.body) {
  if (!(request.headers.get('Content-Type') || '').toLowerCase().startsWith('application/json')) {
    throw new HttpError(415, 'Send JSON.');
  }
  const raw = await request.text();
  if (raw.length > limit) throw new HttpError(413, 'That request is too large.');
  try {
    const data = JSON.parse(raw);
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('not an object');
    return data;
  } catch {
    throw new HttpError(400, 'The request body is not valid JSON.');
  }
}

function checkCollection(name) {
  if (!COLLECTION_RE.test(name || '')) throw new HttpError(404, 'Unknown collection.');
}
function checkId(id) {
  if (!ID_RE.test(id || '')) throw new HttpError(400, 'Invalid document id.');
}

// ------------------------------------------------------------------- auth --

const enc = new TextEncoder();

function b64url(bytes) {
  let s = '';
  for (const b of new Uint8Array(bytes)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function fromB64url(str) {
  const s = atob(str.replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(s, ch => ch.charCodeAt(0));
}

async function sha256(text) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(text)));
}

function sameBytes(x, y) {
  if (x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

// The signing key is derived from the passphrase, so rotating the passphrase
// revokes every token already handed out.
function signingKey(passphrase) {
  return crypto.subtle.importKey('raw', enc.encode(passphrase + '|desk-token-v1'),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}

export async function issueToken(passphrase, now) {
  const payload = b64url(enc.encode(JSON.stringify({ v: 1, iat: now, exp: now + TOKEN_DAYS * 864e5 })));
  const sig = await crypto.subtle.sign('HMAC', await signingKey(passphrase), enc.encode(payload));
  return { token: payload + '.' + b64url(sig), exp: now + TOKEN_DAYS * 864e5 };
}

export async function verifyToken(passphrase, token, now) {
  const [payload, sig] = String(token || '').split('.');
  if (!payload || !sig) return false;
  let good = false;
  try {
    good = await crypto.subtle.verify('HMAC', await signingKey(passphrase), fromB64url(sig), enc.encode(payload));
  } catch {
    return false;
  }
  if (!good) return false;
  try {
    const claims = JSON.parse(new TextDecoder().decode(fromB64url(payload)));
    return claims.v === 1 && typeof claims.exp === 'number' && claims.exp > now;
  } catch {
    return false;
  }
}

function passphraseOf(env) {
  const p = String(env.DESK_PASSPHRASE || '');
  if (p.length < LIMITS.passphrase) {
    throw new HttpError(503, 'The desk is not set up: DESK_PASSPHRASE is missing or shorter than ' + LIMITS.passphrase + ' characters.');
  }
  if (!env.DB) throw new HttpError(503, 'The desk is not set up: bind a D1 database as DB.');
  return p;
}

async function requireToken(ctx) {
  const pass = passphraseOf(ctx.env);
  const auth = ctx.request.headers.get('Authorization') || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!(await verifyToken(pass, token, ctx.now))) throw new HttpError(401, 'Sign in again.');
  await ensureSchema(ctx.env.DB);
}

async function login(ctx) {
  const pass = passphraseOf(ctx.env);
  const db = ctx.env.DB;
  await ensureSchema(db);
  const ip = ctx.request.headers.get('CF-Connecting-IP') || 'unknown';
  const key = b64url((await sha256('desk-ip|' + ip)).slice(0, 12));
  const since = ctx.now - 15 * 60e3;
  const mine = await db.prepare('SELECT COUNT(*) AS n FROM login_failures WHERE key = ? AND at > ?').bind(key, since).first();
  const all = await db.prepare('SELECT COUNT(*) AS n FROM login_failures WHERE at > ?').bind(ctx.now - 60 * 60e3).first();
  if ((mine && mine.n >= LIMITS.failuresPerKey) || (all && all.n >= LIMITS.failuresGlobal)) {
    throw new HttpError(429, 'Too many wrong attempts. Wait 15 minutes, then try again.');
  }
  const body = await readJson(ctx.request, 4096);
  const given = typeof body.passphrase === 'string' ? body.passphrase : '';
  if (!sameBytes(await sha256(given), await sha256(pass))) {
    await db.prepare('INSERT INTO login_failures (key, at) VALUES (?, ?)').bind(key, ctx.now).run();
    await db.prepare('DELETE FROM login_failures WHERE at < ?').bind(ctx.now - 864e5).run();
    throw new HttpError(401, 'That passphrase is not right.');
  }
  await db.prepare('DELETE FROM login_failures WHERE key = ?').bind(key).run();
  return { ok: true, ...(await issueToken(pass, ctx.now)), configured: configured(ctx.env) };
}

// ------------------------------------------------------------------ store --

const schemaReady = new WeakSet();

export async function ensureSchema(db) {
  if (schemaReady.has(db)) return;
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS docs (
      collection TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, version INTEGER NOT NULL,
      updated_at TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (collection, id))`),
    db.prepare(`CREATE TABLE IF NOT EXISTS revisions (
      collection TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL, data TEXT NOT NULL,
      saved_at TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (collection, id, version))`),
    db.prepare('CREATE TABLE IF NOT EXISTS login_failures (key TEXT NOT NULL, at INTEGER NOT NULL)'),
    db.prepare('CREATE INDEX IF NOT EXISTS login_failures_at ON login_failures (key, at)'),
  ]);
  schemaReady.add(db);
}

function rowToDoc(row) {
  if (!row) return null;
  return {
    collection: row.collection, id: row.id, version: row.version,
    updatedAt: row.updated_at, deleted: !!row.deleted, data: JSON.parse(row.data),
  };
}

async function getDoc(db, collection, id) {
  const row = await db.prepare('SELECT * FROM docs WHERE collection = ? AND id = ?').bind(collection, id).first();
  const doc = rowToDoc(row);
  if (!doc || doc.deleted) throw new HttpError(404, 'Not found.');
  return doc;
}

async function listDocs(ctx, collection) {
  const res = await ctx.env.DB.prepare(
    'SELECT * FROM docs WHERE collection = ? AND deleted = 0 ORDER BY updated_at DESC LIMIT 5000',
  ).bind(collection).all();
  return { ok: true, docs: (res.results || []).map(rowToDoc) };
}

// One write path for edits, deletes and imports. `base` is the version the
// client last saw; a mismatch means another device saved in between, and the
// client gets the current document back instead of silently overwriting it.
export async function writeDoc(db, collection, id, data, { base = null, deleted = false, nowIso }) {
  const text = JSON.stringify(data ?? {});
  const cap = collection === 'images' ? LIMITS.image : LIMITS.doc;
  if (text.length > cap) throw new HttpError(413, 'That document is larger than ' + Math.round(cap / 1024) + ' KB.');
  const cur = await db.prepare('SELECT * FROM docs WHERE collection = ? AND id = ?').bind(collection, id).first();
  if (cur && base !== null && base !== undefined && Number(base) !== cur.version) {
    throw new HttpError(409, 'Changed on another device.', { doc: rowToDoc(cur) });
  }
  if (!cur && deleted) throw new HttpError(404, 'Not found.');
  const version = (cur ? cur.version : 0) + 1;
  const stmts = [
    db.prepare(`INSERT INTO docs (collection, id, data, version, updated_at, deleted) VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT (collection, id) DO UPDATE SET data = excluded.data, version = excluded.version,
      updated_at = excluded.updated_at, deleted = excluded.deleted`)
      .bind(collection, id, text, version, nowIso, deleted ? 1 : 0),
  ];
  // Images never change after upload, so they carry no history.
  if (collection !== 'images') {
    stmts.push(db.prepare('INSERT INTO revisions (collection, id, version, data, saved_at, deleted) VALUES (?, ?, ?, ?, ?, ?)')
      .bind(collection, id, version, text, nowIso, deleted ? 1 : 0));
  }
  await db.batch(stmts);
  return { collection, id, version, updatedAt: nowIso, deleted, data: JSON.parse(text) };
}

async function putDoc(ctx, collection, id) {
  const body = await readJson(ctx.request);
  if (!body.data || typeof body.data !== 'object' || Array.isArray(body.data)) throw new HttpError(400, 'Send { data: {...} }.');
  const doc = await writeDoc(ctx.env.DB, collection, id, body.data, { base: body.baseVersion, nowIso: new Date(ctx.now).toISOString() });
  return { ok: true, doc };
}

async function deleteDoc(ctx, collection, id) {
  const cur = await getDoc(ctx.env.DB, collection, id);
  const base = ctx.url.searchParams.get('base');
  const doc = await writeDoc(ctx.env.DB, collection, id, cur.data,
    { base: base === null ? null : Number(base), deleted: true, nowIso: new Date(ctx.now).toISOString() });
  return { ok: true, doc };
}

async function listRevisions(ctx, collection, id) {
  const res = await ctx.env.DB.prepare(
    'SELECT version, saved_at, deleted, length(data) AS size FROM revisions WHERE collection = ? AND id = ? ORDER BY version DESC LIMIT 100',
  ).bind(collection, id).all();
  return {
    ok: true,
    revisions: (res.results || []).map(r => ({ version: r.version, savedAt: r.saved_at, deleted: !!r.deleted, size: r.size })),
  };
}

async function getRevision(ctx, collection, id, version) {
  if (!Number.isInteger(version) || version < 1) throw new HttpError(400, 'Invalid version.');
  const row = await ctx.env.DB.prepare('SELECT * FROM revisions WHERE collection = ? AND id = ? AND version = ?')
    .bind(collection, id, version).first();
  if (!row) throw new HttpError(404, 'No such version.');
  return { ok: true, revision: { version: row.version, savedAt: row.saved_at, deleted: !!row.deleted, data: JSON.parse(row.data) } };
}

async function exportAll(ctx) {
  const withImages = ctx.url.searchParams.get('images') === '1';
  const res = await ctx.env.DB.prepare(
    withImages ? 'SELECT * FROM docs WHERE deleted = 0' : "SELECT * FROM docs WHERE deleted = 0 AND collection <> 'images'",
  ).all();
  const docs = {};
  for (const d of (res.results || []).map(rowToDoc)) (docs[d.collection] ||= []).push({ id: d.id, version: d.version, updatedAt: d.updatedAt, data: d.data });
  return { ok: true, format: 'desk-export-v1', exportedAt: new Date(ctx.now).toISOString(), docs };
}

// Accepts the export format above or a flat list of { collection, id, data }.
async function importDocs(ctx) {
  const body = await readJson(ctx.request);
  let list = [];
  if (Array.isArray(body.docs)) list = body.docs;
  else if (body.docs && typeof body.docs === 'object') {
    for (const [collection, rows] of Object.entries(body.docs)) {
      if (Array.isArray(rows)) for (const r of rows) list.push({ collection, id: r.id, data: r.data });
    }
  }
  if (!list.length) throw new HttpError(400, 'Nothing to import.');
  if (list.length > LIMITS.importDocs) throw new HttpError(413, 'Import at most ' + LIMITS.importDocs + ' documents at a time.');
  const nowIso = new Date(ctx.now).toISOString();
  let written = 0, unchanged = 0;
  const skipped = [];
  for (const item of list) {
    if (!item || !COLLECTION_RE.test(item.collection || '') || !ID_RE.test(item.id || '') || !item.data || typeof item.data !== 'object') {
      skipped.push(String(item && item.id || '?'));
      continue;
    }
    const cur = await ctx.env.DB.prepare('SELECT data, deleted FROM docs WHERE collection = ? AND id = ?').bind(item.collection, item.id).first();
    if (cur && !cur.deleted && cur.data === JSON.stringify(item.data)) { unchanged++; continue; }
    await writeDoc(ctx.env.DB, item.collection, item.id, item.data, { nowIso });
    written++;
  }
  return { ok: true, written, unchanged, skipped };
}

// ------------------------------------------------------------------- sync --

function parseRange(params) {
  const from = params.get('from') || '';
  const to = params.get('to') || '';
  if (!DATE_RE.test(from) || !DATE_RE.test(to) || from > to) throw new HttpError(400, 'Give from and to as YYYY-MM-DD.');
  const days = (Date.parse(to) - Date.parse(from)) / 864e5;
  if (days > LIMITS.rangeDays) throw new HttpError(400, 'Ask for at most ' + LIMITS.rangeDays + ' days at once.');
  const timeMin = params.get('timeMin') || from + 'T00:00:00Z';
  const timeMax = params.get('timeMax') || to + 'T23:59:59Z';
  if (Number.isNaN(Date.parse(timeMin)) || Number.isNaN(Date.parse(timeMax))) throw new HttpError(400, 'Invalid timeMin or timeMax.');
  return { from, to, timeMin, timeMax, tz: (params.get('tz') || '').slice(0, 64) };
}

async function sync(ctx) {
  const range = parseRange(ctx.url.searchParams);
  const [google, notion] = await Promise.all([
    syncGoogle(ctx, range).catch(err => ({ configured: true, ok: false, error: errorText(err) })),
    syncNotion(ctx, range).catch(err => ({ configured: true, ok: false, error: errorText(err), sources: [] })),
  ]);
  return { ok: true, at: new Date(ctx.now).toISOString(), range: { from: range.from, to: range.to }, google, notion };
}

function errorText(err) {
  return err && err.message ? String(err.message).slice(0, 300) : 'Unknown error.';
}

// ----------------------------------------------------------------- google --

async function callBridge(ctx, payload) {
  const env = ctx.env;
  if (!env.GOOGLE_BRIDGE_URL || !env.GOOGLE_BRIDGE_SECRET) throw new HttpError(503, 'Google is not connected yet.');
  let res;
  try {
    res = await ctx.fetchImpl(env.GOOGLE_BRIDGE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ ...payload, secret: env.GOOGLE_BRIDGE_SECRET }),
      redirect: 'follow',
    });
  } catch {
    throw new HttpError(502, 'Google did not answer.');
  }
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    // Apps Script answers with an HTML page when the deployment is not public
    // or the script threw before reaching doPost.
    throw new HttpError(502, 'The Google bridge answered with a page, not data. Redeploy it with access "Anyone".');
  }
  if (!data || data.ok !== true) throw new HttpError(502, 'Google bridge: ' + ((data && data.error) || 'request refused.'));
  return data;
}

async function syncGoogle(ctx, range) {
  if (!ctx.env.GOOGLE_BRIDGE_URL || !ctx.env.GOOGLE_BRIDGE_SECRET) return { configured: false, ok: false };
  const data = await callBridge(ctx, { action: 'agenda', timeMin: range.timeMin, timeMax: range.timeMax, tz: range.tz });
  return {
    configured: true, ok: true,
    calendars: Array.isArray(data.calendars) ? data.calendars : [],
    events: Array.isArray(data.events) ? data.events : [],
    tasklists: Array.isArray(data.tasklists) ? data.tasklists : [],
    tasks: Array.isArray(data.tasks) ? data.tasks : [],
    warnings: Array.isArray(data.warnings) ? data.warnings : [],
  };
}

async function googleAction(ctx) {
  const body = await readJson(ctx.request, 64 * 1024);
  if (!GOOGLE_ACTIONS.includes(body.action)) throw new HttpError(400, 'Unknown Google action.');
  const data = await callBridge(ctx, body);
  delete data.secret;
  return data;
}

// ----------------------------------------------------------------- notion --

function sourcesOf(env, name, fallback) {
  if (!env[name]) return fallback;
  try {
    const list = JSON.parse(env[name]);
    if (Array.isArray(list)) return list.filter(s => s && typeof s.id === 'string' && typeof s.label === 'string');
  } catch {
    console.error('desk: ' + name + ' is not valid JSON; using the defaults');
  }
  return fallback;
}

async function notionFetch(ctx, path, init = {}) {
  if (!ctx.env.NOTION_TOKEN) throw new HttpError(503, 'Notion is not connected yet.');
  const res = await ctx.fetchImpl((ctx.env.NOTION_API || NOTION_API) + path, {
    ...init,
    headers: {
      Authorization: 'Bearer ' + ctx.env.NOTION_TOKEN,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data && data.message ? data.message : 'HTTP ' + res.status;
    if (res.status === 404) throw new HttpError(502, 'Notion cannot see this database. Add the integration under ••• > Connections on Research OS.');
    if (res.status === 401) throw new HttpError(502, 'Notion rejected the token. Check NOTION_TOKEN.');
    throw new HttpError(502, 'Notion: ' + msg);
  }
  return data;
}

function plainText(rich) {
  return Array.isArray(rich) ? rich.map(r => r.plain_text || '').join('') : '';
}

function propValue(p) {
  if (!p) return '';
  switch (p.type) {
    case 'title': return plainText(p.title);
    case 'rich_text': return plainText(p.rich_text);
    case 'select': return p.select ? p.select.name : '';
    case 'status': return p.status ? p.status.name : '';
    case 'multi_select': return (p.multi_select || []).map(o => o.name).join(', ');
    case 'url': return p.url || '';
    case 'number': return p.number == null ? '' : String(p.number);
    case 'checkbox': return p.checkbox ? 'yes' : '';
    case 'formula': return p.formula ? String(p.formula[p.formula.type] ?? '') : '';
    default: return '';
  }
}

export function notionRow(page, source) {
  const props = page.properties || {};
  const titleProp = Object.values(props).find(p => p && p.type === 'title');
  const date = source.date && props[source.date] && props[source.date].date;
  const status = source.status ? propValue(props[source.status]) : '';
  return {
    id: page.id,
    url: page.url || '',
    source: source.label,
    sourceId: source.id,
    title: titleProp ? plainText(titleProp.title) || '(untitled)' : '(untitled)',
    date: date ? date.start : '',
    end: date && date.end ? date.end : '',
    status,
    done: !!(status && Array.isArray(source.done) && source.done.includes(status)),
  };
}

async function querySource(ctx, source, range) {
  const filter = source.date
    ? { and: [{ property: source.date, date: { on_or_after: range.from } }, { property: source.date, date: { on_or_before: range.to } }] }
    : undefined;
  const rows = [];
  let cursor;
  for (let page = 0; page < 3; page++) {
    const body = { page_size: 100, ...(filter ? { filter, sorts: [{ property: source.date, direction: 'ascending' }] } : {}) };
    if (cursor) body.start_cursor = cursor;
    const data = await notionFetch(ctx, '/data_sources/' + source.id + '/query', { method: 'POST', body: JSON.stringify(body) });
    for (const p of data.results || []) if (!p.in_trash && !p.archived) rows.push(notionRow(p, source));
    if (!data.has_more || !data.next_cursor) break;
    cursor = data.next_cursor;
  }
  return rows;
}

async function syncNotion(ctx, range) {
  if (!ctx.env.NOTION_TOKEN) return { configured: false, ok: false, sources: [] };
  const sources = sourcesOf(ctx.env, 'NOTION_SOURCES', DEFAULT_SOURCES);
  const results = await Promise.all(sources.map(s => querySource(ctx, s, range)
    .then(rows => ({ id: s.id, label: s.label, rows }))
    .catch(err => ({ id: s.id, label: s.label, rows: [], error: errorText(err) }))));
  return { configured: true, ok: results.some(r => !r.error), sources: results };
}

function notionTargets(ctx) {
  return { ok: true, targets: sourcesOf(ctx.env, 'NOTION_TARGETS', DEFAULT_TARGETS), notion: !!ctx.env.NOTION_TOKEN };
}

const EDITABLE = ['title', 'rich_text', 'select', 'status', 'multi_select', 'date', 'url', 'number', 'checkbox'];

async function notionSchema(ctx, id) {
  if (!/^[0-9a-f-]{32,36}$/i.test(id || '')) throw new HttpError(400, 'Invalid data source id.');
  const ds = await notionFetch(ctx, '/data_sources/' + id);
  const fields = Object.entries(ds.properties || {})
    .filter(([, p]) => EDITABLE.includes(p.type))
    .map(([name, p]) => ({
      name, type: p.type,
      options: ((p[p.type] && p[p.type].options) || []).map(o => o.name),
    }));
  return { ok: true, id, title: plainText(ds.title) || '', fields };
}

export function typedProperty(type, value) {
  const v = String(value ?? '').trim();
  if (!v) return null;
  const text = s => [{ type: 'text', text: { content: s.slice(0, 2000) } }];
  switch (type) {
    case 'title': return { title: text(v) };
    case 'rich_text': return { rich_text: text(v) };
    case 'select': return { select: { name: v.slice(0, 100) } };
    case 'status': return { status: { name: v.slice(0, 100) } };
    case 'multi_select': return { multi_select: v.split(',').map(s => s.trim()).filter(Boolean).slice(0, 20).map(name => ({ name })) };
    case 'date': return DATE_RE.test(v) || !Number.isNaN(Date.parse(v)) ? { date: { start: v } } : null;
    case 'url': return /^https?:\/\//i.test(v) ? { url: v } : null;
    case 'number': return Number.isFinite(Number(v)) ? { number: Number(v) } : null;
    case 'checkbox': return { checkbox: v === 'true' || v === 'yes' || v === '1' };
    default: return null;
  }
}

// Plain-text body to Notion blocks: "## " headings, "- " bullets, paragraphs.
export function markdownBlocks(md) {
  const blocks = [];
  const rich = s => {
    const out = [];
    for (let i = 0; i < s.length && out.length < 50; i += 2000) out.push({ type: 'text', text: { content: s.slice(i, i + 2000) } });
    return out;
  };
  for (const chunk of String(md || '').split(/\n{2,}/)) {
    const t = chunk.trim();
    if (!t) continue;
    if (t.startsWith('## ')) blocks.push({ object: 'block', type: 'heading_2', heading_2: { rich_text: rich(t.slice(3)) } });
    else if (t.split('\n').every(l => l.startsWith('- '))) {
      for (const l of t.split('\n')) blocks.push({ object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich(l.slice(2)) } });
    } else blocks.push({ object: 'block', type: 'paragraph', paragraph: { rich_text: rich(t) } });
    if (blocks.length >= 90) break;
  }
  return blocks;
}

async function notionCreate(ctx) {
  const body = await readJson(ctx.request, 128 * 1024);
  const targets = sourcesOf(ctx.env, 'NOTION_TARGETS', DEFAULT_TARGETS);
  const target = targets.find(t => t.id === body.target);
  if (!target) throw new HttpError(400, 'Unknown Notion target.');
  const ds = await notionFetch(ctx, '/data_sources/' + target.id);
  const schema = ds.properties || {};
  const properties = {};
  const titleName = Object.keys(schema).find(k => schema[k].type === 'title');
  if (!titleName) throw new HttpError(502, 'That Notion database has no title column.');
  properties[titleName] = typedProperty('title', body.title || 'Untitled');
  for (const [name, value] of Object.entries(body.fields || {})) {
    if (name === titleName || !schema[name]) continue;
    const typed = typedProperty(schema[name].type, value);
    if (typed) properties[name] = typed;
  }
  const page = await notionFetch(ctx, '/pages', {
    method: 'POST',
    body: JSON.stringify({
      parent: { type: 'data_source_id', data_source_id: target.id },
      properties,
      children: markdownBlocks(body.body),
    }),
  });
  return { ok: true, id: page.id, url: page.url || '' };
}
