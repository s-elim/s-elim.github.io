/**
 * Research Desk backend: one Google Apps Script web app, running as the owner.
 *
 * It stores the desk in a Google Sheet ("Research Desk data", one row per
 * document plus a revision row per save), reads and edits Google Calendar and
 * Google Tasks, reads dated rows from Notion and creates new ones, and keeps
 * attached images in a Drive folder. The page at s-elim.github.io/desk/ talks to
 * it with plain POST requests.
 *
 * Modes (Script Properties):
 *   DESK_MODE        "open" (default): anyone can read and edit. Writes are
 *                    metered per minute and per day, deletes are soft, every
 *                    save keeps a revision, call links never leave this script.
 *                    "private": every action except health and auth needs a
 *                    token issued for DESK_PASSPHRASE.
 *   DESK_PASSPHRASE  private mode only, at least 12 characters.
 *   NOTION_TOKEN     optional, a Notion internal integration secret.
 *   NOTION_SOURCES / NOTION_TARGETS  optional JSON overriding the lists below.
 *
 * Install: see README.md beside this file (paste, Run setup, Deploy).
 */

var VERSION = '2026.10.12';
var LIMITS = {
  doc: 45000,               // a Sheets cell holds 50,000 characters
  importDocs: 500,
  rangeDays: 400,
  passphrase: 12,
  writesPerMinute: 60,
  writesPerDay: 3000,
  imagesPerDay: 60,
  imageBase64: 2.2e6,       // about 1.6 MB of image
  failedLogins: 20,         // per 15 minutes, everyone together
  syncFreshMs: 60e3,        // one shared Google + Notion answer per minute
  syncForceGapMs: 10e3,     // a forced refresh at most every 10 seconds
  cacheChunk: 90000         // CacheService keeps at most 100 KB per key
};
var COLLECTIONS = ['entries', 'tasks', 'settings'];
var ID_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
var TIME_RE = /^\d{2}:\d{2}$/;
var NOTION_API = 'https://api.notion.com/v1';
var NOTION_VERSION = '2025-09-03';
var TOKEN_DAYS = 120;
var CALL_LINK_RE = /https?:\/\/[^\s<>"']*(meet\.google\.com|zoom\.us|teams\.microsoft\.com|teams\.live\.com|webex\.com|whereby\.com)[^\s<>"']*/gi;
var DOC_SHEET = 'docs', REV_SHEET = 'revisions';
var HEADER = ['collection', 'id', 'version', 'updated_at', 'deleted', 'data'];

// Notion data sources whose dated rows become deadlines; `done` lists the
// statuses after which a date no longer needs attention.
var DEFAULT_SOURCES = [
  { id: 'e53afef4-a52d-4aa6-a0c2-23a2490a7fde', label: 'Publications', date: 'Deadline', status: 'Status', done: ['Accepted', 'Rejected'] },
  { id: '7b63f21a-ea6a-4f9b-b91d-3769c4e02fcf', label: 'Opportunities', date: 'Deadline', status: 'Status',
    done: ['Applied', 'Interviewing', 'Offer', 'Accepted', 'Waitlisted', 'Rejected', 'Declined'] },
  { id: '21116060-ed74-4ba6-a9e4-f8a952d6424a', label: 'Projects', date: 'Deadline', status: 'Stage', done: ['Shipped'] },
  { id: '086a6332-af9f-401b-b025-32bcd01e6c05', label: 'Milestones', date: 'Target', status: 'Status', done: ['Done', 'Dropped'] },
  { id: '70ab5a2e-e301-47f9-b857-93b2b41b48dd', label: 'Follow-ups', date: 'Next Follow-up' }
];
// Notion data sources an entry can be sent to.
var DEFAULT_TARGETS = [
  { id: '5df9a8fe-83bc-4b35-865c-186120e4b97d', label: 'Ideas' },
  { id: '412a7892-d1d1-43e0-a3b6-ed61c456680d', label: 'Research Roadmap' },
  { id: '086a6332-af9f-401b-b025-32bcd01e6c05', label: 'Career Milestones' }
];

// Tests replace this.
var clock = function () { return Date.now(); };

/* ======================================================================
   Setup and entry points
   ====================================================================== */

/** Run once from the editor. Creates the Sheet and the image folder and asks for permissions. */
function setup() {
  var props = PropertiesService.getScriptProperties();
  var ss = null;
  if (props.getProperty('SHEET_ID')) {
    try { ss = SpreadsheetApp.openById(props.getProperty('SHEET_ID')); } catch (err) { ss = null; }
  }
  if (!ss) {
    ss = SpreadsheetApp.create('Research Desk data');
    props.setProperty('SHEET_ID', ss.getId());
  }
  [DOC_SHEET, REV_SHEET].forEach(function (name, i) {
    var sh = ss.getSheetByName(name);
    if (!sh) {
      sh = i === 0 && ss.getSheets().length === 1 && ss.getSheets()[0].getLastRow() === 0 ? ss.getSheets()[0] : ss.insertSheet(name);
      sh.setName(name);
    }
    // Plain text everywhere, so Sheets never turns a version or a date into a number.
    sh.getRange('A:F').setNumberFormat('@');
    if (sh.getLastRow() === 0) sh.appendRow(HEADER);
    sh.setFrozenRows(1);
  });
  if (!props.getProperty('IMAGE_FOLDER_ID')) props.setProperty('IMAGE_FOLDER_ID', DriveApp.createFolder('Research Desk images').getId());
  // Touch every service once so the permission prompt covers them all now.
  Calendar.CalendarList.list({ maxResults: 1 });
  Tasks.Tasklists.list({ maxResults: 1 });
  Logger.log('Ready. Data: ' + ss.getUrl() + ' · mode: ' + mode() + ' · Notion: ' + (props.getProperty('NOTION_TOKEN') ? 'token set' : 'not set'));
}

function doGet(e) {
  var action = (e && e.parameter && e.parameter.action) || 'health';
  return json(action === 'health' ? health() : { ok: false, status: 405, error: 'Use POST.' });
}

function doPost(e) {
  var req;
  try {
    req = JSON.parse((e && e.postData && e.postData.contents) || '{}');
  } catch (err) {
    return json({ ok: false, status: 400, error: 'The request was not JSON.' });
  }
  return json(handle(req));
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function fail(status, message, extra) {
  var err = new Error(message);
  err.status = status;
  err.extra = extra;
  return err;
}

var ACTIONS = {
  load: load, list: list, get: getOne, put: put, 'delete': remove, revisions: revisions, revision: revision,
  restore: restore, 'export': exportAll, 'import': importDocs, sync: sync,
  createEvent: createEvent, updateEvent: updateEvent, deleteEvent: deleteEvent,
  createTask: createTask, setTask: setTask, deleteTask: deleteTask,
  notionTargets: notionTargets, notionSchema: notionSchema, notionCreate: notionCreate,
  uploadImage: uploadImage
};
var GOOGLE_WRITES = { createEvent: 1, updateEvent: 1, deleteEvent: 1, createTask: 1, setTask: 1, deleteTask: 1 };
var WRITES = { put: 1, 'delete': 1, restore: 1, 'import': 1, createEvent: 1, updateEvent: 1, deleteEvent: 1,
  createTask: 1, setTask: 1, deleteTask: 1, notionCreate: 1, uploadImage: 1 };

function handle(req) {
  try {
    if (!req || typeof req !== 'object') throw fail(400, 'Send a JSON object.');
    var action = String(req.action || '');
    if (action === 'health') return health();
    if (action === 'auth') return login(req);
    if (mode() === 'private') requireToken(req);
    var fn = ACTIONS.hasOwnProperty(action) ? ACTIONS[action] : null;
    if (!fn) throw fail(404, 'Unknown action.');
    if (!WRITES[action]) return fn(req);
    return withLock(function () {
      spendWrites(1);
      var out = fn(req);
      if (GOOGLE_WRITES[action]) bumpSync();
      return out;
    });
  } catch (err) {
    if (err && err.status) {
      var out = { ok: false, status: err.status, error: err.message };
      if (err.extra) for (var k in err.extra) out[k] = err.extra[k];
      return out;
    }
    console.error('desk: ' + (err && err.stack ? err.stack : err));
    return { ok: false, status: 500, error: 'The desk backend failed: ' + String((err && err.message) || err).slice(0, 200) };
  }
}

// A calendar or task change makes the shared snapshot stale; the next sync
// rebuilds it instead of waiting out the minute.
function bumpSync() {
  var cache = CacheService.getScriptCache();
  cache.put('sync:gen', String(Number(cache.get('sync:gen') || 0) + 1), 21600);
}

function prop(name) { return PropertiesService.getScriptProperties().getProperty(name); }
function mode() { return String(prop('DESK_MODE') || 'open').trim().toLowerCase() === 'private' ? 'private' : 'open'; }

function health() {
  return {
    ok: true, service: 'desk', version: VERSION, mode: mode(),
    configured: { sheet: !!prop('SHEET_ID'), notion: !!prop('NOTION_TOKEN'), google: true, images: !!prop('IMAGE_FOLDER_ID') }
  };
}

function withLock(fn) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) throw fail(503, 'The desk is busy. Try again in a moment.');
  try { return fn(); } finally { lock.releaseLock(); }
}

