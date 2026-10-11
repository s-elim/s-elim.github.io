// Local stand-in for the deployed Worker: the real handler, D1 replaced by a
// SQLite file, and (with MOCK=1) Notion and Google answered from generic sample
// data dated around today. Used for UI work and the browser checks.
//
//   node dev/server.mjs                 -> http://localhost:8787, passphrase "local desk passphrase"
//   MOCK=1 DB=/tmp/desk.sqlite node dev/server.mjs
import http from 'node:http';
import { handle } from '../src/worker.js';
import { fakeD1 } from '../test/fake-d1.mjs';

const PORT = Number(process.env.PORT || 8787);
const env = {
  DB: fakeD1(process.env.DB || ':memory:'),
  ALLOWED_ORIGINS: process.env.ORIGINS || 'http://localhost:4000,http://127.0.0.1:4000',
  DESK_PASSPHRASE: process.env.PASS || 'local desk passphrase',
  ...(process.env.MOCK ? { NOTION_TOKEN: 'ntn_mock', GOOGLE_BRIDGE_URL: 'https://script.google.com/mock', GOOGLE_BRIDGE_SECRET: 'm'.repeat(32) } : {}),
};

const day = n => { const d = new Date(); d.setDate(d.getDate() + n); return d; };
const ymd = d => d.toISOString().slice(0, 10);
const at = (n, hh, mm = 0) => { const d = day(n); d.setHours(hh, mm, 0, 0); return d.toISOString(); };

const googleTasks = [
  { id: 't1', listId: 'L1', list: 'My Tasks', title: 'Reply to reviewer comments', due: ymd(day(-1)), done: false },
  { id: 't2', listId: 'L1', list: 'My Tasks', title: 'Book seminar room', due: ymd(day(0)), done: false },
  { id: 't3', listId: 'L1', list: 'My Tasks', title: 'Read two world-model papers', due: ymd(day(2)), done: false },
  { id: 't4', listId: 'L1', list: 'My Tasks', title: 'Renew library loan', due: '', done: false },
  { id: 't5', listId: 'L1', list: 'My Tasks', title: 'Send weekly update', due: ymd(day(0)), done: true, completed: new Date().toISOString() },
];
function agenda() {
  return {
    ok: true,
    calendars: [{ id: 'primary', title: 'Personal', color: '#039be5', primary: true, writable: true }, { id: 'lab', title: 'Lab', color: '#33b679', writable: true }],
    events: [
      { id: 'e1', calendarId: 'lab', calendar: 'Lab', color: '#33b679', title: 'Lab meeting', start: at(0, 10), end: at(0, 11), allDay: false, video: 'https://meet.google.com/xyz-abcd-efg', location: 'Room 301' },
      { id: 'e2', calendarId: 'primary', calendar: 'Personal', color: '#039be5', title: 'Writing block', start: at(0, 14), end: at(0, 16, 30), allDay: false },
      { id: 'e3', calendarId: 'primary', calendar: 'Personal', color: '#8e24aa', title: 'Reading group', start: at(1, 9, 30), end: at(1, 10, 30), allDay: false },
      { id: 'e4', calendarId: 'lab', calendar: 'Lab', color: '#f6bf26', title: 'Robot booked', start: ymd(day(2)), end: ymd(day(4)), allDay: true },
      { id: 'e5', calendarId: 'primary', calendar: 'Personal', color: '#e67c73', title: 'Seminar', start: at(3, 15), end: at(3, 16), allDay: false },
      { id: 'e6', calendarId: 'primary', calendar: 'Personal', color: '#039be5', title: 'Gym', start: at(0, 18), end: at(0, 19), allDay: false },
    ],
    tasklists: [{ id: 'L1', title: 'My Tasks' }],
    tasks: googleTasks,
    warnings: [],
  };
}
const notionRows = {
  'e53afef4-a52d-4aa6-a0c2-23a2490a7fde': [['Paper A camera-ready', 6, 'Camera-ready'], ['Paper B rebuttal', 19, 'Rebuttal'], ['Paper C', -9, 'Accepted']],
  '7b63f21a-ea6a-4f9b-b91d-3769c4e02fcf': [['Fellowship application', 24, 'Preparing'], ['Summer school', 51, 'Interested']],
  '21116060-ed74-4ba6-a9e4-f8a952d6424a': [['Project milestone review', 2, 'Active']],
  '086a6332-af9f-401b-b025-32bcd01e6c05': [['Second first-author paper', 88, 'In progress']],
  '70ab5a2e-e301-47f9-b857-93b2b41b48dd': [['Follow up with collaborator', 1, '']],
};
const DATE_PROP = { '086a6332-af9f-401b-b025-32bcd01e6c05': 'Target', '70ab5a2e-e301-47f9-b857-93b2b41b48dd': 'Next Follow-up' };

async function mockFetch(url, init = {}) {
  const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json' } });
  if (url.startsWith('https://script.google.com/mock')) {
    const req = JSON.parse(init.body);
    if (req.action === 'agenda') return json(agenda());
    if (req.action === 'setTask') { const t = googleTasks.find(x => x.id === req.id); if (t) t.done = req.done; return json({ ok: true, task: t }); }
    if (req.action === 'createTask') { const t = { id: 't' + Date.now(), listId: 'L1', list: 'My Tasks', title: req.title, due: req.due || '', done: false }; googleTasks.push(t); return json({ ok: true, task: t }); }
    if (req.action === 'createEvent') return json({ ok: true, id: 'new', link: 'https://calendar.google.com/' });
    return json({ ok: false, error: 'unknown' });
  }
  const m = /\/data_sources\/([0-9a-f-]+)(\/query)?$/.exec(url);
  if (m && m[2]) {
    const prop = DATE_PROP[m[1]] || 'Deadline';
    const results = (notionRows[m[1]] || []).map(([title, n, status], i) => ({
      id: m[1].slice(0, 8) + i, url: 'https://www.notion.so/' + i,
      properties: { Name: { type: 'title', title: [{ plain_text: title }] }, [prop]: { type: 'date', date: { start: ymd(day(n)) } },
        Status: { type: 'select', select: status ? { name: status } : null }, Stage: { type: 'select', select: status ? { name: status } : null } },
    }));
    return json({ results, has_more: false });
  }
  if (m) {
    return json({ title: [{ plain_text: 'Ideas' }], properties: {
      Idea: { type: 'title' }, Stage: { type: 'select', select: { options: ['Seed', 'Validating', 'Active', 'Parked'].map(name => ({ name })) } },
      Promise: { type: 'select', select: { options: ['Low', 'Medium', 'High'].map(name => ({ name })) } }, Concept: { type: 'rich_text' }, Novelty: { type: 'rich_text' } } });
  }
  if (url.endsWith('/pages')) return json({ id: 'p-new', url: 'https://www.notion.so/new' });
  return json({ message: 'not mocked' }, 404);
}

http.createServer(async (req, res) => {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;
  const request = new Request('http://localhost:' + PORT + req.url, {
    method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : body,
  });
  const response = await handle(request, env, process.env.MOCK ? mockFetch : fetch);
  res.writeHead(response.status, Object.fromEntries(response.headers));
  res.end(Buffer.from(await response.arrayBuffer()));
}).listen(PORT, () => console.log('desk dev server on http://localhost:' + PORT + (process.env.MOCK ? ' (mock Google + Notion)' : '')));
