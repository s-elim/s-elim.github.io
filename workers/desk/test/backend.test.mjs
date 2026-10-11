// Tests for Code.gs, run against the fakes in gas.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { makeGas } from './gas.mjs';

const T0 = Date.parse('2026-10-11T09:00:00Z');

function ready(opts = {}) {
  let t = T0;
  const gas = makeGas({ now: () => t, ...opts });
  gas.ctx.setup();
  gas.tick = ms => { t += ms; };
  return gas;
}

const RANGE = { from: '2026-10-01', to: '2027-01-31', timeMin: '2026-09-30T15:00:00Z', timeMax: '2027-01-31T15:00:00Z', tz: 'Asia/Seoul' };

// ----------------------------------------------------------------- basics

test('health works before setup and reports the mode', () => {
  const gas = makeGas();
  const h = gas.call({ action: 'health' });
  assert.equal(h.ok, true);
  assert.equal(h.mode, 'open');
  assert.equal(h.configured.sheet, false);
  assert.equal(gas.call({ action: 'list', collection: 'entries' }).status, 503);
  gas.ctx.setup();
  assert.equal(gas.call({ action: 'health' }).configured.sheet, true);
});

test('setup is idempotent and creates both tabs with headers', () => {
  const gas = ready();
  gas.ctx.setup();
  const book = Object.values(gas.ctx.SpreadsheetApp._books)[0];
  assert.deepEqual(book.getSheets().map(s => s.getName()), ['docs', 'revisions']);
  assert.equal(book.getSheetByName('docs')._rows()[0][0], 'collection');
  assert.equal(Object.keys(gas.ctx.SpreadsheetApp._books).length, 1);
});

test('doPost answers bad JSON and unknown actions with JSON errors', () => {
  const gas = ready();
  assert.equal(gas.post('{not json').status, 400);
  assert.equal(gas.post({ action: 'drop_tables' }).status, 404);
  assert.equal(JSON.parse(gas.ctx.doGet({ parameter: {} }).text).service, 'desk');
});

// -------------------------------------------------------------- documents

test('documents carry versions, keep history, refuse stale writes and can be restored', () => {
  const gas = ready();
  const v1 = gas.call({ action: 'put', collection: 'entries', id: 'idea-1', data: { title: 'First' } });
  assert.equal(v1.doc.version, 1);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'idea-1', data: { title: 'Second' }, baseVersion: 1 }).doc.version, 2);
  const stale = gas.call({ action: 'put', collection: 'entries', id: 'idea-1', data: { title: 'Lost' }, baseVersion: 1 });
  assert.equal(stale.status, 409);
  assert.equal(stale.doc.data.title, 'Second');

  assert.equal(gas.call({ action: 'delete', collection: 'entries', id: 'idea-1', base: 2 }).doc.deleted, true);
  assert.equal(gas.call({ action: 'list', collection: 'entries' }).docs.length, 0);
  assert.deepEqual(gas.call({ action: 'list', collection: 'entries', deleted: true }).docs.map(d => d.id), ['idea-1']);
  assert.equal(gas.call({ action: 'get', collection: 'entries', id: 'idea-1' }).status, 404);

  const revs = gas.call({ action: 'revisions', collection: 'entries', id: 'idea-1' }).revisions;
  assert.deepEqual(revs.map(r => [r.version, r.deleted]), [[3, true], [2, false], [1, false]]);
  assert.equal(gas.call({ action: 'revision', collection: 'entries', id: 'idea-1', version: 1 }).revision.data.title, 'First');

  const back = gas.call({ action: 'restore', collection: 'entries', id: 'idea-1' });
  assert.deepEqual([back.doc.version, back.doc.deleted, back.doc.data.title], [4, false, 'Second']);
  assert.equal(gas.call({ action: 'list', collection: 'entries' }).docs[0].data.title, 'Second');
});

test('stored values stay text: dates and versions are not reinterpreted', () => {
  const gas = ready();
  gas.call({ action: 'put', collection: 'entries', id: 'd', data: { deadline: '2027-07-30', title: '=SUM(A1)' } });
  const doc = gas.call({ action: 'get', collection: 'entries', id: 'd' }).doc;
  assert.equal(doc.data.deadline, '2027-07-30');
  assert.equal(doc.data.title, '=SUM(A1)');
  assert.equal(doc.version, 1);
});