// Anyone may edit in open mode, so writes are metered. Apps Script cannot see
// the caller's address, so the meter is shared: per minute against bursts, per
// day so a script cannot use up the owner's quotas.
function spendWrites(n) {
  var cache = CacheService.getScriptCache(), props = PropertiesService.getScriptProperties();
  var t = clock(), minKey = 'w:m:' + Math.floor(t / 6e4), dayKey = 'w:d:' + Math.floor(t / 864e5);
  var m = Number(cache.get(minKey) || 0) + n;
  cache.put(minKey, String(m), 120);
  var d = Number(props.getProperty(dayKey) || 0) + n;
  props.setProperty(dayKey, String(d));
  if (d === n) pruneProps('w:d:', dayKey);
  if (m > LIMITS.writesPerMinute) throw fail(429, 'Too many changes in the last minute. Wait a moment.');
  if (d > LIMITS.writesPerDay) throw fail(429, 'The desk has taken its changes for today. It opens again tomorrow (UTC).');
}

function pruneProps(prefix, keep) {
  var props = PropertiesService.getScriptProperties();
  props.getKeys().forEach(function (k) { if (k.indexOf(prefix) === 0 && k !== keep) props.deleteProperty(k); });
}

/* ======================================================================
   Private mode: passphrase and tokens
   ====================================================================== */

