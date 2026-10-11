/**
 * Google Calendar + Google Tasks bridge for the private research desk.
 *
 * Runs inside your own Google account as an Apps Script web app, so it needs no
 * Google Cloud project, no OAuth client and no token that expires. Only the
 * desk Worker calls it, server to server, with the secret that setup() makes.
 *
 * Install (about five minutes, see ../README.md for screenshots-free steps):
 *   1. script.google.com > New project. Paste this file over Code.gs.
 *   2. Project Settings > tick "Show appsscript.json"; paste appsscript.json.
 *   3. Run setup() once and accept the Calendar and Tasks permissions. The log
 *      prints DESK_SECRET.
 *   4. Deploy > New deployment > Web app; Execute as: Me; Who has access: Anyone.
 *      Copy the /exec URL.
 *   5. In the Worker, set GOOGLE_BRIDGE_URL to that URL and GOOGLE_BRIDGE_SECRET
 *      to the secret.
 */

var MAX_EVENTS_PER_CALENDAR = 500;
var MAX_TASKS_PER_LIST = 300;

function setup() {
  var props = PropertiesService.getScriptProperties();
  var secret = props.getProperty('DESK_SECRET');
  if (!secret) {
    secret = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('DESK_SECRET', secret);
  }
  // Touch both services so the permission prompt covers them now.
  Calendar.CalendarList.list({ maxResults: 1 });
  Tasks.Tasklists.list({ maxResults: 1 });
  Logger.log('DESK_SECRET = ' + secret);
}

/** Makes a new secret. Paste it into the Worker afterwards. */
function rotateSecret() {
  PropertiesService.getScriptProperties().deleteProperty('DESK_SECRET');
  setup();
}

function doGet() {
  return json({ ok: true, service: 'desk-bridge' });
}

