// Runs bridge/Code.gs in a sandbox with the Apps Script services faked, so the
// bridge's request handling and data shaping are checked without a Google account.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SOURCE = readFileSync(new URL('../bridge/Code.gs', import.meta.url), 'utf8');

function sandbox() {
  const props = { DESK_SECRET: 'b'.repeat(64) };
  const inserted = { events: [], tasks: [], patches: [] };
  const ctx = {
    crypto,
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: k => props[k] ?? null,
        setProperty: (k, v) => { props[k] = v; },
        deleteProperty: k => { delete props[k]; },
      }),
    },
    ContentService: {
      MimeType: { JSON: 'json' },
      createTextOutput: text => ({ text, setMimeType() { return this; } }),
    },
    Utilities: { getUuid: () => crypto.randomUUID() },
    Session: { getScriptTimeZone: () => 'Asia/Seoul' },
    Logger: { log() {} },
    Calendar: {
      Colors: { get: () => ({ event: { 11: { background: '#dc2127' } } }) },
      CalendarList: {
        list: () => ({ items: [
          { id: 'me@gmail.com', summary: 'Selim', backgroundColor: '#9fe1e7', primary: true, accessRole: 'owner', selected: true },
          { id: 'hidden', summary: 'Hidden', hidden: true },
        ] }),
      },
      Events: {
        list: (id) => ({ items: [
          { id: 'e1', status: 'confirmed', summary: 'Lab meeting', start: { dateTime: '2026-10-12T10:00:00+09:00' }, end: { dateTime: '2026-10-12T11:00:00+09:00' },
            colorId: '11', hangoutLink: 'https://meet.google.com/abc', description: '<b>Agenda</b><br>GaussVLA', htmlLink: 'https://calendar.google.com/e1' },
          { id: 'e2', status: 'cancelled', summary: 'Gone', start: { date: '2026-10-13' } },
          { id: 'e3', status: 'confirmed', summary: 'Declined', start: { date: '2026-10-14' }, attendees: [{ self: true, responseStatus: 'declined' }] },
          { id: 'e4', status: 'confirmed', summary: 'CVPR deadline', start: { date: '2026-11-14' }, end: { date: '2026-11-15' } },
        ].map(e => ({ ...e, _cal: id })) }),
        insert: (resource, calId) => { inserted.events.push([resource, calId]); return { id: 'new', htmlLink: 'https://calendar.google.com/new' }; },
      },
    },
    Tasks: {
      Tasklists: {
        list: () => ({ items: [{ id: 'L1', title: 'My Tasks' }] }),
        get: id => ({ id, title: 'My Tasks' }),
      },
      Tasks: {
        list: (listId, args) => args.showCompleted
          ? { items: [{ id: 't2', title: 'Sent reviews', status: 'completed', completed: '2026-10-11T01:00:00Z' }, { id: 't1', title: 'Rebuttal', status: 'needsAction' }] }
          : { items: [{ id: 't1', title: 'Rebuttal', status: 'needsAction', due: '2026-10-15T00:00:00.000Z' }, { id: 'tx', title: '' }] },
        insert: (body, listId) => { inserted.tasks.push([body, listId]); return { id: 'tn', title: body.title, due: body.due, status: 'needsAction' }; },
        patch: (patch, listId, id) => { inserted.patches.push([patch, listId, id]); return { id, title: 'x', status: patch.status }; },
      },
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SOURCE, ctx);
  const post = body => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(body) } }).text);
  // Objects built inside the sandbox have that realm's prototypes; compare plain copies.
  const plain = () => JSON.parse(JSON.stringify(inserted));
  return { ctx, post, props, plain };
}

const SECRET = 'b'.repeat(64);

test('refuses a request without the right secret', () => {
  const { post } = sandbox();
  assert.equal(post({ action: 'agenda' }).ok, false);
  assert.equal(post({ action: 'agenda', secret: 'wrong' }).ok, false);
  assert.equal(post({ action: 'nope', secret: SECRET }).error, 'Unknown action.');
});

test('agenda returns visible calendars, live events and open plus recently done tasks', () => {
  const { post } = sandbox();
  const r = post({ action: 'agenda', secret: SECRET, timeMin: '2026-10-10T15:00:00Z', timeMax: '2026-12-31T15:00:00Z' });
  assert.equal(r.ok, true);
  assert.deepEqual(r.calendars.map(c => c.id), ['me@gmail.com']);
  assert.deepEqual(r.events.map(e => e.title), ['Lab meeting', 'CVPR deadline']);
  const [lab, cvpr] = r.events;
  assert.equal(lab.color, '#dc2127');
  assert.equal(lab.video, 'https://meet.google.com/abc');
  assert.equal(lab.description, 'Agenda\nGaussVLA');
  assert.equal(cvpr.allDay, true);
  assert.equal(cvpr.color, '#9fe1e7');
  assert.deepEqual(r.tasks.map(t => [t.id, t.done, t.due]), [['t1', false, '2026-10-15'], ['t2', true, '']]);
});

test('createEvent builds timed and all-day resources and never ends before it starts', () => {
  const { post, plain } = sandbox();
  assert.equal(post({ action: 'createEvent', secret: SECRET, title: 'Write', date: '2026-10-12', start: '23:30', end: '10:00' }).ok, true);
  assert.equal(post({ action: 'createEvent', secret: SECRET, title: 'Due', date: '2026-12-31', allDay: true }).ok, true);
  assert.equal(post({ action: 'createEvent', secret: SECRET, title: 'No date' }).ok, false);
  const [[timed, cal], [allDay]] = plain().events;
  assert.equal(cal, 'primary');
  assert.deepEqual([timed.start.dateTime, timed.end.dateTime, timed.start.timeZone], ['2026-10-12T23:30:00', '2026-10-12T23:59:00', 'Asia/Seoul']);
  assert.deepEqual([allDay.start.date, allDay.end.date], ['2026-12-31', '2027-01-01']);
});

test('createTask and setTask shape Google Tasks requests', () => {
  const { post, plain } = sandbox();
  const made = post({ action: 'createTask', secret: SECRET, title: 'Email Prof. Kim', due: '2026-10-12' });
  assert.equal(made.task.due, '2026-10-12');
  assert.deepEqual(plain().tasks[0], [{ title: 'Email Prof. Kim', notes: '', due: '2026-10-12T00:00:00.000Z' }, '@default']);
  post({ action: 'setTask', secret: SECRET, listId: 'L1', id: 't1', done: false });
  assert.deepEqual(plain().patches[0], [{ status: 'needsAction', completed: null }, 'L1', 't1']);
  assert.equal(post({ action: 'setTask', secret: SECRET, done: true }).ok, false);
});

test('setup keeps an existing secret and rotateSecret replaces it', () => {
  const { ctx, props } = sandbox();
  ctx.setup();
  assert.equal(props.DESK_SECRET, SECRET);
  ctx.rotateSecret();
  assert.notEqual(props.DESK_SECRET, SECRET);
  assert.equal(props.DESK_SECRET.length, 64);
});