function passphrase() {
  var p = String(prop('DESK_PASSPHRASE') || '');
  if (p.length < LIMITS.passphrase) throw fail(503, 'Private mode needs DESK_PASSPHRASE (12+ characters) in Script Properties.');
  return p;
}

function b64(bytesOrText) { return Utilities.base64EncodeWebSafe(bytesOrText).replace(/=+$/, ''); }
function signToken(pass, payload) { return b64(Utilities.computeHmacSha256Signature(payload, pass + '|desk-token-v1')); }

function issueToken(pass) {
  var exp = clock() + TOKEN_DAYS * 864e5;
  var payload = b64(JSON.stringify({ v: 1, exp: exp }));
  return { token: payload + '.' + signToken(pass, payload), exp: exp };
}

function verifyToken(pass, token) {
  var parts = String(token || '').split('.');
  if (parts.length !== 2 || signToken(pass, parts[0]) !== parts[1]) return false;
  try {
    var pad = parts[0] + '==='.slice((parts[0].length + 3) % 4);
    var claims = JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(pad)).getDataAsString());
    return claims.v === 1 && claims.exp > clock();
  } catch (err) {
    return false;
  }
}

function requireToken(req) {
  if (!verifyToken(passphrase(), req.token)) throw fail(401, 'Sign in again.');
}

function login(req) {
  if (mode() !== 'private') return { ok: true, token: '', exp: 0, mode: 'open' };
  var pass = passphrase();
  var cache = CacheService.getScriptCache(), key = 'auth:fail:' + Math.floor(clock() / 9e5);
  var fails = Number(cache.get(key) || 0);
  if (fails >= LIMITS.failedLogins) throw fail(429, 'Too many wrong attempts. Wait 15 minutes.');
  if (String(req.passphrase || '') !== pass) {
    cache.put(key, String(fails + 1), 1000);
    throw fail(401, 'That passphrase is not right.');
  }
  var t = issueToken(pass);
  return { ok: true, token: t.token, exp: t.exp, mode: 'private' };
}

/* ======================================================================
   Documents in the Sheet
   ====================================================================== */

function sheet(name) {
  var id = prop('SHEET_ID');
  if (!id) throw fail(503, 'Run setup() in the Apps Script editor first.');
  var sh = SpreadsheetApp.openById(id).getSheetByName(name);
  if (!sh) throw fail(503, 'The "' + name + '" tab is missing from the desk Sheet. Run setup() again.');
  return sh;
}

function readRows() {
  var sh = sheet(DOC_SHEET), last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, 6).getValues().map(function (r, i) {
    return { row: i + 2, collection: String(r[0]), id: String(r[1]), version: Number(r[2]) || 0,
      updatedAt: String(r[3]), deleted: String(r[4]) === '1', text: String(r[5]) };
  });
}

function toDoc(r) {
  var data;
  try { data = JSON.parse(r.text || '{}'); } catch (err) { data = {}; }
  return { collection: r.collection, id: r.id, version: r.version, updatedAt: r.updatedAt, deleted: r.deleted, data: data };
}

function checkCollection(c) { if (COLLECTIONS.indexOf(c) === -1) throw fail(404, 'Unknown collection.'); }
function checkId(id) { if (!ID_RE.test(String(id || ''))) throw fail(400, 'Invalid document id.'); }

function findRow(rows, collection, id) {
  for (var i = 0; i < rows.length; i++) if (rows[i].collection === collection && rows[i].id === id) return rows[i];
  return null;
}

// The one write path. `base` is the version the editor last saw: a mismatch
// means someone else saved in between, and the caller gets their copy back
// instead of silently overwriting it.
function writeDoc(collection, id, data, opts) {
  opts = opts || {};
  var text = JSON.stringify(data || {});
  if (text.length > LIMITS.doc) throw fail(413, 'That entry is too long to store (limit about ' + Math.round(LIMITS.doc / 1000) + ' thousand characters).');
  var rows = opts.rows || readRows();
  var cur = findRow(rows, collection, id);
  if (cur && opts.base !== null && opts.base !== undefined && opts.base !== '' && Number(opts.base) !== cur.version) {
    throw fail(409, 'Changed by someone else a moment ago.', { doc: toDoc(cur) });
  }
  if (!cur && opts.deleted) throw fail(404, 'Not found.');
  var version = (cur ? cur.version : 0) + 1;
  var now = new Date(clock()).toISOString();
  var row = [collection, id, String(version), now, opts.deleted ? '1' : '0', text];
  var sh = sheet(DOC_SHEET);
  if (cur) {
    sh.getRange(cur.row, 1, 1, 6).setValues([row]);
    cur.version = version; cur.updatedAt = now; cur.deleted = !!opts.deleted; cur.text = text;
  } else {
    sh.appendRow(row);
    rows.push({ row: sh.getLastRow(), collection: collection, id: id, version: version, updatedAt: now, deleted: !!opts.deleted, text: text });
  }
  sheet(REV_SHEET).appendRow(row);
  return { collection: collection, id: id, version: version, updatedAt: now, deleted: !!opts.deleted, data: JSON.parse(text) };
}

function docsOf(rows, collection, deleted) {
  return rows.filter(function (r) { return r.collection === collection && r.deleted === !!deleted; })
    .map(toDoc).sort(function (a, b) { return a.updatedAt < b.updatedAt ? 1 : -1; });
}

