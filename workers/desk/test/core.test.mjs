// Tests for the desk's browser-side logic in assets/js/desk/core.js.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const core = createRequire(import.meta.url)('../../../assets/js/desk/core.js');
const NOW = new Date(2026, 9, 11, 9, 30); // Sunday 11 Oct 2026, local time

test('parseQuick pulls dates, times, ranges and tags out of a sentence', () => {
  assert.deepEqual(core.parseQuick('Draft ICRA rebuttal tomorrow 14:00 #writing', NOW),
    { title: 'Draft ICRA rebuttal', date: '2026-10-12', start: '14:00', end: '', tags: ['writing'] });
  assert.deepEqual(core.parseQuick('Lab meeting fri 10am-11:30am', NOW),
    { title: 'Lab meeting', date: '2026-10-16', start: '10:00', end: '11:30', tags: [] });
  assert.equal(core.parseQuick('Call Prof. Kim next mon', NOW).date, '2026-10-12');
  assert.equal(core.parseQuick('Call Prof. Kim next mon', NOW).title, 'Call Prof. Kim');
  assert.equal(core.parseQuick('Submit 2026-11-16', NOW).date, '2026-11-16');
  assert.equal(core.parseQuick('Renew visa 3/2', NOW).date, '2027-03-02');
  assert.equal(core.parseQuick('Camera ready nov 20', NOW).date, '2026-11-20');
  assert.equal(core.parseQuick('Review in 2w', NOW).date, '2026-10-25');
  assert.equal(core.parseQuick('Sunday reset sun', NOW).date, '2026-10-18', 'a weekday always means the next one');
});

test('parseQuick leaves ordinary words and bare numbers in the title', () => {
  const r = core.parseQuick('Read 3 papers on world models', NOW);
  assert.deepEqual([r.title, r.date, r.start], ['Read 3 papers on world models', '', '']);
  assert.equal(core.parseQuick('Monday standup notes', NOW).date, '2026-10-12');
  assert.equal(core.parseQuick('25:00 is not a time', NOW).start, '');
});

test('countdown and urgency label days relative to today', () => {
  assert.deepEqual([0, 1, -1, -4, 12, 70].map(core.countdown), ['today', 'tomorrow', 'yesterday', '4 d ago', '12 d', '10 wk']);
  assert.deepEqual([-1, 2, 10, 40].map(core.urgency), ['past', 'hot', 'near', 'far']);
});

test('collectDeadlines merges desk, Notion and watched conferences, and keeps only open overdue items', () => {
  const list = core.collectDeadlines({
    today: '2026-10-11',
    entries: [
      { id: 'a', title: 'Plan till July', deadline: '2027-01-30', axis: 'world', status: 'inbox' },
      { id: 'b', title: 'V2D registration', deadline: '2026-09-21', axis: 'data', status: 'shortlist' },
      { id: 'c', title: 'Old done thing', deadline: '2026-10-01', status: 'done' },
    ],
    notion: [{ label: 'Publications', rows: [
      { id: 'p1', title: 'AFFORD-X', date: '2026-11-16T23:59:00.000-12:00', done: false },
      { id: 'p2', title: 'Accepted paper', date: '2026-10-02', done: true },
    ] }],
    conferences: [
      { name: 'CVPR', edition: 2027, website: 'https://cvpr.thecvf.com', timeline: [{ label: 'Paper Submission', date: '2026-11-13' }, { label: 'Decisions', date: 'tba' }] },
      { name: 'KDD', edition: 2027, timeline: [{ label: 'Paper', date: '2026-10-20' }] },
      { name: 'ICLR', edition: 2027, timeline: [{ label: 'Paper Submission', date: '2026-09-25' }] },
    ],
    watched: ['cvpr', 'ICLR'],
  });
  assert.deepEqual(list.map(d => d.title), ['V2D registration', 'CVPR 2027 Paper Submission', 'AFFORD-X', 'Plan till July']);
  const afford = list.find(d => d.title === 'AFFORD-X');
  assert.deepEqual([afford.date, afford.time, afford.days, afford.urgency], ['2026-11-16', '23:59', 36, 'far']);
  assert.equal(list[0].urgency, 'past');
  assert.equal(list.find(d => d.source === 'Conference').color, core.SOURCE_COLORS.Conference);
});