test('rejects unknown collections, bad ids and oversized documents', () => {
  const gas = ready();
  assert.equal(gas.call({ action: 'list', collection: 'secrets' }).status, 404);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'bad id', data: {} }).status, 400);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'big', data: { x: 'a'.repeat(50000) } }).status, 413);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'x', title: 'no wrapper' }).status, 400);
});

test('import accepts an export, skips invalid rows and is idempotent; load returns everything', () => {
  const gas = ready();
  const payload = { format: 'desk-export-v1', docs: { entries: [{ id: 'a', data: { title: 'A' } }, { id: 'b', data: { title: 'B' } }], settings: [{ id: 'prefs', data: { watched: ['CVPR'] } }] } };
  const first = gas.call({ action: 'import', docs: payload.docs });
  assert.deepEqual([first.written, first.unchanged], [3, 0]);
  const again = gas.call({ action: 'import', docs: payload.docs });
  assert.deepEqual([again.written, again.unchanged], [0, 3]);
  const flat = gas.call({ action: 'import', docs: [{ collection: 'entries', id: 'c', data: { title: 'C' } }, { collection: 'nope', id: 'd', data: {} }] });
  assert.deepEqual([flat.written, flat.skipped], [1, ['d']]);
  const all = gas.call({ action: 'load' });
  assert.deepEqual([all.docs.entries.length, all.docs.settings.length, all.docs.tasks.length], [3, 1, 0]);
  const exp = gas.call({ action: 'export' });
  assert.equal(exp.format, 'desk-export-v1');
  assert.equal(exp.docs.entries.length, 3);
});

// ------------------------------------------------------------ write meter

test('writes are metered per minute and per day; reads are not', () => {
  const gas = ready();
  for (let i = 0; i < 60; i++) assert.equal(gas.call({ action: 'put', collection: 'tasks', id: 't' + i, data: { title: 'x' } }).ok, true);
  assert.equal(gas.call({ action: 'put', collection: 'tasks', id: 'over', data: {} }).status, 429);
  assert.equal(gas.call({ action: 'list', collection: 'tasks' }).ok, true);
  gas.tick(61e3);
  assert.equal(gas.call({ action: 'put', collection: 'tasks', id: 'later', data: {} }).ok, true);
  gas.props['w:d:' + Math.floor((T0 + 61e3) / 864e5)] = '3000';
  assert.match(gas.call({ action: 'put', collection: 'tasks', id: 'day', data: {} }).error, /today/);
  gas.tick(864e5);
  assert.equal(gas.call({ action: 'put', collection: 'tasks', id: 'tomorrow', data: {} }).ok, true);
  assert.equal(Object.keys(gas.props).filter(k => k.startsWith('w:d:')).length, 1, 'old day counters are pruned');
});

// ------------------------------------------------------------ private mode

test('private mode needs a token, and the token dies with the passcode', () => {
  const gas = ready();
  gas.props.DESK_MODE = 'private';
  assert.equal(gas.call({ action: 'list', collection: 'entries' }).status, 503, 'no passcode configured');
  gas.props.DESK_PASSPHRASE = '471';
  assert.equal(gas.call({ action: 'auth', passphrase: '471' }).status, 503, 'shorter than 4 is refused');
  gas.props.DESK_PASSPHRASE = '4711';
  assert.equal(gas.call({ action: 'list', collection: 'entries' }).status, 401);
  assert.equal(gas.call({ action: 'auth', passphrase: '0000' }).status, 401);
  const { token } = gas.call({ action: 'auth', passphrase: '4711' });
  assert.equal(gas.call({ action: 'list', collection: 'entries', token }).ok, true);
  assert.equal(gas.call({ action: 'sync', ...RANGE, token }).ok, true);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'x', data: {}, token }).ok, true);
  assert.equal(gas.call({ action: 'put', collection: 'entries', id: 'y', data: {} }).status, 401, 'writes need the token too');
  assert.equal(gas.call({ action: 'list', collection: 'entries', token: token.replace(/.$/, c => (c === 'A' ? 'B' : 'A')) }).status, 401);
  gas.props.DESK_PASSPHRASE = '9999';
  assert.equal(gas.call({ action: 'list', collection: 'entries', token }).status, 401);
});