function list(req) {
  checkCollection(req.collection);
  return { ok: true, docs: docsOf(readRows(), req.collection, !!req.deleted) };
}

function getOne(req) {
  checkCollection(req.collection); checkId(req.id);
  var r = findRow(readRows(), req.collection, req.id);
  if (!r || r.deleted) throw fail(404, 'Not found.');
  return { ok: true, doc: toDoc(r) };
}

function put(req) {
  checkCollection(req.collection); checkId(req.id);
  if (!req.data || typeof req.data !== 'object' || Array.isArray(req.data)) throw fail(400, 'Send { data: {...} }.');
  return { ok: true, doc: writeDoc(req.collection, req.id, req.data, { base: req.baseVersion }) };
}

function remove(req) {
  checkCollection(req.collection); checkId(req.id);
  var rows = readRows(), cur = findRow(rows, req.collection, req.id);
  if (!cur || cur.deleted) throw fail(404, 'Not found.');
  return { ok: true, doc: writeDoc(req.collection, req.id, toDoc(cur).data, { base: req.base, deleted: true, rows: rows }) };
}

function revisionRows(collection, id) {
  var sh = sheet(REV_SHEET), last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, 6).getValues()
    .filter(function (r) { return String(r[0]) === collection && String(r[1]) === id; })
    .map(function (r) { return { version: Number(r[2]), savedAt: String(r[3]), deleted: String(r[4]) === '1', text: String(r[5]) }; })
    .sort(function (a, b) { return b.version - a.version; });
}

function revisions(req) {
  checkCollection(req.collection); checkId(req.id);
  return { ok: true, revisions: revisionRows(req.collection, req.id).slice(0, 100).map(function (r) {
    return { version: r.version, savedAt: r.savedAt, deleted: r.deleted, size: r.text.length };
  }) };
}

function revision(req) {
  checkCollection(req.collection); checkId(req.id);
  var hit = revisionRows(req.collection, req.id).filter(function (r) { return r.version === Number(req.version); })[0];
  if (!hit) throw fail(404, 'No such version.');
  return { ok: true, revision: { version: hit.version, savedAt: hit.savedAt, deleted: hit.deleted, data: JSON.parse(hit.text) } };
}

// Undo a delete, or any unwanted edit: the newest live revision becomes a new version.
function restore(req) {
  checkCollection(req.collection); checkId(req.id);
  var live = revisionRows(req.collection, req.id).filter(function (r) { return !r.deleted; })[0];
  if (!live) throw fail(404, 'Nothing to restore.');
  return { ok: true, doc: writeDoc(req.collection, req.id, JSON.parse(live.text), {}) };
}

function load(req) {
  var rows = readRows(), docs = {};
  COLLECTIONS.forEach(function (c) { docs[c] = docsOf(rows, c, false); });
  return { ok: true, mode: mode(), docs: docs, sync: req.sync ? sync(req.sync) : null };
}

function exportAll() {
  var rows = readRows(), docs = {};
  COLLECTIONS.forEach(function (c) {
    docs[c] = docsOf(rows, c, false).map(function (d) { return { id: d.id, version: d.version, updatedAt: d.updatedAt, data: d.data }; });
  });
  return { ok: true, format: 'desk-export-v1', exportedAt: new Date(clock()).toISOString(), docs: docs };
}

// Accepts the export format above or a flat list of { collection, id, data }.
function importDocs(req) {
  var items = [];
  if (Array.isArray(req.docs)) items = req.docs;
  else if (req.docs && typeof req.docs === 'object') {
    Object.keys(req.docs).forEach(function (c) {
      (Array.isArray(req.docs[c]) ? req.docs[c] : []).forEach(function (r) { items.push({ collection: c, id: r && r.id, data: r && r.data }); });
    });
  }
  if (!items.length) throw fail(400, 'Nothing to import.');
  if (items.length > LIMITS.importDocs) throw fail(413, 'Import at most ' + LIMITS.importDocs + ' documents at a time.');
  spendWrites(items.length - 1);
  var rows = readRows(), written = 0, unchanged = 0, skipped = [];
  items.forEach(function (it) {
    if (!it || COLLECTIONS.indexOf(it.collection) === -1 || !ID_RE.test(String(it.id || '')) || !it.data || typeof it.data !== 'object') {
      skipped.push(String((it && it.id) || '?'));
      return;
    }
    var cur = findRow(rows, it.collection, it.id);
    if (cur && !cur.deleted && cur.text === JSON.stringify(it.data)) { unchanged++; return; }
    writeDoc(it.collection, it.id, it.data, { rows: rows });
    written++;
  });
  return { ok: true, written: written, unchanged: unchanged, skipped: skipped };
}

/* ======================================================================
   Sync: Google Calendar, Google Tasks and Notion, shared for a minute
   ====================================================================== */

function parseRange(r) {
  r = r || {};
  var from = String(r.from || ''), to = String(r.to || '');
  if (!DATE_RE.test(from) || !DATE_RE.test(to) || from > to) throw fail(400, 'Give from and to as YYYY-MM-DD.');
  if ((Date.parse(to) - Date.parse(from)) / 864e5 > LIMITS.rangeDays) throw fail(400, 'Ask for at most ' + LIMITS.rangeDays + ' days at once.');
  var timeMin = String(r.timeMin || from + 'T00:00:00Z'), timeMax = String(r.timeMax || to + 'T23:59:59Z');
  if (isNaN(Date.parse(timeMin)) || isNaN(Date.parse(timeMax))) throw fail(400, 'Invalid timeMin or timeMax.');
  return { from: from, to: to, timeMin: timeMin, timeMax: timeMax, tz: String(r.tz || '').slice(0, 64), fresh: !!r.fresh };
}