test('normEvent handles all-day spans, timed events and broken ends', () => {
  const allDay = core.normEvent({ id: 'x', start: '2026-10-12', end: '2026-10-14', allDay: true });
  assert.equal(core.eventOnDay(allDay, '2026-10-13'), true);
  assert.equal(core.eventOnDay(allDay, '2026-10-14'), false);
  const timed = core.normEvent({ id: 'y', start: '2026-10-12T10:00:00+09:00', end: '2026-10-12T09:00:00+09:00' });
  assert.equal(timed.end - timed.start, 36e5);
  assert.equal(core.normEvent({ id: 'z' }), null);
});

test('bucketTasks sorts tasks into overdue, today, upcoming, undated and recently done', () => {
  const tasks = core.unifyTasks(
    [
      { id: '1', listId: 'L', title: 'Late', due: '2026-10-09', done: false },
      { id: '2', listId: 'L', title: 'Now', due: '2026-10-11', done: false },
      { id: '3', listId: 'L', title: 'Someday', due: '', done: false },
      { id: '4', listId: 'L', title: 'Finished', due: '2026-10-11', done: true, completed: '2026-10-11T01:00:00Z' },
      { id: '5', listId: 'L', title: 'Ancient', due: '2026-01-01', done: true, completed: '2026-01-01T01:00:00Z' },
    ],
    [{ id: 'd1', version: 1, data: { title: 'Desk task', due: '2026-10-13', time: '09:00' } }],
  );
  const b = core.bucketTasks(tasks, '2026-10-11');
  assert.deepEqual(Object.fromEntries(Object.entries(b).map(([k, v]) => [k, v.map(t => t.title)])),
    { overdue: ['Late'], today: ['Now'], upcoming: ['Desk task'], undated: ['Someday'], done: ['Finished'] });
  assert.equal(b.upcoming[0].source, 'desk');
});

test('gcalTemplateUrl builds timed and all-day Google Calendar links', () => {
  const timed = core.gcalTemplateUrl({ title: 'Write intro', date: '2026-10-12', start: '14:00', end: '15:30', tz: 'Asia/Seoul' });
  assert.match(timed, /dates=20261012T140000\/20261012T153000/);
  assert.match(timed, /ctz=Asia%2FSeoul/);
  const allDay = core.gcalTemplateUrl({ title: 'Deadline', date: '2026-12-31', allDay: true });
  assert.match(allDay, /dates=20261231\/20270101/);
});

