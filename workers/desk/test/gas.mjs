// Runs Code.gs in a Node sandbox with the Apps Script services it uses replaced
// by small in-memory fakes. Shared by the tests and dev/server.mjs.
import { readFileSync } from 'node:fs';
import { createHmac, createHash, randomUUID } from 'node:crypto';
import vm from 'node:vm';

const SOURCE = readFileSync(new URL('../Code.gs', import.meta.url), 'utf8');

const toSigned = buf => Array.from(buf, b => (b > 127 ? b - 256 : b));
const toBuf = x => (typeof x === 'string' ? Buffer.from(x, 'utf8') : Buffer.from(x.map(b => (b < 0 ? b + 256 : b))));

function fakeSheet(name) {
  let rows = [];
  const sheet = {
    getName: () => name,
    setName: n => { name = n; return sheet; },
    getLastRow: () => rows.length,
    appendRow: r => { rows.push(r.map(String)); return sheet; },
    setFrozenRows: () => sheet,
    getRange: (a, col, nr, nc) => {
      if (typeof a === 'string') return { setNumberFormat: () => {} };
      return {
        getValues: () => rows.slice(a - 1, a - 1 + nr).map(r => r.slice(col - 1, col - 1 + nc)),
        setValues: vals => { vals.forEach((v, i) => { rows[a - 1 + i] = v.map(String); }); },
        setNumberFormat: () => {},
      };
    },
    _rows: () => rows,
  };
  return sheet;
}

function fakeSpreadsheets() {
  const books = {};
  const make = id => {
    const sheets = [fakeSheet('Sheet1')];
    const book = {
      getId: () => id,
      getUrl: () => 'https://docs.google.com/spreadsheets/d/' + id,
      getSheets: () => sheets,
      getSheetByName: n => sheets.find(s => s.getName() === n) || null,
      insertSheet: n => { const s = fakeSheet(n); sheets.push(s); return s; },
    };
    books[id] = book;
    return book;
  };
  return {
    create: () => make('sheet-' + Object.keys(books).length),
    openById: id => { if (!books[id]) throw new Error('No spreadsheet ' + id); return books[id]; },
    _books: books,
  };
}