test('a short passcode cannot be recovered by forging tokens offline', () => {
  const gas = ready();
  Object.assign(gas.props, { DESK_MODE: 'private', DESK_PASSPHRASE: '4711' });
  gas.call({ action: 'auth', passphrase: '4711' });
  assert.equal(gas.props.TOKEN_SECRET.length, 64, 'a random signing secret exists');
  // An attacker who guesses the passcode right still cannot sign without the secret.
  const payload = Buffer.from(JSON.stringify({ v: 2, exp: T0 + 9e9 })).toString('base64url');
  for (const key of ['4711|desk-token-v2', '4711|desk-token-v1', '|4711|desk-token-v2']) {
    const sig = createHmac('sha256', key).update(payload).digest('base64url');
    assert.equal(gas.call({ action: 'list', collection: 'entries', token: payload + '.' + sig }).status, 401, key);
  }
});

test('ten wrong passcodes in an hour close sign-in and email the owner once', () => {
  const gas = ready();
  Object.assign(gas.props, { DESK_MODE: 'private', DESK_PASSPHRASE: '4711' });
  const { token } = gas.call({ action: 'auth', passphrase: '4711' });
  for (let i = 0; i < 10; i++) assert.equal(gas.call({ action: 'auth', passphrase: String(1000 + i) }).status, 401);
  assert.equal(gas.call({ action: 'auth', passphrase: '4711' }).status, 429, 'even the right code waits');
  assert.equal(gas.call({ action: 'auth', passphrase: '1234' }).status, 429);
  assert.equal(gas.mail.length, 1);
  assert.equal(gas.mail[0].to, 'owner@example.com');
  assert.equal(gas.call({ action: 'list', collection: 'entries', token }).ok, true, 'signed-in devices keep working');
  gas.tick(36e5);
  assert.equal(gas.call({ action: 'auth', passphrase: '4711' }).ok, true, 'the next hour opens again');
});

test('private-mode tokens expire after 120 days', () => {
  const gas = ready();
  Object.assign(gas.props, { DESK_MODE: 'private', DESK_PASSPHRASE: '4711' });
  const { token } = gas.call({ action: 'auth', passphrase: '4711' });
  gas.tick(119 * 864e5);
  assert.equal(gas.call({ action: 'list', collection: 'entries', token }).ok, true);
  gas.tick(2 * 864e5);
  assert.equal(gas.call({ action: 'list', collection: 'entries', token }).status, 401);
});

