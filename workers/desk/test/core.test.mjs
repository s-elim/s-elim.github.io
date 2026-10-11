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