test('entryMarkdown and notionDefaults turn an entry into a Notion row', () => {
  const e = core.normaliseEntry('x', {
    title: 'T', kind: 'target', axis: 'world', status: 'active', conviction: 5, deadline: '2027-07-30',
    thesis: '<b>World model</b> first<br>then VLA', experiment: '<ul><li>step one</li></ul>', tags: ['wm'],
  });
  const md = core.entryMarkdown(e);
  assert.match(md, /## Thesis\n\nWorld model first\nthen VLA/);
  assert.match(md, /- step one/);
  assert.match(md, /Tags: wm/);
  const d = core.notionDefaults(e, [
    { name: 'Milestone', type: 'title', options: [] },
    { name: 'Status', type: 'select', options: ['Not started', 'In progress', 'Done'] },
    { name: 'Category', type: 'select', options: ['Skill'] },
    { name: 'Target', type: 'date', options: [] },
    { name: 'Notes', type: 'rich_text', options: [] },
  ]);
  assert.deepEqual(d, { Status: 'In progress', Target: '2027-07-30', Notes: 'World model first\nthen VLA' });
});

test('htmlToText decodes entities once and keeps line structure', () => {
  assert.equal(core.htmlToText('<p>a &amp;lt; b</p><p>c&nbsp;d</p>'), 'a &lt; b\nc d');
});

test('parseQuick turns a duration after a start time into an end time', () => {
  const r = core.parseQuick('Deep work 14:00 for 90m', NOW);
  assert.deepEqual([r.title, r.start, r.end], ['Deep work', '14:00', '15:30']);
  assert.equal(core.parseQuick('Call Prof. Kim 2pm 45m', NOW).end, '14:45');
  assert.equal(core.parseQuick('Review 10:00 1h30', NOW).end, '11:30');
  assert.equal(core.parseQuick('Gym 1h tomorrow 18:00', NOW).end, '19:00', 'the duration may come before the time');
  assert.equal(core.parseQuick('Late session 23:30 for 2h', NOW).end, '23:59', 'an event never runs past midnight');
});

test('parseQuick keeps a duration in the title when there is no start time', () => {
  const r = core.parseQuick('Read for 1h tomorrow', NOW);
  assert.deepEqual([r.title, r.date, r.start, r.end], ['Read for 1h', '2026-10-12', '', '']);
});

test('addMinutes and fmtDuration handle clock arithmetic and labels', () => {
  assert.equal(core.addMinutes('14:00', 90), '15:30');
  assert.equal(core.addMinutes('09:45', 15), '10:00');
  assert.equal(core.addMinutes('23:30', 60), '23:59');
  assert.deepEqual([0, 25, 60, 70, 150].map(core.fmtDuration), ['0 min', '25 min', '1 h', '1 h 10', '2 h 30']);
});

// Local-time events on Sunday 11 Oct 2026.
const ev = (h1, m1, h2, m2, extra = {}) => ({
  start: new Date(2026, 9, 11, h1, m1), end: new Date(2026, 9, 11, h2, m2), allDay: false, ...extra,
});

test('freeSlots finds the gaps of at least the minimum length inside the planning window', () => {
  const events = [
    ev(10, 0, 11, 0), ev(10, 30, 12, 0), ev(14, 0, 16, 30), ev(21, 0, 23, 0),
    { start: new Date(2026, 9, 11), end: new Date(2026, 9, 12), allDay: true },
  ];
  const slots = core.freeSlots(events, '2026-10-11', { from: new Date(2026, 9, 11, 9, 32), start: '08:00', end: '22:00', min: 20 });
  const hm = d => core.pad2(d.getHours()) + ':' + core.pad2(d.getMinutes());
  assert.deepEqual(slots.map(s => [hm(s.start), hm(s.end), s.mins]),
    [['09:35', '10:00', 25], ['12:00', '14:00', 120], ['16:30', '21:00', 270]]);
  assert.deepEqual(core.freeSlots(events, '2026-10-11', { from: new Date(2026, 9, 11, 22, 5), start: '08:00', end: '22:00' }), []);
  assert.equal(core.freeSlots([], '2026-10-12', { from: new Date(2026, 9, 11, 9, 0), start: '08:00', end: '22:00' })[0].mins, 840,
    'a later day starts at the window start');
});

test('nowNext picks the running event that ends first and the next one to start', () => {
  const at = new Date(2026, 9, 11, 10, 40);
  const events = [ev(9, 0, 12, 0, { title: 'Long block' }), ev(10, 30, 11, 0, { title: 'Stand-up' }), ev(14, 0, 15, 0, { title: 'Review' }),
    { start: new Date(2026, 9, 11), end: new Date(2026, 9, 12), allDay: true, title: 'Holiday' }];
  const r = core.nowNext(events, at);
  assert.equal(r.current.title, 'Stand-up');
  assert.equal(r.next.title, 'Review');
  assert.deepEqual(core.nowNext([], at), { current: null, next: null });
});

test('planSlot offers the next free block of the wanted length, rolling over to tomorrow', () => {
  const opts = { start: '08:00', end: '22:00', length: 60, min: 30 };
  assert.deepEqual(core.planSlot([ev(10, 0, 11, 0), ev(11, 20, 13, 0)], new Date(2026, 9, 11, 10, 20), opts),
    { date: '2026-10-11', start: '13:00', end: '14:00' }, 'skips a gap shorter than the minimum');
  assert.deepEqual(core.planSlot([ev(9, 0, 11, 0)], new Date(2026, 9, 11, 8, 50), opts),
    { date: '2026-10-11', start: '11:00', end: '12:00' }, 'skips a gap that a rounded start leaves too short');
  assert.deepEqual(core.planSlot([], new Date(2026, 9, 11, 21, 40), opts),
    { date: '2026-10-12', start: '08:00', end: '09:00' });
  assert.deepEqual(core.planSlot([ev(14, 0, 15, 0)], new Date(2026, 9, 11, 13, 20), opts),
    { date: '2026-10-11', start: '13:30', end: '14:00' }, 'a gap shorter than the wanted length still fits the minimum');
});