test('auth in open mode is a no-op', () => {
  const gas = ready();
  assert.deepEqual(gas.call({ action: 'auth' }), { ok: true, token: '', exp: 0, mode: 'open' });
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

const GOOGLE = {
  calendars: [
    { id: 'me', summary: 'Selim', backgroundColor: '#9fe1e7', primary: true, accessRole: 'owner', selected: true },
    { id: 'holidays', summary: 'Holidays', backgroundColor: '#16a765', accessRole: 'reader', selected: true },
    { id: 'hidden', summary: 'Hidden', hidden: true },
  ],
  events: {
    me: [
      { id: 'e1', status: 'confirmed', summary: 'Lab meeting', start: { dateTime: '2026-10-12T10:00:00+09:00' }, end: { dateTime: '2026-10-12T11:00:00+09:00' },
        colorId: '11', hangoutLink: 'https://meet.google.com/abc-defg-hij', location: 'https://zoom.us/j/123 or Room 301', description: '<b>Agenda</b><br>Join https://meet.google.com/abc-defg-hij', htmlLink: 'https://calendar.google.com/e1' },
      { id: 'e2', status: 'cancelled', summary: 'Gone', start: { date: '2026-10-13' } },
      { id: 'e3', status: 'confirmed', summary: 'Declined', start: { date: '2026-10-14' }, attendees: [{ self: true, responseStatus: 'declined' }] },
      { id: 'e5', status: 'confirmed', summary: 'Weekly sync', recurringEventId: 'base', start: { dateTime: '2026-10-15T09:00:00+09:00' }, end: { dateTime: '2026-10-15T09:30:00+09:00' } },
    ],
    holidays: [{ id: 'h1', status: 'confirmed', summary: 'Hangul Day', start: { date: '2026-10-09' }, end: { date: '2026-10-10' } }],
  },
  tasks: {
    L1: [
      { id: 't1', title: 'Rebuttal', status: 'needsAction', due: '2026-10-15T00:00:00.000Z' },
      { id: 't2', title: 'Sent reviews', status: 'completed', completed: '2026-10-11T01:00:00Z' },
      { id: 'tx', title: '' },
    ],
  },
};

function notionHandler(url, method) {
  if (url.endsWith('aaaa0001/query')) return { body: { results: [notionPage('p1', 'Camera-ready', '2026-10-20', 'Camera-ready'), notionPage('p2', 'Old', '2026-10-05', 'Accepted')], has_more: false } };
  return { code: 404, body: { message: 'Could not find data source' } };
}

test('sync merges Google and Notion, hides call links in open mode, and isolates a failing source', () => {
  const gas = ready({ google: GOOGLE, notion: { handler: notionHandler } });
  Object.assign(gas.props, {
    NOTION_TOKEN: 'ntn_test',
    NOTION_SOURCES: JSON.stringify([
      { id: 'aaaa0001', label: 'Publications', date: 'Deadline', status: 'Status', done: ['Accepted'] },
      { id: 'aaaa0002', label: 'Broken', date: 'Deadline' },
    ]),
  });
  const s = gas.call({ action: 'sync', ...RANGE });
  assert.equal(s.google.ok, true);
  assert.deepEqual(s.google.events.map(e => e.title), ['Lab meeting', 'Weekly sync', 'Hangul Day']);
  const lab = s.google.events[0];
  assert.equal(lab.video, '');
  assert.equal(lab.location, '[call link hidden] or Room 301');
  assert.equal(lab.description, 'Agenda\nJoin [call link hidden]');
  assert.equal(lab.color, '#dc2127');
  assert.deepEqual([lab.editable, s.google.events[2].editable, s.google.events[1].recurring], [true, false, true]);
  assert.deepEqual(s.google.tasks.map(t => [t.id, t.done, t.due]), [['t1', false, '2026-10-15'], ['t2', true, '']]);
  const [pubs, broken] = s.notion.sources;
  assert.deepEqual(pubs.rows.map(r => [r.title, r.done]), [['Camera-ready', false], ['Old', true]]);
  assert.match(broken.error, /Connections/);
  const q = gas.calls.notion.find(c => c.url.endsWith('aaaa0001/query'));
  assert.deepEqual(q.body.filter.and[0], { property: 'Deadline', date: { on_or_after: '2026-10-01' } });
  assert.equal(q.headers['Notion-Version'], '2025-09-03');
});

test('private mode keeps call links', () => {
  const gas = ready({ google: GOOGLE });
  Object.assign(gas.props, { DESK_MODE: 'private', DESK_PASSPHRASE: '4711' });
  const { token } = gas.call({ action: 'auth', passphrase: '4711' });
  const s = gas.call({ action: 'sync', ...RANGE, token });
  assert.equal(s.google.events[0].video, 'https://meet.google.com/abc-defg-hij');
});

test('sync answers are shared for a minute; a forced refresh is honoured after ten seconds', () => {
  const gas = ready({ google: GOOGLE });
  const listCalls = () => gas.calls.events.filter(c => c[0] === 'list').length;
  gas.call({ action: 'sync', ...RANGE });
  const n = listCalls();
  assert.equal(gas.call({ action: 'sync', ...RANGE }).cached, true);
  assert.equal(gas.call({ action: 'sync', ...RANGE, fresh: true }).cached, true, 'forced within 10 s still shares');
  assert.equal(listCalls(), n);
  gas.tick(11e3);
  assert.equal(gas.call({ action: 'sync', ...RANGE, fresh: true }).cached, undefined);
  assert.ok(listCalls() > n);
  gas.tick(61e3);
  assert.equal(gas.call({ action: 'sync', ...RANGE }).cached, undefined);
});

test('sync reports Notion as unconfigured and validates its range', () => {
  const gas = ready({ google: GOOGLE });
  const s = gas.call({ action: 'sync', ...RANGE });
  assert.deepEqual([s.notion.configured, s.notion.ok], [false, false]);
  assert.equal(gas.call({ action: 'sync', from: '2026-10-31', to: '2026-10-01' }).status, 400);
  assert.equal(gas.call({ action: 'sync', from: '2026-01-01', to: '2028-01-01' }).status, 400);
  const withSync = gas.call({ action: 'load', sync: RANGE });
  assert.equal(withSync.sync.google.ok, true);
});

test('a Tasks failure becomes a warning, not a broken calendar', () => {
  const gas = ready({ google: { ...GOOGLE, tasks: () => { throw new Error('Tasks API has not been used'); } } });
  const s = gas.call({ action: 'sync', ...RANGE });
  assert.equal(s.google.ok, true);
  assert.equal(s.google.events.length, 3);
  assert.match(s.google.warnings.join(' '), /Tasks service/);
});

// ---------------------------------------------------------- google writes

test('event writes build timed and all-day resources and edit or remove existing events', () => {
  const gas = ready({ google: GOOGLE });
  assert.equal(gas.call({ action: 'createEvent', title: 'Write', date: '2026-10-12', start: '23:30', end: '10:00', tz: 'Asia/Seoul' }).ok, true);
  assert.equal(gas.call({ action: 'createEvent', title: 'Due', date: '2026-12-31', allDay: true }).ok, true);
  assert.equal(gas.call({ action: 'createEvent', title: 'No date' }).status, 400);
  const [[, cal, timed], [, , allDay]] = gas.calls.events.filter(c => c[0] === 'insert');
  assert.equal(cal, 'primary');
  assert.deepEqual([timed.start.dateTime, timed.end.dateTime, timed.start.timeZone], ['2026-10-12T23:30:00', '2026-10-12T23:59:00', 'Asia/Seoul']);
  assert.deepEqual([allDay.start.date, allDay.end.date], ['2026-12-31', '2027-01-01']);

  const up = gas.call({ action: 'updateEvent', calendarId: 'me', id: 'e1', title: 'Lab meeting (moved)', date: '2026-10-13', start: '14:00', end: '15:00', tz: 'Asia/Seoul' });
  assert.equal(up.ok, true);
  const patch = gas.calls.events.find(c => c[0] === 'patch');
  assert.deepEqual([patch[1], patch[2], patch[3].summary, patch[3].start.dateTime], ['me', 'e1', 'Lab meeting (moved)', '2026-10-13T14:00:00']);
  const titleOnly = gas.call({ action: 'updateEvent', calendarId: 'me', id: 'e1', title: 'Renamed' });
  assert.equal(titleOnly.ok, true);
  assert.equal(gas.calls.events.filter(c => c[0] === 'patch')[1][3].start, undefined, 'a rename leaves the time alone');
  assert.equal(gas.call({ action: 'deleteEvent', calendarId: 'me', id: 'e1' }).ok, true);
  assert.deepEqual(gas.calls.events.find(c => c[0] === 'remove'), ['remove', 'me', 'e1']);
  assert.equal(gas.call({ action: 'deleteEvent' }).status, 400);
});

test('task writes create, complete, reopen, rename and delete Google Tasks', () => {
  const gas = ready({ google: GOOGLE });
  const made = gas.call({ action: 'createTask', title: 'Email Prof. Kim', due: '2026-10-12' });
  assert.equal(made.task.due, '2026-10-12');
  gas.call({ action: 'setTask', listId: 'L1', id: 't1', done: false });
  gas.call({ action: 'setTask', listId: 'L1', id: 't1', title: 'Rebuttal v2', due: '' });
  gas.call({ action: 'deleteTask', listId: 'L1', id: 't1' });
  const [insert, reopen, rename, del] = JSON.parse(JSON.stringify(gas.calls.tasks));
  assert.deepEqual(insert, ['insert', '@default', { title: 'Email Prof. Kim', notes: '', due: '2026-10-12T00:00:00.000Z' }]);
  assert.deepEqual(reopen[3], { status: 'needsAction', completed: null });
  assert.deepEqual(rename[3], { title: 'Rebuttal v2', due: null });
  assert.deepEqual(del, ['remove', 'L1', 't1']);
  assert.equal(gas.call({ action: 'setTask', done: true }).status, 400);
});

// ----------------------------------------------------------------- notion

test('notion helpers map rows, types and blocks', () => {
  const gas = ready();
  const row = gas.fn('notionRow', notionPage('p', 'Paper', '2026-11-16', 'Accepted'), { id: 's', label: 'Publications', date: 'Deadline', status: 'Status', done: ['Accepted'] });
  assert.deepEqual([row.title, row.date, row.status, row.done], ['Paper', '2026-11-16', 'Accepted', true]);
  assert.deepEqual(gas.fn('typedProperty', 'multi_select', 'VLA, World Models'), { multi_select: [{ name: 'VLA' }, { name: 'World Models' }] });
  assert.equal(gas.fn('typedProperty', 'url', 'javascript:alert(1)'), null);
  assert.equal(gas.fn('typedProperty', 'date', 'soon'), null);
  assert.deepEqual(gas.fn('markdownBlocks', '## Thesis\n\nOne claim.\n\n- a\n- b').map(b => b.type), ['heading_2', 'paragraph', 'bulleted_list_item', 'bulleted_list_item']);
});

test('creating a Notion row types each field from the live schema', () => {
  let created;
  const handler = (url, method, body) => {
    if (url.endsWith('/data_sources/5df9a8fe-83bc-4b35-865c-186120e4b97d')) {
      return { body: { title: [{ plain_text: 'Ideas' }], properties: { Idea: { type: 'title' }, Stage: { type: 'select', select: { options: [{ name: 'Seed' }] } }, Concept: { type: 'rich_text' } } } };
    }
    if (url.endsWith('/pages')) { created = body; return { body: { id: 'new', url: 'https://www.notion.so/new' } }; }
    return { code: 404, body: {} };
  };
  const gas = ready({ notion: { handler } });
  assert.equal(gas.call({ action: 'notionTargets' }).notion, false);
  gas.props.NOTION_TOKEN = 'ntn_test';
  assert.deepEqual(gas.call({ action: 'notionSchema', id: '5df9a8fe-83bc-4b35-865c-186120e4b97d' }).fields.map(f => f.name), ['Idea', 'Stage', 'Concept']);
  const r = gas.call({ action: 'notionCreate', target: '5df9a8fe-83bc-4b35-865c-186120e4b97d', title: 'World model plan', fields: { Stage: 'Seed', Concept: 'WM', Unknown: 'x' }, body: '## Thesis\n\nClaim.' });
  assert.equal(r.url, 'https://www.notion.so/new');
  assert.deepEqual(created.parent, { type: 'data_source_id', data_source_id: '5df9a8fe-83bc-4b35-865c-186120e4b97d' });
  assert.deepEqual(Object.keys(created.properties).sort(), ['Concept', 'Idea', 'Stage']);
  assert.equal(gas.call({ action: 'notionCreate', target: 'nope', title: 'x' }).status, 400);
});

// ----------------------------------------------------------------- images

test('images go to the Drive folder, shared by link, with a daily cap', () => {
  const gas = ready();
  const png = 'data:image/png;base64,' + Buffer.from('fake png bytes').toString('base64');
  const r = gas.call({ action: 'uploadImage', name: 'fig 1.png', dataUrl: png });
  assert.match(r.image.url, /^https:\/\/drive\.google\.com\/thumbnail\?id=file0&sz=w1600$/);
  assert.deepEqual(gas.drive[0].sharing, ['ANYONE_WITH_LINK', 'VIEW']);
  assert.equal(gas.call({ action: 'uploadImage', dataUrl: 'data:text/html;base64,PGgxPg==' }).status, 400);
  gas.props['img:d:' + Math.floor(T0 / 864e5)] = '60';
  assert.equal(gas.call({ action: 'uploadImage', dataUrl: png }).status, 429);
});
