// Local stand-in for the deployed Apps Script web app: the real Code.gs, run
// against the fakes in test/gas.mjs, with generic sample Calendar, Tasks and
// Notion data dated around today. For UI work and the browser checks.
//
//   node dev/server.mjs          -> http://localhost:8787 (open mode)
//   PRIVATE=1 node dev/server.mjs  (private mode, passphrase "local desk passphrase")
import http from 'node:http';
import { makeGas } from '../test/gas.mjs';

const PORT = Number(process.env.PORT || 8787);
const day = n => { const d = new Date(); d.setDate(d.getDate() + n); return d; };
const ymd = d => d.toISOString().slice(0, 10);
const at = (n, hh, mm = 0) => { const d = day(n); d.setHours(hh, mm, 0, 0); return d.toISOString(); };
const timed = (id, title, n, h1, m1, h2, m2, extra = {}) => ({ id, status: 'confirmed', summary: title, start: { dateTime: at(n, h1, m1) }, end: { dateTime: at(n, h2, m2) }, htmlLink: 'https://calendar.google.com/', ...extra });

const google = {
  calendars: [
    { id: 'me@example.com', summary: 'Personal', backgroundColor: '#039be5', primary: true, accessRole: 'owner', selected: true },
    { id: 'lab@example.com', summary: 'Lab', backgroundColor: '#33b679', accessRole: 'writer', selected: true },
    { id: 'holidays', summary: 'Holidays', backgroundColor: '#f6bf26', accessRole: 'reader', selected: true },
  ],
  events: {
    'me@example.com': [
      timed('e2', 'Writing block', 0, 14, 0, 16, 30),
      timed('e3', 'Reading group', 1, 9, 30, 10, 30, { colorId: '11' }),
      timed('e5', 'Seminar', 3, 15, 0, 16, 0, { location: 'Hall B · https://zoom.us/j/123456' }),
      timed('e6', 'Gym', 0, 18, 0, 19, 0, { recurringEventId: 'gym' }),
    ],
    'lab@example.com': [
      timed('e1', 'Lab meeting', 0, 10, 0, 11, 0, { location: 'Room 301', hangoutLink: 'https://meet.google.com/xyz-abcd-efg' }),
      { id: 'e4', status: 'confirmed', summary: 'Robot booked', start: { date: ymd(day(2)) }, end: { date: ymd(day(4)) } },
    ],
    holidays: [{ id: 'h1', status: 'confirmed', summary: 'Public holiday', start: { date: ymd(day(5)) }, end: { date: ymd(day(6)) } }],
  },
  tasklists: [{ id: 'L1', title: 'My Tasks' }],
  tasks: {
    L1: [
      { id: 't1', title: 'Reply to reviewer comments', status: 'needsAction', due: ymd(day(-1)) + 'T00:00:00.000Z' },
      { id: 't2', title: 'Book seminar room', status: 'needsAction', due: ymd(day(0)) + 'T00:00:00.000Z' },
      { id: 't3', title: 'Read two world-model papers', status: 'needsAction', due: ymd(day(2)) + 'T00:00:00.000Z' },
      { id: 't4', title: 'Renew library loan', status: 'needsAction' },
      { id: 't5', title: 'Send weekly update', status: 'completed', due: ymd(day(0)) + 'T00:00:00.000Z', completed: new Date().toISOString() },
    ],
  },
};

const ROWS = {
  'e53afef4-a52d-4aa6-a0c2-23a2490a7fde': [['Paper A camera-ready', 6, 'Camera-ready'], ['Paper B rebuttal', 19, 'Rebuttal'], ['Paper C', -9, 'Accepted']],
  '7b63f21a-ea6a-4f9b-b91d-3769c4e02fcf': [['Fellowship application', 24, 'Preparing'], ['Summer school', 51, 'Interested']],
  '21116060-ed74-4ba6-a9e4-f8a952d6424a': [['Project milestone review', 2, 'Active']],
  '086a6332-af9f-401b-b025-32bcd01e6c05': [['Second first-author paper', 88, 'In progress']],
  '70ab5a2e-e301-47f9-b857-93b2b41b48dd': [['Follow up with collaborator', 1, '']],
};
const DATE_PROP = { '086a6332-af9f-401b-b025-32bcd01e6c05': 'Target', '70ab5a2e-e301-47f9-b857-93b2b41b48dd': 'Next Follow-up' };
const notion = {
  handler(url, method) {
    const m = /\/data_sources\/([0-9a-f-]+)(\/query)?$/.exec(url);
    if (m && m[2]) {
      const prop = DATE_PROP[m[1]] || 'Deadline';
      return { body: { has_more: false, results: (ROWS[m[1]] || []).map(([title, n, status], i) => ({
        id: m[1].slice(0, 8) + i, url: 'https://www.notion.so/' + i,
        properties: { Name: { type: 'title', title: [{ plain_text: title }] }, [prop]: { type: 'date', date: { start: ymd(day(n)) } },
          Status: { type: 'select', select: status ? { name: status } : null }, Stage: { type: 'select', select: status ? { name: status } : null } },
      })) } };
    }
    if (m) {
      return { body: { title: [{ plain_text: 'Ideas' }], properties: {
        Idea: { type: 'title' }, Stage: { type: 'select', select: { options: ['Seed', 'Validating', 'Active', 'Parked'].map(name => ({ name })) } },
        Promise: { type: 'select', select: { options: ['Low', 'Medium', 'High'].map(name => ({ name })) } }, Concept: { type: 'rich_text' }, Novelty: { type: 'rich_text' } } } };
    }
    if (url.endsWith('/pages') && method === 'post') return { body: { id: 'p-new', url: 'https://www.notion.so/new' } };
    return { code: 404, body: { message: 'not mocked' } };
  },
};

const gas = makeGas({ google, notion });
gas.ctx.setup();
gas.props.NOTION_TOKEN = 'ntn_mock';
if (process.env.PRIVATE) Object.assign(gas.props, { DESK_MODE: 'private', DESK_PASSPHRASE: 'local desk passphrase' });

// Apps Script answers every request with Access-Control-Allow-Origin: *.
http.createServer(async (req, res) => {
  const headers = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (req.method === 'OPTIONS') { res.writeHead(405, headers); res.end(); return; } // Apps Script cannot answer preflight either
  let body = '';
  for await (const c of req) body += c;
  const out = req.method === 'POST' ? gas.ctx.doPost({ postData: { contents: body } }).text : gas.ctx.doGet({ parameter: {} }).text;
  res.writeHead(200, headers);
  res.end(out);
}).listen(PORT, () => console.log('desk dev backend on http://localhost:' + PORT + (process.env.PRIVATE ? ' (private)' : ' (open)')));