function cacheKey(parts) {
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, parts.join('|'));
  return 'sync:' + b64(bytes);
}

function sync(raw) {
  var r = parseRange(raw);
  var cache = CacheService.getScriptCache();
  var key = cacheKey([r.from, r.to, r.timeMin, r.timeMax, r.tz, mode(), cache.get('sync:gen') || '0']);
  var meta = cache.get(key + ':meta');
  if (meta) {
    meta = JSON.parse(meta);
    var age = clock() - meta.at;
    if (age < LIMITS.syncFreshMs && (!r.fresh || age < LIMITS.syncForceGapMs)) {
      var names = [];
      for (var i = 0; i < meta.n; i++) names.push(key + ':' + i);
      var got = cache.getAll(names), text = '';
      for (var j = 0; j < names.length && text !== null; j++) text = got[names[j]] === undefined || got[names[j]] === null ? null : text + got[names[j]];
      if (text) { var hit = JSON.parse(text); hit.cached = true; return hit; }
    }
  }
  var out = {
    ok: true, at: new Date(clock()).toISOString(), range: { from: r.from, to: r.to },
    google: guarded(function () { return agenda(r); }),
    notion: guarded(function () { return syncNotion(r); }, { sources: [] })
  };
  var body = JSON.stringify(out), chunks = {}, n = 0;
  for (var k = 0; k < body.length; k += LIMITS.cacheChunk) chunks[key + ':' + (n++)] = body.slice(k, k + LIMITS.cacheChunk);
  chunks[key + ':meta'] = JSON.stringify({ at: clock(), n: n });
  try { cache.putAll(chunks, 120); } catch (err) { console.warn('desk: sync cache skipped: ' + err); }
  return out;
}

function guarded(fn, extra) {
  try { return fn(); } catch (err) {
    var out = { configured: true, ok: false, error: String((err && err.message) || err).slice(0, 300) };
    if (extra) for (var k in extra) out[k] = extra[k];
    return out;
  }
}