// `google` and `notion` are plain objects the caller can mutate to shape what
// the fake Calendar, Tasks and Notion return.
export function makeGas({ google = {}, notion = {}, now = () => Date.now() } = {}) {
  const props = {};
  const cache = {};
  const drive = [];
  const calls = { events: [], tasks: [], notion: [] };
  // Copies, so a test or the dev server can edit events and tasks without
  // touching the caller's fixture.
  const copy = x => (typeof x === 'function' || x === undefined ? x : structuredClone(x));
  const cal = copy(google.calendars) || [{ id: 'primary', summary: 'Personal', backgroundColor: '#039be5', primary: true, accessRole: 'owner', selected: true }];
  const events = copy(google.events) || {};
  const tasklists = copy(google.tasklists) || [{ id: 'L1', title: 'My Tasks' }];
  const tasks = copy(google.tasks) || {};
  const store = (bag, key) => (typeof bag === 'function' ? null : (bag[key] = bag[key] || []));
  let seq = 0;

  const notionHandler = notion.handler || (() => ({ code: 404, body: { message: 'not mocked' } }));
  const response = ({ code = 200, body = {} }) => ({ getResponseCode: () => code, getContentText: () => JSON.stringify(body) });
  const fetchOne = (url, params = {}) => {
    calls.notion.push({ url, method: params.method, body: params.payload ? JSON.parse(params.payload) : null, headers: params.headers });
    return response(notionHandler(url, params.method || 'get', params.payload ? JSON.parse(params.payload) : null, params.headers || {}));
  };

  const ctx = {
    console: { error() {}, warn() {}, log() {} },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: k => (k in props ? props[k] : null),
        setProperty: (k, v) => { props[k] = String(v); },
        deleteProperty: k => { delete props[k]; },
        getKeys: () => Object.keys(props),
      }),
    },
    CacheService: {
      getScriptCache: () => ({
        get: k => (k in cache ? cache[k] : null),
        put: (k, v) => { cache[k] = String(v); },
        getAll: keys => Object.fromEntries(keys.filter(k => k in cache).map(k => [k, cache[k]])),
        putAll: obj => { Object.assign(cache, obj); },
        remove: k => { delete cache[k]; },
      }),
    },
    LockService: { getScriptLock: () => ({ tryLock: () => true, releaseLock: () => {} }) },
    ContentService: { MimeType: { JSON: 'json' }, createTextOutput: text => ({ text, setMimeType() { return this; } }) },
    Logger: { log() {} },
    Session: { getScriptTimeZone: () => 'Asia/Seoul' },
    SpreadsheetApp: fakeSpreadsheets(),
    Utilities: {
      getUuid: () => randomUUID(),
      DigestAlgorithm: { MD5: 'md5' },
      computeDigest: (algo, text) => toSigned(createHash(algo).update(text).digest()),
      computeHmacSha256Signature: (value, key) => toSigned(createHmac('sha256', key).update(value).digest()),
      base64EncodeWebSafe: x => toBuf(x).toString('base64').replace(/\+/g, '-').replace(/\//g, '_'),
      base64DecodeWebSafe: s => toSigned(Buffer.from(s.replace(/-/g, '+').replace(/_/g, '/'), 'base64')),
      base64Decode: s => toSigned(Buffer.from(s, 'base64')),
      newBlob: (bytes, mime, name) => ({ bytes, mime, name, getDataAsString: () => toBuf(bytes).toString('utf8') }),
    },
    UrlFetchApp: { fetch: fetchOne, fetchAll: list => list.map(r => fetchOne(r.url, r)) },
    DriveApp: {
      Access: { ANYONE_WITH_LINK: 'ANYONE_WITH_LINK' },
      Permission: { VIEW: 'VIEW' },
      createFolder: name => ({ getId: () => 'folder-' + name }),
      getFolderById: () => ({
        createFile: blob => {
          const file = { id: 'file' + drive.length, blob, sharing: null };
          drive.push(file);
          return { getId: () => file.id, setSharing: (a, p) => { file.sharing = [a, p]; } };
        },
      }),
    },
    Calendar: {
      Colors: { get: () => ({ event: { 11: { background: '#dc2127' } } }) },
      CalendarList: {
        list: () => ({ items: cal }),
        get: id => cal.find(c => c.id === id) || null,
      },
      Events: {
        list: (id, args) => {
          calls.events.push(['list', id, args]);
          return { items: (typeof events === 'function' ? events(id, args) : events[id]) || [] };
        },
        insert: (res, id) => {
          calls.events.push(['insert', id, res]);
          const ev = { id: 'ev' + (++seq), status: 'confirmed', htmlLink: 'https://calendar.google.com/new', ...structuredClone(res) };
          const list = store(events, id === 'primary' ? (cal.find(c => c.primary) || cal[0]).id : id);
          if (list) list.push(ev);
          return ev;
        },
        patch: (res, id, evId) => {
          calls.events.push(['patch', id, evId, res]);
          const found = (store(events, id) || []).find(e => e.id === evId);
          if (found) { Object.assign(found, structuredClone(res)); return found; }
          return { id: evId, summary: res.summary || 'x', start: res.start || { date: '2026-10-12' }, end: res.end, htmlLink: '' };
        },
        remove: (id, evId) => {
          calls.events.push(['remove', id, evId]);
          const list = store(events, id);
          if (list) list.splice(0, list.length, ...list.filter(e => e.id !== evId));
        },
      },
    },
    Tasks: {
      Tasklists: { list: () => ({ items: tasklists }), get: id => tasklists.find(l => l.id === id) || { id, title: '' } },
      Tasks: {
        list: (listId, args) => {
          const all = (typeof tasks === 'function' ? tasks(listId, args) : tasks[listId]) || [];
          return { items: all.filter(t => (args.showCompleted ? true : t.status !== 'completed')) };
        },
        insert: (body, listId) => {
          calls.tasks.push(['insert', listId, body]);
          const t = { id: 'task' + (++seq), status: 'needsAction', ...structuredClone(body) };
          const list = store(tasks, listId === '@default' ? tasklists[0].id : listId);
          if (list) list.push(t);
          return t;
        },
        patch: (body, listId, id) => {
          calls.tasks.push(['patch', listId, id, body]);
          const found = (store(tasks, listId) || []).find(t => t.id === id);
          if (found) {
            Object.entries(body).forEach(([k, v]) => { if (v === null) delete found[k]; else found[k] = v; });
            if (body.status === 'completed' && !found.completed) found.completed = new Date().toISOString();
            return found;
          }
          return { id, title: body.title || 't', status: body.status || 'needsAction' };
        },
        remove: (listId, id) => {
          calls.tasks.push(['remove', listId, id]);
          const list = store(tasks, listId);
          if (list) list.splice(0, list.length, ...list.filter(t => t.id !== id));
        },
      },
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SOURCE, ctx);
  ctx.clock = now;
  // Objects built in the sandbox have that realm's prototypes; hand back plain copies.
  const plain = x => (x === undefined ? x : JSON.parse(JSON.stringify(x)));
  return {
    ctx, props, cache, drive, calls,
    call: req => plain(ctx.handle(req)),
    post: req => JSON.parse(ctx.doPost({ postData: { contents: typeof req === 'string' ? req : JSON.stringify(req) } }).text),
    fn: (name, ...args) => plain(ctx[name](...args)),
  };
}