function doPost(e) {
  var req;
  try {
    req = JSON.parse((e && e.postData && e.postData.contents) || '{}');
  } catch (err) {
    return json({ ok: false, error: 'The request was not JSON.' });
  }
  var secret = PropertiesService.getScriptProperties().getProperty('DESK_SECRET');
  if (!secret || req.secret !== secret) return json({ ok: false, error: 'Wrong or missing bridge secret.' });
  try {
    if (req.action === 'agenda') return json(agenda(req));
    if (req.action === 'createEvent') return json(createEvent(req));
    if (req.action === 'createTask') return json(createTask(req));
    if (req.action === 'setTask') return json(setTask(req));
    return json({ ok: false, error: 'Unknown action.' });
  } catch (err) {
    return json({ ok: false, error: String((err && err.message) || err).slice(0, 300) });
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function clip(s, n) {
  s = String(s || '');
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function stripHtml(s) {
  return String(s || '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim();
}

// ------------------------------------------------------------------ read --

function agenda(req) {
  var timeMin = new Date(req.timeMin).toISOString();
  var timeMax = new Date(req.timeMax).toISOString();
  var warnings = [];
  var palette = {};
  try { palette = Calendar.Colors.get().event || {}; } catch (err) { warnings.push('colours: ' + err.message); }

  var calendars = (Calendar.CalendarList.list({ maxResults: 250 }).items || [])
    .filter(function (c) { return c.selected !== false && !c.hidden; });
  var events = [];
  calendars.forEach(function (c) {
    try {
      var token = null, n = 0;
      do {
        var page = Calendar.Events.list(c.id, {
          timeMin: timeMin, timeMax: timeMax, singleEvents: true, orderBy: 'startTime',
          maxResults: 250, pageToken: token || undefined
        });
        (page.items || []).forEach(function (ev) {
          if (ev.status === 'cancelled') return;
          var me = (ev.attendees || []).filter(function (a) { return a.self; })[0];
          if (me && me.responseStatus === 'declined') return;
          var video = ev.hangoutLink || '';
          if (!video && ev.conferenceData && ev.conferenceData.entryPoints) {
            ev.conferenceData.entryPoints.forEach(function (p) { if (!video && p.entryPointType === 'video') video = p.uri; });
          }
          events.push({
            id: ev.id,
            calendarId: c.id,
            calendar: c.summaryOverride || c.summary || '',
            color: (ev.colorId && palette[ev.colorId] && palette[ev.colorId].background) || c.backgroundColor || '',
            title: ev.summary || '(no title)',
            start: ev.start.dateTime || ev.start.date,
            end: (ev.end && (ev.end.dateTime || ev.end.date)) || '',
            allDay: !ev.start.dateTime,
            location: clip(ev.location, 200),
            description: clip(stripHtml(ev.description), 800),
            link: ev.htmlLink || '',
            video: video,
            attendees: (ev.attendees || []).length,
            type: ev.eventType || 'default'
          });
          n++;
        });
        token = page.nextPageToken;
      } while (token && n < MAX_EVENTS_PER_CALENDAR);
    } catch (err) {
      warnings.push((c.summary || c.id) + ': ' + err.message);
    }
  });

  var tasklists = Tasks.Tasklists.list({ maxResults: 100 }).items || [];
  var tasks = [];
  tasklists.forEach(function (list) {
    try {
      // Open tasks of any date, plus what was finished inside the window.
      collectTasks(list, { showCompleted: false }, tasks);
      collectTasks(list, { showCompleted: true, showHidden: true, completedMin: timeMin, completedMax: timeMax }, tasks, true);
    } catch (err) {
      warnings.push(list.title + ': ' + err.message);
    }
  });

  return {
    ok: true,
    calendars: calendars.map(function (c) {
      return { id: c.id, title: c.summaryOverride || c.summary || '', color: c.backgroundColor || '', primary: !!c.primary, writable: c.accessRole === 'owner' || c.accessRole === 'writer' };
    }),
    events: events,
    tasklists: tasklists.map(function (l) { return { id: l.id, title: l.title }; }),
    tasks: tasks,
    warnings: warnings
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
  } while (token && n < MAX_TASKS_PER_LIST);
}

function taskOut(list, t) {
  return {
    id: t.id,
    listId: list.id,
    list: list.title,
    title: t.title,
    notes: clip(t.notes, 600),
    due: t.due ? String(t.due).slice(0, 10) : '',
    done: t.status === 'completed',
    completed: t.completed || '',
    link: t.webViewLink || '',
    parent: t.parent || ''
  };
}

// ----------------------------------------------------------------- write --

function createEvent(req) {
  var tz = req.tz || Session.getScriptTimeZone();
  var date = String(req.date || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Give the event a date.');
  var resource = { summary: clip(req.title || 'Untitled', 250), description: clip(req.description, 4000), location: clip(req.location, 300) };
  if (req.allDay) {
    var next = new Date(date + 'T12:00:00Z');
    next.setUTCDate(next.getUTCDate() + 1);
    resource.start = { date: date };
    resource.end = { date: next.toISOString().slice(0, 10) };
  } else {
    var start = /^\d{2}:\d{2}$/.test(req.start || '') ? req.start : '09:00';
    var end = /^\d{2}:\d{2}$/.test(req.end || '') ? req.end : start;
    if (end <= start) end = Number(start.slice(0, 2)) >= 23 ? '23:59' : pad2(Number(start.slice(0, 2)) + 1) + start.slice(2);
    resource.start = { dateTime: date + 'T' + start + ':00', timeZone: tz };
    resource.end = { dateTime: date + 'T' + end + ':00', timeZone: tz };
  }
  var ev = Calendar.Events.insert(resource, req.calendarId || 'primary');
  return { ok: true, id: ev.id, link: ev.htmlLink || '' };
}

function pad2(n) { return (n < 10 ? '0' : '') + n; }

function createTask(req) {
  var body = { title: clip(req.title || 'Untitled', 1000), notes: clip(req.notes, 4000) };
  if (/^\d{4}-\d{2}-\d{2}$/.test(req.due || '')) body.due = req.due + 'T00:00:00.000Z';
  var listId = req.listId || '@default';
  var t = Tasks.Tasks.insert(body, listId);
  var list = { id: listId, title: '' };
  try { list = Tasks.Tasklists.get(listId); } catch (err) { /* keep the id */ }
  return { ok: true, task: taskOut(list, t) };
}

function setTask(req) {
  if (!req.listId || !req.id) throw new Error('Which task?');
  var patch = {};
  if (typeof req.done === 'boolean') {
    patch.status = req.done ? 'completed' : 'needsAction';
    if (!req.done) patch.completed = null;
  }
  if (typeof req.title === 'string' && req.title.trim()) patch.title = clip(req.title.trim(), 1000);
  if (req.due === '') patch.due = null;
  else if (/^\d{4}-\d{2}-\d{2}$/.test(req.due || '')) patch.due = req.due + 'T00:00:00.000Z';
  var t = Tasks.Tasks.patch(patch, req.listId, req.id);
  return { ok: true, task: taskOut({ id: req.listId, title: req.list || '' }, t) };
}