function clip(s, n) {
  s = String(s == null ? '' : s);
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function stripHtml(s) {
  return String(s || '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&').trim();
}

// In open mode the calendar is public, so call links (which let anyone join a
// meeting) are removed here and never reach a browser.
function stripCallLinks(ev) {
  var clean = function (s) { return String(s || '').replace(CALL_LINK_RE, '[call link hidden]'); };
  var out = {};
  for (var k in ev) out[k] = ev[k];
  out.video = '';
  out.location = clean(ev.location);
  out.description = clean(ev.description);
  return out;
}

function eventOut(c, ev, palette) {
  var me = (ev.attendees || []).filter(function (a) { return a.self; })[0];
  var video = ev.hangoutLink || '';
  if (!video && ev.conferenceData && ev.conferenceData.entryPoints) {
    ev.conferenceData.entryPoints.forEach(function (p) { if (!video && p.entryPointType === 'video') video = p.uri; });
  }
  var out = {
    id: ev.id, calendarId: c.id, calendar: c.summaryOverride || c.summary || c.title || '',
    color: (ev.colorId && palette[ev.colorId] && palette[ev.colorId].background) || c.backgroundColor || c.color || '',
    title: ev.summary || '(no title)',
    start: ev.start.dateTime || ev.start.date,
    end: (ev.end && (ev.end.dateTime || ev.end.date)) || '',
    allDay: !ev.start.dateTime,
    location: clip(ev.location, 200), description: clip(stripHtml(ev.description), 800),
    link: ev.htmlLink || '', video: video, attendees: (ev.attendees || []).length,
    editable: c.accessRole === 'owner' || c.accessRole === 'writer' || c.writable === true,
    recurring: !!ev.recurringEventId, declined: !!(me && me.responseStatus === 'declined')
  };
  return mode() === 'open' ? stripCallLinks(out) : out;
}

function agenda(r) {
  var warnings = [], palette = {};
  try { palette = Calendar.Colors.get().event || {}; } catch (err) { warnings.push('colours: ' + err.message); }
  var timeMin = new Date(r.timeMin).toISOString(), timeMax = new Date(r.timeMax).toISOString();
  var calendars = (Calendar.CalendarList.list({ maxResults: 250 }).items || [])
    .filter(function (c) { return c.selected !== false && !c.hidden; });
  var events = [];
  calendars.forEach(function (c) {
    try {
      var token = null, n = 0;
      do {
        var page = Calendar.Events.list(c.id, { timeMin: timeMin, timeMax: timeMax, singleEvents: true, orderBy: 'startTime', maxResults: 250, pageToken: token || undefined });
        (page.items || []).forEach(function (ev) {
          if (ev.status === 'cancelled' || !ev.start) return;
          var out = eventOut(c, ev, palette);
          if (!out.declined) { events.push(out); n++; }
        });
        token = page.nextPageToken;
      } while (token && n < 500);
    } catch (err) {
      warnings.push((c.summary || c.id) + ': ' + err.message);
    }
  });
  var tasklists = [], tasks = [];
  try {
    tasklists = Tasks.Tasklists.list({ maxResults: 100 }).items || [];
    tasklists.forEach(function (l) {
      collectTasks(l, { showCompleted: false }, tasks, false);
      collectTasks(l, { showCompleted: true, showHidden: true, completedMin: timeMin, completedMax: timeMax }, tasks, true);
    });
  } catch (err) {
    warnings.push('Google Tasks: ' + err.message + ' (is the Tasks service on in appsscript.json?)');
  }
  return {
    configured: true, ok: true, warnings: warnings,
    calendars: calendars.map(function (c) {
      return { id: c.id, title: c.summaryOverride || c.summary || '', color: c.backgroundColor || '', primary: !!c.primary,
        writable: c.accessRole === 'owner' || c.accessRole === 'writer' };
    }),
    events: events,
    tasklists: tasklists.map(function (l) { return { id: l.id, title: l.title }; }),
    tasks: tasks
  };
}

function collectTasks(list, opts, out, completedOnly) {
  var token = null, n = 0;
  do {
    var args = { maxResults: 100, pageToken: token || undefined };
    for (var k in opts) args[k] = opts[k];
    var page = Tasks.Tasks.list(list.id, args);
    (page.items || []).forEach(function (t) {
      if (!t.title || t.deleted) return;
      if (completedOnly && t.status !== 'completed') return;
      out.push(taskOut(list, t));
      n++;
    });
    token = page.nextPageToken;
  } while (token && n < 300);
}

function taskOut(list, t) {
  return { id: t.id, listId: list.id, list: list.title || '', title: t.title || '', notes: clip(t.notes, 600),
    due: t.due ? String(t.due).slice(0, 10) : '', done: t.status === 'completed', completed: t.completed || '',
    link: t.webViewLink || '', parent: t.parent || '' };
}

/* ======================================================================
   Google writes
   ====================================================================== */

function pad2(n) { return (n < 10 ? '0' : '') + n; }

function eventTimes(req) {
  var date = String(req.date || '');
  if (!DATE_RE.test(date)) throw fail(400, 'Give the event a date.');
  if (req.allDay) {
    var next = new Date(date + 'T12:00:00Z');
    next.setUTCDate(next.getUTCDate() + 1);
    return { start: { date: date }, end: { date: next.toISOString().slice(0, 10) } };
  }
  var tz = String(req.tz || '') || Session.getScriptTimeZone();
  var start = TIME_RE.test(req.start || '') ? req.start : '09:00';
  var end = TIME_RE.test(req.end || '') ? req.end : start;
  if (end <= start) end = Number(start.slice(0, 2)) >= 23 ? '23:59' : pad2(Number(start.slice(0, 2)) + 1) + start.slice(2);
  return { start: { dateTime: date + 'T' + start + ':00', timeZone: tz }, end: { dateTime: date + 'T' + end + ':00', timeZone: tz } };
}

function calendarOf(id) {
  var c = { id: id || 'primary', summary: '', accessRole: 'owner' };
  try { var got = Calendar.CalendarList.get(c.id); if (got) c = got; } catch (err) { /* keep the id */ }
  return c;
}

function createEvent(req) {
  var t = eventTimes(req);
  var resource = { summary: clip(req.title || 'Untitled', 250), description: clip(req.description, 4000), location: clip(req.location, 300), start: t.start, end: t.end };
  var cal = req.calendarId || 'primary';
  var ev = Calendar.Events.insert(resource, cal);
  return { ok: true, id: ev.id, link: ev.htmlLink || '', event: eventOut(calendarOf(cal), ev, {}) };
}

function updateEvent(req) {
  if (!req.calendarId || !req.id) throw fail(400, 'Which event?');
  var patch = {};
  if (typeof req.title === 'string') patch.summary = clip(req.title.trim() || 'Untitled', 250);
  if (typeof req.description === 'string') patch.description = clip(req.description, 4000);
  if (typeof req.location === 'string') patch.location = clip(req.location, 300);
  if (req.date) { var t = eventTimes(req); patch.start = t.start; patch.end = t.end; }
  var ev = Calendar.Events.patch(patch, req.calendarId, req.id);
  return { ok: true, event: eventOut(calendarOf(req.calendarId), ev, {}) };
}

function deleteEvent(req) {
  if (!req.calendarId || !req.id) throw fail(400, 'Which event?');
  Calendar.Events.remove(req.calendarId, req.id);
  return { ok: true };
}

function createTask(req) {
  var body = { title: clip(req.title || 'Untitled', 1000), notes: clip(req.notes, 4000) };
  if (DATE_RE.test(req.due || '')) body.due = req.due + 'T00:00:00.000Z';
  var listId = req.listId || '@default';
  var t = Tasks.Tasks.insert(body, listId);
  var list = { id: listId, title: '' };
  try { list = Tasks.Tasklists.get(listId); } catch (err) { /* keep the id */ }
  return { ok: true, task: taskOut(list, t) };
}

function setTask(req) {
  if (!req.listId || !req.id) throw fail(400, 'Which task?');
  var patch = {};
  if (typeof req.done === 'boolean') {
    patch.status = req.done ? 'completed' : 'needsAction';
    if (!req.done) patch.completed = null;
  }
  if (typeof req.title === 'string' && req.title.trim()) patch.title = clip(req.title.trim(), 1000);
  if (typeof req.notes === 'string') patch.notes = clip(req.notes, 4000);
  if (req.due === '') patch.due = null;
  else if (DATE_RE.test(req.due || '')) patch.due = req.due + 'T00:00:00.000Z';
  var t = Tasks.Tasks.patch(patch, req.listId, req.id);
  return { ok: true, task: taskOut({ id: req.listId, title: req.list || '' }, t) };
}

function deleteTask(req) {
  if (!req.listId || !req.id) throw fail(400, 'Which task?');
  Tasks.Tasks.remove(req.listId, req.id);
  return { ok: true };
}

/* ======================================================================
   Notion
   ====================================================================== */

function listFrom(name, fallback) {
  var raw = prop(name);
  if (!raw) return fallback;
  try {
    var list = JSON.parse(raw);
    if (Array.isArray(list)) return list.filter(function (s) { return s && typeof s.id === 'string' && typeof s.label === 'string'; });
  } catch (err) {
    console.warn('desk: ' + name + ' is not valid JSON; using the defaults');
  }
  return fallback;
}

function notionRequest(path, method, body) {
  var token = prop('NOTION_TOKEN');
  if (!token) throw fail(503, 'Notion is not connected yet (NOTION_TOKEN in Script Properties).');
  var req = { url: NOTION_API + path, method: method || 'get', muteHttpExceptions: true, contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token, 'Notion-Version': NOTION_VERSION } };
  if (body) req.payload = JSON.stringify(body);
  return req;
}

