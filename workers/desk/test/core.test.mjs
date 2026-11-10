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

test('parseQuick reads evening ranges however they are typed', () => {
  const at = t => { const r = core.parseQuick(t, NOW); return [r.title, r.start, r.end]; };
  assert.deepEqual(at('Meeting 9-10pm'), ['Meeting', '21:00', '22:00'], 'the meridiem on the end applies to the start');
  assert.deepEqual(at('Meeting 9-10 pm'), ['Meeting', '21:00', '22:00']);
  assert.deepEqual(at('Meeting 9pm - 10pm'), ['Meeting', '21:00', '22:00']);
  assert.deepEqual(at('Meeting 9 to 10pm'), ['Meeting', '21:00', '22:00']);
  assert.deepEqual(at('Dinner 9:30-10:30pm'), ['Dinner', '21:30', '22:30']);
  assert.deepEqual(at('Lunch 11-1pm'), ['Lunch', '11:00', '13:00'], 'flips the start when the shared meridiem would put it after the end');
  assert.deepEqual(at('Call 11pm-1am'), ['Call', '23:00', '01:00'], 'past midnight is kept for the backend to book');
  assert.deepEqual(at('Talk 9 pm'), ['Talk', '21:00', '']);
  assert.deepEqual(at('Read pages 3 to 5'), ['Read pages 3 to 5', '', ''], 'plain numbers stay words');
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

test('eventMarkKey gives every occurrence of a repeating event one key', () => {
  const one = core.eventMarkKey({ eventId: 'abc123', calendarId: 'me@example.com' });
  assert.equal(one, 'ev:abc123@me@example.com');
  const occ = id => core.eventMarkKey({ eventId: id, calendarId: 'lab', recurring: true });
  assert.equal(occ('base9_20261102T090000Z'), 'ev:base9@lab');
  assert.equal(occ('base9_20261109T090000Z'), 'ev:base9@lab');
  assert.equal(occ('base9_20261102'), 'ev:base9@lab', 'an all-day occurrence');
  assert.equal(core.eventMarkKey({ eventId: 'odd_id', calendarId: 'lab', recurring: true, series: 'gym' }), 'ev:gym@lab',
    'a series id from the backend wins over the name');
  assert.equal(core.eventMarkKey({ eventId: 'base9_20261102T090000Z', calendarId: 'lab' }), 'ev:base9_20261102T090000Z@lab',
    'a one-off event keeps its full id');
  assert.equal(core.normEvent({ id: 'x', start: '2026-11-02', series: 'base9' }).series, 'base9');
});

test('normMark keeps only known fields in range and treats an empty style as none', () => {
  assert.deepEqual(core.normMark({ c: 3, h: 2, b: true, i: true, s: true, at: '2026-11-02' }),
    { c: 3, h: 2, b: true, i: true, s: true, at: '2026-11-02' });
  assert.deepEqual(core.normMark({ c: 9, h: 0, b: 'yes', i: 1, s: true, at: 'soon', x: '<script>' }), { s: true });
  assert.deepEqual(core.normMark({ c: 2.5, h: -1 }), null);
  assert.equal(core.normMark({ b: false, at: '2026-11-02' }), null);
  assert.equal(core.normMark(null), null);
  assert.equal(core.normMark('bold'), null);
});

test('normMarks drops unknown keys and broken styles', () => {
  const items = JSON.parse('{"__proto__": {"b": true}, "ev:a@c": {"b": true}, "g:L1:t1": {"c": 7}, "d:t9": {"h": 1}, "x": {"b": true}}');
  assert.deepEqual(core.normMarks(items), { 'ev:a@c': { b: true }, 'd:t9': { h: 1 } });
  assert.deepEqual(core.normMarks(null), {});
  assert.deepEqual(core.normMarks([{ b: true }]), {});
});

test('markClass turns a style into classes, with the highlight optional', () => {
  assert.equal(core.markClass({ c: 4, h: 1, b: true, i: true, s: true }), 'dk-mk is-b is-i is-star tc-4 hl-1');
  assert.equal(core.markClass({ c: 4, h: 1 }, { text: true }), 'dk-mk tc-4');
  assert.equal(core.markClass({ c: 99 }), '');
  assert.equal(core.markClass(null), '');
});

test('pruneMarks forgets styles on items gone for months, never ones still in view', () => {
  const items = { 'ev:old@c': { b: true, at: '2026-05-01' }, 'ev:live@c': { b: true, at: '2026-01-01' },
    'g:L:t': { c: 1, at: '2026-10-30' }, 'd:t': { s: true } };
  assert.deepEqual(Object.keys(core.pruneMarks(items, ['ev:live@c'], '2026-11-02')).sort(), ['d:t', 'ev:live@c', 'g:L:t']);
  assert.deepEqual(Object.keys(core.pruneMarks(items, [], '2026-11-02', 400)).sort(), Object.keys(items).sort());
  const seen = core.pruneMarks(items, ['ev:live@c'], '2026-11-02');
  assert.equal(seen['ev:live@c'].at, '2026-11-02', 'an item in view counts as seen today');
  assert.equal(items['ev:live@c'].at, '2026-01-01', 'the input is not changed');
});

test('starFirst lifts starred items and keeps the order otherwise', () => {
  const list = ['a', 'b', 'c', 'd'];
  assert.deepEqual(core.starFirst(list, x => x === 'c' || x === 'd'), ['c', 'd', 'a', 'b']);
  assert.deepEqual(core.starFirst(list, () => false), list);
  assert.deepEqual(core.starFirst(null, () => true), []);
});

test('parseQuick reads repeats and leaves look-alike words in the title', () => {
  const rep = t => { const r = core.parseQuick(t, NOW); return [r.title, r.date, r.repeat && core.rrule(r.repeat, r.date)]; };
  // NOW is Sunday 11 Oct; "every <weekday>" starts on the next one, today included.
  assert.deepEqual(rep('Lab meeting every mon 10-11am'), ['Lab meeting', '2026-10-12', 'RRULE:FREQ=WEEKLY;BYDAY=MO']);
  assert.deepEqual(rep('Reset every sunday'), ['Reset', '2026-10-11', 'RRULE:FREQ=WEEKLY;BYDAY=SU']);
  assert.deepEqual(rep('Standup weekdays 9am'), ['Standup', '2026-10-12', 'RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'], 'typed on a Sunday, weekdays start Monday');
  assert.deepEqual(rep('1:1 biweekly thu'), ['1:1', '2026-10-15', 'RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TH']);
  assert.deepEqual(rep('Sync every other week tomorrow'), ['Sync', '2026-10-12', 'RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO']);
  assert.deepEqual(rep('Group sync every 3 weeks 2026-10-14'), ['Group sync', '2026-10-14', 'RRULE:FREQ=WEEKLY;INTERVAL=3;BYDAY=WE']);
  assert.deepEqual(rep('Journal daily 22:00'), ['Journal', '', 'RRULE:FREQ=DAILY']);
  assert.deepEqual(rep('Report monthly 2026-11-30'), ['Report', '2026-11-30', 'RRULE:FREQ=MONTHLY']);
  assert.equal(core.parseQuick('Plain event tomorrow', NOW).repeat, undefined, 'no repeat key unless one is typed');
  // Words that merely start like a weekday or month are not dates.
  assert.equal(core.parseQuick('Wedding photos', NOW).date, '');
  assert.equal(core.parseQuick('Sunset walk', NOW).date, '');
  assert.equal(core.parseQuick('Thurs seminar', NOW).date, '2026-10-15');
});

test('normRepeat, rrule and repeatLabel only accept known frequencies and days', () => {
  assert.equal(core.normRepeat({ freq: 'YEARLY' }), null);
  assert.equal(core.normRepeat(null), null);
  assert.deepEqual(core.normRepeat({ freq: 'weekly', interval: 9, byday: ['MO', 'ZZ'] }), { freq: 'WEEKLY', interval: 4, byday: ['MO'] });
  assert.equal(core.rrule({ freq: 'nope' }, '2026-10-12'), '');
  assert.equal(core.repeatLabel({ freq: 'DAILY' }), 'daily');
  assert.equal(core.repeatLabel({ freq: 'WEEKLY' }, '2026-10-15'), 'weekly on Thu');
  assert.equal(core.repeatLabel({ freq: 'WEEKLY', interval: 2, byday: ['TH'] }), 'every 2 weeks on Thu');
  assert.equal(core.repeatLabel({ freq: 'WEEKLY', byday: ['MO', 'TU', 'WE', 'TH', 'FR'] }), 'weekdays');
  assert.equal(core.repeatLabel({ freq: 'MONTHLY', interval: 3 }), 'every 3 months');
});

test('gcalTemplateUrl carries a repeat as a recur rule', () => {
  const url = core.gcalTemplateUrl({ title: 'Lab', date: '2026-10-12', start: '10:00', end: '11:00', tz: 'Asia/Seoul', repeat: { freq: 'WEEKLY' } });
  assert.match(url, /&recur=RRULE%3AFREQ%3DWEEKLY%3BBYDAY%3DMO/);
  assert.doesNotMatch(core.gcalTemplateUrl({ title: 'Once', date: '2026-10-12', allDay: true }), /recur=/);
});

test('dueReminders announces each upcoming timed occurrence once', () => {
  const at = (id, min, extra = {}) => ({ id, start: new Date(NOW.getTime() + min * 60e3), end: new Date(NOW.getTime() + (min + 60) * 60e3), allDay: false, ...extra });
  const evs = [at('soon', 9), at('edge', 10), at('later', 11), at('started', -0.5), at('long-gone', -5), at('day', 5, { allDay: true })];
  const due = core.dueReminders(evs, NOW, 10, {});
  assert.deepEqual(due.map(d => d.event.id), ['soon', 'edge', 'started']);
  assert.deepEqual(due.map(d => d.minutes), [9, 10, 0]);
  const sent = { [due[0].key]: 1 };
  assert.deepEqual(core.dueReminders(evs, NOW, 10, sent).map(d => d.event.id), ['edge', 'started'], 'already-sent keys are skipped');
  // A repeating event's next occurrence has a new start, so it gets its own reminder.
  const nextWeek = at('soon', 9 + 7 * 1440);
  assert.notEqual(core.reminderKey(nextWeek), due[0].key);
  assert.deepEqual(core.dueReminders(evs, NOW, 15, {}).map(d => d.event.id), ['soon', 'edge', 'later', 'started']);
});

test('repeat words stay in the title when repeats are switched off, and declined events stay quiet', () => {
  const r = core.parseQuick('Water plants weekly fri', NOW, { repeats: false });
  assert.deepEqual([r.title, r.date, r.repeat], ['Water plants weekly', '2026-10-16', undefined]);
  const declined = core.normEvent({ id: 'x', calendarId: 'me', title: 'Skip', start: new Date(NOW.getTime() + 5 * 60e3).toISOString(), declined: true });
  assert.equal(declined.declined, true);
  assert.deepEqual(core.dueReminders([declined], NOW, 10, {}), []);
});

test('a weekly repeat starts on one of its days, wherever the date was typed', () => {
  const rep = t => { const r = core.parseQuick(t, NOW); return [r.title, r.date, r.repeat && core.rrule(r.repeat, r.date)]; };
  assert.deepEqual(rep('Lab fri every mon'), ['Lab', '2026-10-19', 'RRULE:FREQ=WEEKLY;BYDAY=MO'], 'a Friday date moves to the next Monday');
  assert.deepEqual(rep('Seminar every wed 2026-11-18 3pm'), ['Seminar', '2026-11-18', 'RRULE:FREQ=WEEKLY;BYDAY=WE'], 'a date after the repeat is still read');
  assert.deepEqual(rep('Lab every mon tomorrow'), ['Lab', '2026-10-12', 'RRULE:FREQ=WEEKLY;BYDAY=MO']);
  assert.deepEqual(rep('Gym mondays 7pm'), ['Gym', '2026-10-12', 'RRULE:FREQ=WEEKLY;BYDAY=MO'], 'a plural weekday repeats');
  assert.deepEqual(rep('Fix constructor bug tomorrow 3pm'), ['Fix constructor bug', '2026-10-12', undefined], 'object property names are just words');
  const task = core.parseQuick('Team sync tuesdays', NOW, { repeats: false });
  assert.deepEqual([task.title, task.date, task.repeat], ['Team sync', '2026-10-13', undefined], 'without repeats a plural weekday is a date again');
  assert.equal(core.alignToDays('2026-11-14', ['MO', 'TU', 'WE', 'TH', 'FR']), '2026-11-16');
  assert.equal(core.alignToDays('2026-11-16', ['MO']), '2026-11-16');
  assert.equal(core.alignToDays('', ['MO']), '');
});

// ------------------------------------------------------------- agendaDays
// Fixtures go through the real normEvent and unifyTasks, so a change in their
// shape shows up here too. The order of items within one day is not pinned.

const TWO_WEEKS = ['2026-10-11', '2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-17',
  '2026-10-18', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-24'];
const AFTER_TWO_WEEKS = '2026-10-25';
const agendaEvent = (title, start, end) => core.normEvent({ id: title, calendarId: 'me', title, start, end });
const hourOn = (title, date) => agendaEvent(title, date + 'T10:00:00', date + 'T11:00:00');
const agendaTask = (title, due, done = false) => core.unifyTasks([{ id: title, listId: 'L1', title, due, done }], [])[0];
const agendaDeadline = (title, date, done = false) => ({ key: 'desk:' + title, title, date, time: '', source: 'Desk', done });
const titlesOf = list => list.map(item => item.title).sort();
// { date: [titles] } for just the days with something in that column.
const filledDays = (days, column) => Object.fromEntries(days.filter(d => d[column].length).map(d => [d.date, titlesOf(d[column])]));

test('agendaDays returns one empty day per date when there is nothing to show', () => {
  const out = core.agendaDays({ today: '2026-10-11', days: 14, events: [], tasks: [], deadlines: [] });
  assert.deepEqual(out, TWO_WEEKS.map(date => ({ date, events: [], tasks: [], deadlines: [] })));
});

test('agendaDays treats missing lists as empty', () => {
  const empty = date => ({ date, events: [], tasks: [], deadlines: [] });
  assert.deepEqual(core.agendaDays({ today: '2026-10-11', days: 2 }), [empty('2026-10-11'), empty('2026-10-12')]);
  assert.deepEqual(core.agendaDays({ today: '2026-10-11', days: 1, events: undefined, tasks: undefined, deadlines: undefined }), [empty('2026-10-11')]);
  const [day] = core.agendaDays({ today: '2026-10-11', days: 1, tasks: [agendaTask('Solo', '2026-10-11')] });
  assert.deepEqual([titlesOf(day.tasks), day.events, day.deadlines], [['Solo'], [], []], 'one list given, the others still empty');
});

test('agendaDays returns exactly as many days as asked for', () => {
  const dates = days => core.agendaDays({ today: '2026-10-11', days }).map(d => d.date);
  assert.deepEqual(dates(0), []);
  assert.deepEqual(dates(1), ['2026-10-11']);
  assert.deepEqual(dates(7), TWO_WEEKS.slice(0, 7));
  assert.deepEqual(dates(14), TWO_WEEKS);
});

test('agendaDays gives consecutive dates across a month end and a year end', () => {
  const dates = today => core.agendaDays({ today, days: 14 }).map(d => d.date);
  assert.deepEqual(dates('2026-10-25'), ['2026-10-25', '2026-10-26', '2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30', '2026-10-31',
    '2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-07']);
  assert.deepEqual(dates('2026-12-25'), ['2026-12-25', '2026-12-26', '2026-12-27', '2026-12-28', '2026-12-29', '2026-12-30', '2026-12-31',
    '2027-01-01', '2027-01-02', '2027-01-03', '2027-01-04', '2027-01-05', '2027-01-06', '2027-01-07']);
});

test('agendaDays includes the last day of the window and nothing after it', () => {
  const out = core.agendaDays({
    today: '2026-10-11', days: 14,
    events: [hourOn('Last event', '2026-10-24'), hourOn('Too late event', AFTER_TWO_WEEKS)],
    tasks: [agendaTask('Last task', '2026-10-24'), agendaTask('Too late task', AFTER_TWO_WEEKS)],
    deadlines: [agendaDeadline('Last deadline', '2026-10-24'), agendaDeadline('Too late deadline', AFTER_TWO_WEEKS)],
  });
  assert.equal(out.length, 14);
  assert.equal(out[13].date, '2026-10-24');
  assert.deepEqual(filledDays(out, 'events'), { '2026-10-24': ['Last event'] });
  assert.deepEqual(filledDays(out, 'tasks'), { '2026-10-24': ['Last task'] });
  assert.deepEqual(filledDays(out, 'deadlines'), { '2026-10-24': ['Last deadline'] });
});

test('agendaDays shows items in the second week, past the old 7-day limit', () => {
  const secondWeek = TWO_WEEKS.slice(7);
  const expected = label => Object.fromEntries(secondWeek.map(d => [d, [label + ' ' + d]]));
  const out = core.agendaDays({
    today: '2026-10-11', days: 14,
    events: secondWeek.map(d => hourOn('Event ' + d, d)),
    tasks: secondWeek.map(d => agendaTask('Task ' + d, d)),
    deadlines: secondWeek.map(d => agendaDeadline('Deadline ' + d, d)),
  });
  assert.deepEqual(filledDays(out, 'events'), expected('Event'));
  assert.deepEqual(filledDays(out, 'tasks'), expected('Task'));
  assert.deepEqual(filledDays(out, 'deadlines'), expected('Deadline'));
});

test('agendaDays puts a multi-day event on every day it touches, with exclusive all-day ends', () => {
  const out = core.agendaDays({
    today: '2026-10-11', days: 5,
    events: [
      agendaEvent('Conference', '2026-10-12', '2026-10-14'),
      agendaEvent('Overnight', '2026-10-13T22:00:00', '2026-10-14T02:00:00'),
      agendaEvent('Ends at midnight', '2026-10-11T22:00:00', '2026-10-12T00:00:00'),
      agendaEvent('Began earlier', '2026-10-09T09:00:00', '2026-10-11T10:00:00'),
      agendaEvent('Runs off the end', '2026-10-15T09:00:00', '2026-10-20T09:00:00'),
    ],
  });
  assert.deepEqual(filledDays(out, 'events'), {
    '2026-10-11': ['Began earlier', 'Ends at midnight'],
    '2026-10-12': ['Conference'],
    '2026-10-13': ['Conference', 'Overnight'],
    '2026-10-14': ['Overnight'],
    '2026-10-15': ['Runs off the end'],
  });
});

test('agendaDays lists open tasks on their due date, and no undated, overdue or done ones', () => {
  const tasks = [
    agendaTask('Due today', '2026-10-11'),
    agendaTask('Due later', '2026-10-20'),
    agendaTask('Undated', ''),
    agendaTask('Overdue', '2026-10-09'),
    agendaTask('Finished', '2026-10-20', true),
    ...core.unifyTasks([], [{ id: 'd1', version: 1, data: { title: 'Desk task', due: '2026-10-13' } }]),
  ];
  const out = core.agendaDays({ today: '2026-10-11', days: 14, tasks });
  assert.deepEqual(filledDays(out, 'tasks'), { '2026-10-11': ['Due today'], '2026-10-13': ['Desk task'], '2026-10-20': ['Due later'] });
});

test('agendaDays lists open deadlines on their date and drops done ones', () => {
  const deadlines = core.collectDeadlines({
    today: '2026-10-11',
    entries: [
      { id: 'a', title: 'Open paper', deadline: '2026-10-20', status: 'inbox' },
      { id: 'b', title: 'Done paper', deadline: '2026-10-20', status: 'done' },
      { id: 'c', title: 'Missed paper', deadline: '2026-10-05', status: 'inbox' },
    ],
  });
  assert.equal(deadlines.length, 3, 'all three reach agendaDays');
  const out = core.agendaDays({ today: '2026-10-11', days: 14, deadlines });
  assert.deepEqual(filledDays(out, 'deadlines'), { '2026-10-20': ['Open paper'] });
});

test('agendaDays leaves its inputs unchanged', () => {
  const input = {
    today: '2026-10-11', days: 3,
    events: [hourOn('Later', '2026-10-12'), hourOn('Sooner', '2026-10-11')],
    tasks: [agendaTask('Task', '2026-10-12'), agendaTask('Done task', '2026-10-11', true)],
    deadlines: [agendaDeadline('Deadline', '2026-10-12'), agendaDeadline('Done deadline', '2026-10-11', true)],
  };
  const before = structuredClone(input);
  core.agendaDays(input);
  assert.deepEqual(input, before);
});

// ------------------------------------------------------------- taskBlocks

const blockTask = () => core.unifyTasks([{ id: 't1', listId: 'L1', title: 'Write intro', due: '', done: false }], [])[0];
const LINKED = { taskKey: 'g:L1:t1' };
// A block later today (NOW is 09:30), unlinked and with an unrelated title unless told otherwise.
const block = (id, h1, h2, extra = {}) => ev(h1, 0, h2, 0, { id, title: 'Some block', taskKey: '', editable: true, recurring: false, ...extra });
const blockIds = (task, events) => core.taskBlocks(task, events, NOW).map(e => e.id);

test('normEvent carries the task link of a time block', () => {
  assert.equal(core.normEvent({ id: 'b', calendarId: 'me', start: '2026-10-12T10:00:00', taskKey: 'g:L1:t1' }).taskKey, 'g:L1:t1');
});

test('normEvent gives an unlinked event an empty taskKey', () => {
  assert.equal(core.normEvent({ id: 'b', calendarId: 'me', start: '2026-10-12T10:00:00' }).taskKey, '');
});

test('taskBlocks finds events linked by taskKey, whatever their title', () => {
  const events = [block('renamed', 10, 11, { title: 'Renamed in Google Calendar', ...LINKED }), block('stranger', 12, 13, { title: 'Lunch' })];
  assert.deepEqual(blockIds(blockTask(), events), ['renamed']);
  const deskTask = core.unifyTasks([], [{ id: 'abc', version: 1, data: { title: 'Desk task' } }])[0];
  assert.deepEqual(blockIds(deskTask, [block('desk', 10, 11, { taskKey: 'd:abc' }), block('google', 12, 13, LINKED)]), ['desk']);
});

test('taskBlocks picks up unlinked events by title, ignoring case and surrounding whitespace', () => {
  const events = [
    block('exact', 10, 11, { title: 'Write intro' }),
    block('case', 11, 12, { title: 'WRITE INTRO' }),
    block('spaces', 12, 13, { title: '  write Intro\t' }),
  ];
  assert.deepEqual(blockIds(blockTask(), events), ['exact', 'case', 'spaces']);
  const paddedTask = { ...blockTask(), title: '  WRITE intro ' };
  assert.deepEqual(blockIds(paddedTask, [block('exact', 10, 11, { title: 'Write intro' })]), ['exact'], 'the task title is normalised too');
});

test('taskBlocks does not pick up unlinked events whose title only resembles the task', () => {
  const events = [
    block('same', 10, 11, { title: 'Write intro' }),
    block('longer', 11, 12, { title: 'Write intro draft' }),
    block('inner-space', 12, 13, { title: 'Write  intro' }),
  ];
  assert.deepEqual(blockIds(blockTask(), events), ['same']);
});

test('taskBlocks does not take a repeating or read-only event for a block on its title alone', () => {
  const events = [
    block('weekly', 10, 11, { title: 'Write intro', recurring: true }),
    block('shared', 12, 13, { title: 'Write intro', editable: false }),
  ];
  assert.deepEqual(blockIds(blockTask(), events), []);
});

test('taskBlocks keeps a linked event even when it repeats or is read-only', () => {
  const events = [block('daily', 10, 11, { ...LINKED, recurring: true }), block('shared', 12, 13, { ...LINKED, editable: false })];
  assert.deepEqual(blockIds(blockTask(), events), ['daily', 'shared']);
});

test('taskBlocks refuses an event linked to another task, even with an identical title', () => {
  const events = [block('mine', 10, 11, LINKED), block('theirs', 12, 13, { title: 'Write intro', taskKey: 'g:L1:t2' })];
  assert.deepEqual(blockIds(blockTask(), events), ['mine']);
});

test('taskBlocks never counts all-day events, linked or not', () => {
  const allDay = (id, extra) => ({ id, start: new Date(2026, 9, 12), end: new Date(2026, 9, 13), allDay: true, ...extra });
  const events = [
    allDay('by-key', { title: 'Anything', ...LINKED }),
    allDay('by-title', { title: 'Write intro', taskKey: '' }),
    block('timed', 10, 11, LINKED),
  ];
  assert.deepEqual(blockIds(blockTask(), events), ['timed']);
});

test('taskBlocks drops blocks that have ended and keeps the one in progress', () => {
  const events = [
    ev(8, 0, 9, 0, { id: 'ended', title: 'Write intro', ...LINKED }),
    ev(9, 0, 9, 30, { id: 'ends-now', title: 'Write intro', ...LINKED }),
    ev(9, 0, 10, 0, { id: 'running', title: 'Write intro', ...LINKED }),
    ev(9, 30, 10, 0, { id: 'starts-now', title: 'Write intro', ...LINKED }),
    ev(11, 0, 12, 0, { id: 'later', title: 'Write intro', ...LINKED }),
  ];
  assert.deepEqual(blockIds(blockTask(), events), ['running', 'starts-now', 'later']);
});

test('taskBlocks sorts by start across days, whatever the input order', () => {
  const tomorrow = { id: 'tomorrow', title: 'Some block', start: new Date(2026, 9, 12, 8, 0), end: new Date(2026, 9, 12, 9, 0), allDay: false, ...LINKED };
  const events = [tomorrow, block('afternoon', 14, 15, LINKED), block('morning', 10, 11, LINKED)];
  assert.deepEqual(blockIds(blockTask(), events), ['morning', 'afternoon', 'tomorrow']);
});

test('taskBlocks leaves the event list in its original order', () => {
  const events = [block('later', 14, 15, LINKED), block('earlier', 10, 11, LINKED)];
  core.taskBlocks(blockTask(), events, NOW);
  assert.deepEqual(events.map(e => e.id), ['later', 'earlier']);
});

test('taskBlocks returns an empty list when nothing belongs to the task', () => {
  assert.deepEqual(core.taskBlocks(blockTask(), [], NOW), []);
  assert.deepEqual(core.taskBlocks(blockTask(), [block('other', 10, 11, { title: 'Lunch' })], NOW), []);
});

test('taskBlocks reads the link off an event that came through normEvent', () => {
  const e = core.normEvent({ id: 'b', calendarId: 'me', title: 'Renamed', start: '2026-10-12T10:00:00', end: '2026-10-12T11:00:00', taskKey: 'g:L1:t1' });
  assert.deepEqual(blockIds(blockTask(), [e]), ['b@me']);
});

// ---- 2026-11-10 upgrade: palette, work-back, week review, links, queue ----

test('quick capture reads "review GaussVLA fri 3pm 1h" as a timed hour on Friday', () => {
  const p = core.parseQuick('review GaussVLA fri 3pm 1h', NOW);
  assert.deepEqual(p, { title: 'review GaussVLA', date: '2026-10-16', start: '15:00', end: '16:00', tags: [] });
});

test('paletteScore prefers substrings and word starts, and rejects non-matches', () => {
  assert.ok(core.paletteScore('gauss', 'Review GaussVLA') > core.paletteScore('gauss', 'Degauss the monitor'));
  assert.ok(core.paletteScore('mv tmr', 'Move to tomorrow: Draft rebuttal') > 0);
  assert.equal(core.paletteScore('xyz', 'Move to tomorrow'), 0);
  assert.equal(core.paletteScore('', 'anything'), 1);
  const items = [{ label: 'Today' }, { label: 'Board' }, { label: 'Move to tomorrow: Book room' }, { label: 'Block time: Book room' }];
  assert.deepEqual(core.paletteFilter(items, 'book', 10).map(x => x.label).sort(), ['Block time: Book room', 'Move to tomorrow: Book room']);
  assert.equal(core.paletteFilter(items, 'book', 1).length, 1);
  assert.deepEqual(core.paletteFilter(items, 'bo', 10).map(x => x.label)[0], 'Board');
});

test('workBack dates each step before the deadline and never in the past', () => {
  const plan = core.workBack('2026-11-30', core.WORKBACK_DEFAULT, '2026-11-10');
  assert.equal(plan.length, 6);
  assert.equal(plan[0].title, 'Outline and related work');
  assert.equal(plan[0].due, '2026-11-10', 'a step 28 days out already passed, so it lands on today');
  assert.equal(plan[0].clamped, true);
  assert.equal(plan[plan.length - 1].due, '2026-11-29');
  assert.deepEqual(plan.map(p => p.due), plan.map(p => p.due).slice().sort());
  assert.deepEqual(core.workBack('nonsense', core.WORKBACK_DEFAULT, '2026-11-10'), []);
  assert.deepEqual(core.normTemplate([{ title: '  ', before: 3 }, { title: 'Draft', before: '9.6' }, { title: 'Far', before: 9999 }]),
    [{ title: 'Draft', before: 10 }, { title: 'Far', before: 365 }]);
});

test('weekReview splits hours into meetings, task blocks and free time, and sorts tasks and entries', () => {
  const ev = (id, day, h1, h2, extra = {}) => core.normEvent({ id, calendarId: 'c', calendar: 'Lab', title: id,
    start: new Date(2026, 9, day, h1).toISOString(), end: new Date(2026, 9, day, h2).toISOString(), editable: true, ...extra });
  // Week of Mon 5 Oct to Sun 11 Oct 2026; today is Sunday 11 Oct.
  const events = [ev('meet', 6, 10, 11), ev('block', 7, 14, 16, { taskKey: 'g:L1:t1' }), ev('allday', 8, 0, 0, { allDay: true, start: '2026-10-08', end: '2026-10-09' })];
  const tasks = [
    { key: 'a', title: 'Done one', done: true, completed: '2026-10-07T10:00:00Z', due: '2026-10-07' },
    { key: 'b', title: 'Slipped', done: false, due: '2026-10-08' },
    { key: 'c', title: 'Later', done: false, due: '2026-10-20' },
    { key: 'd', title: 'Done last week', done: true, completed: '2026-10-01T10:00:00Z', due: '' }
  ];
  const entries = [{ id: 'e1', title: 'New', addedAt: '2026-10-06T01:00:00Z', updatedAt: '2026-10-06T01:00:00Z' },
    { id: 'e2', title: 'Old but edited', addedAt: '2026-09-01T01:00:00Z', updatedAt: '2026-10-09T01:00:00Z' }];
  const deadlines = [{ key: 'x', title: 'This week', date: '2026-10-09', done: false }, { key: 'y', title: 'Next week', date: '2026-10-14', done: false }];
  const rv = core.weekReview({ week: '2026-10-11', today: '2026-10-11', events, tasks, entries, deadlines, workday: { start: '08:00', end: '18:00' } });
  assert.equal(rv.from, '2026-10-05');
  assert.equal(rv.to, '2026-10-11');
  assert.equal(rv.meetingMinutes, 60);
  assert.equal(rv.blockMinutes, 120);
  assert.equal(rv.byCalendar.Lab, 180);
  assert.equal(rv.days.length, 7);
  assert.equal(rv.days[1].busy, 60);
  assert.equal(rv.days[1].free, 540);
  assert.equal(rv.freeMinutes, 7 * 600 - 180);
  assert.deepEqual(rv.tasksDone.map(t => t.key), ['a']);
  assert.deepEqual(rv.tasksSlipped.map(t => t.key), ['b']);
  assert.deepEqual(rv.entriesAdded.map(e => e.id), ['e1']);
  assert.deepEqual(rv.entriesChanged.map(e => e.id), ['e2']);
  assert.deepEqual(rv.deadlines.map(d => d.key), ['x']);
  assert.deepEqual(rv.deadlinesAhead.map(d => d.key), ['y']);
});

test('[[title]] links resolve to ids, survive renames, and are found as backlinks', () => {
  const entries = [{ id: 'e1', title: 'World model priors', thesis: '' }, { id: 'e2', title: 'Other', thesis: '' }];
  const html = core.linkRefs('<p>Builds on [[world model priors]] and [[Nothing here]] and <b>[[Other]]</b></p>', entries, 'e2');
  assert.equal(html, '<p>Builds on <span class="dk-ref" data-ref="e1">world model priors</span> and [[Nothing here]] and <b>[[Other]]</b></p>', 'unknown titles and self links stay as typed');
  assert.deepEqual(core.refsIn(html), ['e1']);
  assert.equal(core.linkRefs('<a href="https://x.y/[[q]]">[[Other]]</a>', entries, 'e1'), '<a href="https://x.y/[[q]]"><span class="dk-ref" data-ref="e2">Other</span></a>', 'never inside a tag');
  const renamed = [{ id: 'e1', title: 'Priors v2' }];
  assert.equal(core.refreshRefs(html, renamed), '<p>Builds on <span class="dk-ref" data-ref="e1">Priors v2</span> and [[Nothing here]] and <b>[[Other]]</b></p>');
  assert.equal(core.refreshRefs(html, []), '<p>Builds on <span class="dk-ref is-missing" data-ref="e1">world model priors</span> and [[Nothing here]] and <b>[[Other]]</b></p>');
  const all = [{ id: 'e1', title: 'World model priors', thesis: '', gap: '', experiment: '', risk: '' }, { id: 'e2', title: 'Other', thesis: html, gap: '', experiment: '', risk: '' }];
  assert.deepEqual(core.backlinks('e1', all).map(e => e.id), ['e2']);
  assert.deepEqual(core.backlinks('e2', all), []);
});

test('queueAdd folds writes to one document and keeps the first baseVersion', () => {
  let q = [];
  q = core.queueAdd(q, { action: 'put', at: 1, payload: { collection: 'entries', id: 'e1', data: { title: 'a' }, baseVersion: 3 } });
  q = core.queueAdd(q, { action: 'put', at: 2, payload: { collection: 'entries', id: 'e1', data: { title: 'b' }, baseVersion: 3 } });
  q = core.queueAdd(q, { action: 'setTask', at: 3, payload: { listId: 'L', id: 't', due: '2026-11-12' } });
  q = core.queueAdd(q, { action: 'setTask', at: 4, payload: { listId: 'L', id: 't', done: true } });
  q = core.queueAdd(q, { action: 'createTask', at: 5, payload: { title: 'x' } });
  q = core.queueAdd(q, { action: 'createTask', at: 6, payload: { title: 'y' } });
  assert.equal(q.length, 4);
  assert.deepEqual(q[0].payload, { collection: 'entries', id: 'e1', data: { title: 'b' }, baseVersion: 3 });
  assert.deepEqual(q[1].payload, { listId: 'L', id: 't', due: '2026-11-12', done: true });
  q = core.queueAdd(q, { action: 'delete', at: 7, payload: { collection: 'entries', id: 'e1' } });
  assert.equal(q.filter(i => i.payload.id === 'e1').length, 1);
  assert.equal(q[q.length - 1].action, 'delete');
  assert.equal(q[q.length - 1].payload.base, 3);
});

test('entryHaystack joins title, tags and the plain text of every field, lowercased', () => {
  const e = core.normaliseEntry('e1', { title: 'GaussVLA', tags: ['vla'], venue: 'BMVC', thesis: '<p>Spatial <b>tokens</b></p>' });
  const hay = core.entryHaystack(e, core.htmlToText);
  assert.ok(hay.indexOf('gaussvla') !== -1 && hay.indexOf('vla') !== -1 && hay.indexOf('spatial tokens') !== -1 && hay.indexOf('bmvc') !== -1);
  assert.equal(hay.indexOf('<b>'), -1);
});

test('normaliseEntry keeps private images by id and public ones by link, drops the rest', () => {
  const e = core.normaliseEntry('e1', { images: [{ id: 'abcdefghijkl', private: true }, { id: 'x', url: 'https://drive.google.com/thumbnail?id=x' }, { id: 'short', private: true }, { url: 'http://insecure' }] });
  assert.deepEqual(e.images.map(i => i.id || i.url), ['abcdefghijkl', 'x']);
});