function notionParse(res) {
  var code = res.getResponseCode(), data = {};
  try { data = JSON.parse(res.getContentText() || '{}'); } catch (err) { data = {}; }
  if (code === 404) throw fail(502, 'Notion cannot see this database. Add the integration under ••• > Connections on Research OS.');
  if (code === 401) throw fail(502, 'Notion rejected the token. Check NOTION_TOKEN.');
  if (code >= 400) throw fail(502, 'Notion: ' + (data.message || 'HTTP ' + code));
  return data;
}

function notionFetch(path, method, body) {
  var r = notionRequest(path, method, body);
  return notionParse(UrlFetchApp.fetch(r.url, r));
}

function plainText(rich) { return Array.isArray(rich) ? rich.map(function (t) { return t.plain_text || ''; }).join('') : ''; }

function propValue(p) {
  if (!p) return '';
  switch (p.type) {
    case 'title': return plainText(p.title);
    case 'rich_text': return plainText(p.rich_text);
    case 'select': return p.select ? p.select.name : '';
    case 'status': return p.status ? p.status.name : '';
    case 'multi_select': return (p.multi_select || []).map(function (o) { return o.name; }).join(', ');
    case 'url': return p.url || '';
    case 'number': return p.number == null ? '' : String(p.number);
    case 'checkbox': return p.checkbox ? 'yes' : '';
    case 'formula': return p.formula ? String(p.formula[p.formula.type] == null ? '' : p.formula[p.formula.type]) : '';
    default: return '';
  }
}

function notionRow(page, source) {
  var props = page.properties || {}, title = null;
  for (var k in props) if (props[k] && props[k].type === 'title') { title = props[k]; break; }
  var date = source.date && props[source.date] && props[source.date].date;
  var status = source.status ? propValue(props[source.status]) : '';
  return {
    id: page.id, url: page.url || '', source: source.label, sourceId: source.id,
    title: title ? plainText(title.title) || '(untitled)' : '(untitled)',
    date: date ? date.start : '', end: date && date.end ? date.end : '', status: status,
    done: !!(status && Array.isArray(source.done) && source.done.indexOf(status) !== -1)
  };
}

function sourceQuery(source, r, cursor) {
  var body = { page_size: 100 };
  if (source.date) {
    body.filter = { and: [{ property: source.date, date: { on_or_after: r.from } }, { property: source.date, date: { on_or_before: r.to } }] };
    body.sorts = [{ property: source.date, direction: 'ascending' }];
  }
  if (cursor) body.start_cursor = cursor;
  return notionRequest('/data_sources/' + source.id + '/query', 'post', body);
}

function syncNotion(r) {
  if (!prop('NOTION_TOKEN')) return { configured: false, ok: false, sources: [] };
  var sources = listFrom('NOTION_SOURCES', DEFAULT_SOURCES);
  // First pages in parallel; Notion allows about three requests a second.
  var responses = UrlFetchApp.fetchAll(sources.map(function (s) { return sourceQuery(s, r); }));
  var results = sources.map(function (s, i) {
    try {
      var data = notionParse(responses[i]), rows = [], pages = 0;
      while (true) {
        (data.results || []).forEach(function (p) { if (!p.in_trash && !p.archived) rows.push(notionRow(p, s)); });
        if (!data.has_more || !data.next_cursor || ++pages >= 3) break;
        var q = sourceQuery(s, r, data.next_cursor);
        data = notionParse(UrlFetchApp.fetch(q.url, q));
      }
      return { id: s.id, label: s.label, rows: rows };
    } catch (err) {
      return { id: s.id, label: s.label, rows: [], error: String(err.message || err).slice(0, 300) };
    }
  });
  return { configured: true, ok: results.some(function (x) { return !x.error; }), sources: results };
}

function notionTargets() {
  return { ok: true, targets: listFrom('NOTION_TARGETS', DEFAULT_TARGETS), notion: !!prop('NOTION_TOKEN') };
}

var EDITABLE = ['title', 'rich_text', 'select', 'status', 'multi_select', 'date', 'url', 'number', 'checkbox'];

function notionSchema(req) {
  var id = String(req.id || '');
  if (!/^[0-9a-f-]{32,36}$/i.test(id)) throw fail(400, 'Invalid data source id.');
  var ds = notionFetch('/data_sources/' + id, 'get');
  var fields = Object.keys(ds.properties || {}).filter(function (name) { return EDITABLE.indexOf(ds.properties[name].type) !== -1; })
    .map(function (name) {
      var p = ds.properties[name];
      return { name: name, type: p.type, options: ((p[p.type] && p[p.type].options) || []).map(function (o) { return o.name; }) };
    });
  return { ok: true, id: id, title: plainText(ds.title) || '', fields: fields };
}

function typedProperty(type, value) {
  var v = String(value == null ? '' : value).trim();
  if (!v) return null;
  var text = function (s) { return [{ type: 'text', text: { content: s.slice(0, 2000) } }]; };
  switch (type) {
    case 'title': return { title: text(v) };
    case 'rich_text': return { rich_text: text(v) };
    case 'select': return { select: { name: v.slice(0, 100) } };
    case 'status': return { status: { name: v.slice(0, 100) } };
    case 'multi_select': return { multi_select: v.split(',').map(function (s) { return s.trim(); }).filter(Boolean).slice(0, 20).map(function (name) { return { name: name }; }) };
    case 'date': return DATE_RE.test(v) || !isNaN(Date.parse(v)) ? { date: { start: v } } : null;
    case 'url': return /^https?:\/\//i.test(v) ? { url: v } : null;
    case 'number': return isFinite(Number(v)) ? { number: Number(v) } : null;
    case 'checkbox': return { checkbox: v === 'true' || v === 'yes' || v === '1' };
    default: return null;
  }
}

// Plain-text body to Notion blocks: "## " headings, "- " bullets, paragraphs.
function markdownBlocks(md) {
  var blocks = [];
  var rich = function (s) {
    var out = [];
    for (var i = 0; i < s.length && out.length < 50; i += 2000) out.push({ type: 'text', text: { content: s.slice(i, i + 2000) } });
    return out;
  };
  String(md || '').split(/\n{2,}/).forEach(function (chunk) {
    var t = chunk.trim();
    if (!t || blocks.length >= 90) return;
    if (t.indexOf('## ') === 0) blocks.push({ object: 'block', type: 'heading_2', heading_2: { rich_text: rich(t.slice(3)) } });
    else if (t.split('\n').every(function (l) { return l.indexOf('- ') === 0; })) {
      t.split('\n').forEach(function (l) { blocks.push({ object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich(l.slice(2)) } }); });
    } else blocks.push({ object: 'block', type: 'paragraph', paragraph: { rich_text: rich(t) } });
  });
  return blocks;
}

function notionCreate(req) {
  var target = listFrom('NOTION_TARGETS', DEFAULT_TARGETS).filter(function (t) { return t.id === req.target; })[0];
  if (!target) throw fail(400, 'Unknown Notion target.');
  var schema = notionFetch('/data_sources/' + target.id, 'get').properties || {};
  var titleName = Object.keys(schema).filter(function (k) { return schema[k].type === 'title'; })[0];
  if (!titleName) throw fail(502, 'That Notion database has no title column.');
  var properties = {};
  properties[titleName] = typedProperty('title', req.title || 'Untitled');
  var fields = req.fields || {};
  Object.keys(fields).forEach(function (name) {
    if (name === titleName || !schema[name]) return;
    var typed = typedProperty(schema[name].type, fields[name]);
    if (typed) properties[name] = typed;
  });
  var page = notionFetch('/pages', 'post', {
    parent: { type: 'data_source_id', data_source_id: target.id }, properties: properties, children: markdownBlocks(req.body)
  });
  return { ok: true, id: page.id, url: page.url || '' };
}

/* ======================================================================
   Images, kept in a Drive folder shared by link
   ====================================================================== */

function uploadImage(req) {
  var m = /^data:(image\/(?:jpeg|png|webp|gif));base64,([A-Za-z0-9+/=]+)$/.exec(String(req.dataUrl || ''));
  if (!m) throw fail(400, 'Send a JPEG, PNG, WebP or GIF image.');
  if (m[2].length > LIMITS.imageBase64) throw fail(413, 'That image is too large.');
  var props = PropertiesService.getScriptProperties(), dayKey = 'img:d:' + Math.floor(clock() / 864e5);
  var n = Number(props.getProperty(dayKey) || 0) + 1;
  if (n > LIMITS.imagesPerDay) throw fail(429, 'The desk has taken its images for today.');
  props.setProperty(dayKey, String(n));
  if (n === 1) pruneProps('img:d:', dayKey);
  var folderId = prop('IMAGE_FOLDER_ID');
  if (!folderId) throw fail(503, 'Run setup() in the Apps Script editor first.');
  var blob = Utilities.newBlob(Utilities.base64Decode(m[2]), m[1], clip(String(req.name || 'image').replace(/[^\w. -]/g, '_'), 100));
  var file = DriveApp.getFolderById(folderId).createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  return { ok: true, image: { id: file.getId(), url: 'https://drive.google.com/thumbnail?id=' + file.getId() + '&sz=w1600' } };
}
