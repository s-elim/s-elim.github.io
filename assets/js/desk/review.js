/* ==========================================================================
   Research desk - the week in review (view 5). Hours in meetings and in
   blocks tied to tasks, free hours by day, tasks finished and slipped,
   entries added or changed, deadlines met and ahead. Computed on the page
   from the sync already loaded (core.js weekReview), so it needs no new
   backend. Uses Desk.app at call time.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var R = { anchor: "" }; // a day inside the shown week; "" means this week

  function hours(min) { return min < 60 ? min + " min" : (Math.round(min / 6) / 10) + " h"; }

  function review() {
    var a = A(), S = a.S, t = a.today();
    return C.weekReview({
      week: R.anchor || t, today: t, events: a.events(), tasks: a.allTasks(),
      entries: S.entries.map(function (r) { return r.e; }), deadlines: a.deadlines(), workday: S.ui.workday
    });
  }

  function tile(k, v, m) {
    var esc = A().esc;
    return '<div class="dk-rv__tile"><span class="dk-rv__k">' + esc(k) + '</span><b class="dk-rv__v">' + esc(v) + '</b><span class="dk-rv__m">' + esc(m) + '</span></div>';
  }

  function dayBars(rv) {
    var a = A(), esc = a.esc, max = Math.max(1, rv.days.reduce(function (n, d) { return Math.max(n, d.busy + d.free); }, 0));
    return '<ol class="dk-rv__days" aria-label="Busy and free hours by day">' + rv.days.map(function (d) {
      var busyPct = Math.round(d.busy / max * 100), freePct = Math.round(d.free / max * 100);
      return '<li class="dk-rv__day' + (d.today ? " is-today" : "") + (d.past ? " is-past" : "") + '">' +
        '<button type="button" class="dk-rv__dayb" data-calday="' + d.date + '" aria-label="' + esc(a.fmtDate(d.date, { weekday: "long", day: "numeric", month: "long" })) + ': ' + esc(hours(d.busy)) + ' busy, ' + esc(hours(d.free)) + ' free">' +
          '<span class="dk-rv__dow">' + esc(a.fmtDate(d.date, { weekday: "short" })) + ' <em>' + esc(String(C.parseYmd(d.date).getDate())) + '</em></span>' +
          '<span class="dk-rv__bar" aria-hidden="true"><i class="is-busy" style="width:' + busyPct + '%"></i><i class="is-free" style="width:' + freePct + '%"></i></span>' +
          '<span class="dk-rv__num">' + esc(hours(d.busy)) + ' busy · ' + esc(hours(d.free)) + ' free</span>' +
        '</button></li>';
    }).join("") + '</ol>';
  }

  function taskList(list, t, opts) {
    var a = A(), esc = a.esc;
    if (!list.length) return '<p class="dk-quiet">' + esc(opts.empty) + '</p>';
    return '<ul class="dk-rv__list">' + list.slice(0, 40).map(function (x) {
      var when = opts.completed ? String(x.completed || "").slice(0, 10) : x.due;
      return '<li><button type="button" class="dk-rv__item" data-edittask="' + esc(x.key) + '">' + (Desk.marks ? Desk.marks.taskTitle(x) : esc(x.title)) + '</button>' +
        '<span class="dk-rv__when">' + esc(C.isYmd(when) ? a.fmtDate(when, { weekday: "short", day: "numeric" }) : "") + '</span>' +
        (opts.pull ? '<button type="button" class="dk-task__act" data-taskdue="' + esc(x.key) + '" data-due="' + t + '">Today</button>' : "") + '</li>';
    }).join("") + (list.length > 40 ? '<li class="dk-quiet">+' + (list.length - 40) + ' more</li>' : "") + '</ul>';
  }
  function entryList(list, empty) {
    var a = A(), esc = a.esc;
    if (!list.length) return '<p class="dk-quiet">' + esc(empty) + '</p>';
    return '<ul class="dk-rv__list">' + list.slice(0, 40).map(function (e) {
      return '<li><button type="button" class="dk-rv__item" data-entry="' + esc(e.id) + '">' + esc(e.title || "Untitled") + '</button>' +
        '<span class="dk-rv__when">' + esc(C.byId(C.STATUSES, e.status).label) + '</span></li>';
    }).join("") + '</ul>';
  }
  function deadlineList(list, empty) {
    var a = A(), esc = a.esc;
    if (!list.length) return '<p class="dk-quiet">' + esc(empty) + '</p>';
    return '<ul class="dk-rv__list">' + list.slice(0, 40).map(function (d) {
      var attr = d.entryId ? 'data-entry="' + esc(d.entryId) + '"' : (a.safeUrl(d.url) ? 'data-href="' + esc(a.safeUrl(d.url)) + '"' : "");
      return '<li><button type="button" class="dk-rv__item" ' + attr + '><i class="dk-swatch" style="--c:' + esc(d.color) + '"></i> ' + esc(d.title) + (d.done ? ' <span class="dk-st">done</span>' : "") + '</button>' +
        '<span class="dk-rv__when">' + esc(a.fmtDate(d.date, { weekday: "short", day: "numeric" })) + '</span>' +
        (Desk.workback && !d.done && d.days >= 0 ? '<button type="button" class="dk-task__act" data-workback="' + esc(d.key) + '">Work back</button>' : "") + '</li>';
    }).join("") + '</ul>';
  }

  // The same numbers as text, for a lab notebook or a weekly message.
  function asText(rv) {
    var a = A(), lines = ["Week " + rv.from + " to " + rv.to];
    lines.push("Meetings " + hours(rv.meetingMinutes) + " · blocks on tasks " + hours(rv.blockMinutes) + " · free " + hours(rv.freeMinutes));
    lines.push("", "Done (" + rv.tasksDone.length + ")"); rv.tasksDone.forEach(function (x) { lines.push("- " + x.title); });
    lines.push("", "Slipped (" + rv.tasksSlipped.length + ")"); rv.tasksSlipped.forEach(function (x) { lines.push("- " + x.title + " (due " + x.due + ")"); });
    lines.push("", "Entries added (" + rv.entriesAdded.length + ")"); rv.entriesAdded.forEach(function (e) { lines.push("- " + (e.title || "Untitled")); });
    lines.push("", "Entries changed (" + rv.entriesChanged.length + ")"); rv.entriesChanged.forEach(function (e) { lines.push("- " + (e.title || "Untitled")); });
    lines.push("", "Deadlines this week (" + rv.deadlines.length + ")"); rv.deadlines.forEach(function (d) { lines.push("- " + d.title + " " + d.date + (d.done ? " (done)" : "")); });
    lines.push("", "Deadlines next week (" + rv.deadlinesAhead.length + ")"); rv.deadlinesAhead.forEach(function (d) { lines.push("- " + d.title + " " + d.date); });
    return lines.join("\n");
  }

  function render(body) {
    var a = A(), esc = a.esc, t = a.today(), rv = review();
    var cals = Object.keys(rv.byCalendar).sort(function (x, y) { return rv.byCalendar[y] - rv.byCalendar[x]; });
    var html = '<div class="dk-rv">' +
      '<div class="dk-tools"><div class="dk-calnav">' +
        '<button type="button" class="dk-icon" data-rvshift="-1" aria-label="Previous week"><i class="fas fa-chevron-left" aria-hidden="true"></i></button>' +
        '<button type="button" class="dk-btn" data-rvshift="0">This week</button>' +
        '<button type="button" class="dk-icon" data-rvshift="1" aria-label="Next week"><i class="fas fa-chevron-right" aria-hidden="true"></i></button></div>' +
        '<h3 class="dk-period">' + esc(a.fmtDate(rv.from, { day: "numeric", month: "short" })) + ' – ' + esc(a.fmtDate(rv.to, { day: "numeric", month: "short", year: "numeric" })) + '</h3>' +
        '<button type="button" class="dk-btn dk-btn--quiet" data-rvcopy="1" title="Copy this review as plain text"><i class="fas fa-copy" aria-hidden="true"></i> Copy as text</button>' +
      '</div>' +
      (a.googleReady() ? "" : '<p class="dk-hint">Google Calendar is not connected, so hours show only what the desk knows.</p>') +
      '<div class="dk-rv__tiles">' +
        tile("In meetings", hours(rv.meetingMinutes), cals.length ? cals.slice(0, 3).map(function (c) { return c + " " + hours(rv.byCalendar[c]); }).join(" · ") : "no timed events") +
        tile("Blocked for tasks", hours(rv.blockMinutes), rv.blockMinutes ? "time tied to a task" : "use Block time on a task") +
        tile("Free in the day", hours(rv.freeMinutes), "between " + esc(a.S.ui.workday.start) + " and " + esc(a.S.ui.workday.end)) +
        tile("Tasks finished", String(rv.tasksDone.length), rv.tasksSlipped.length ? rv.tasksSlipped.length + " slipped" : "none slipped") +
      '</div>' +
      dayBars(rv) +
      '<div class="dk-rv__grid">' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-check" aria-hidden="true"></i> Finished</h3></header>' + taskList(rv.tasksDone, t, { completed: true, empty: "No task was finished this week." }) + '</section>' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-history" aria-hidden="true"></i> Slipped</h3></header>' + taskList(rv.tasksSlipped, t, { pull: true, empty: "Nothing slipped." }) + '</section>' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-lightbulb" aria-hidden="true"></i> Entries added</h3></header>' + entryList(rv.entriesAdded, "No new entries.") + '</section>' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-pen" aria-hidden="true"></i> Entries changed</h3></header>' + entryList(rv.entriesChanged, "No existing entry changed.") + '</section>' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-flag-checkered" aria-hidden="true"></i> Deadlines this week</h3></header>' + deadlineList(rv.deadlines, "None this week.") + '</section>' +
        '<section class="dk-panel"><header class="dk-panel__head"><h3><i class="fas fa-flag" aria-hidden="true"></i> Deadlines next week</h3></header>' + deadlineList(rv.deadlinesAhead, "Nothing due next week.") + '</section>' +
      '</div></div>';
    body.innerHTML = html;
    if (!body.__dkRv) {
      body.__dkRv = true;
      body.addEventListener("click", onClick);
    }
  }

  function onClick(e) {
    var a = A();
    if (a.S.ui.view !== "review") return;
    var t = e.target.closest("[data-rvshift], [data-rvcopy], [data-calday], [data-href]");
    if (!t) return;
    var v;
    if ((v = t.getAttribute("data-rvshift")) !== null) {
      var base = C.parseYmd(R.anchor || a.today());
      R.anchor = +v === 0 ? "" : C.ymd(C.addDays(C.startOfWeek(base), 7 * (+v)));
      a.render();
    } else if (t.hasAttribute("data-rvcopy")) {
      var text = asText(review());
      var done = function () { a.toast("Copied the week as text."); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { window.prompt("Copy this text", text); });
      else window.prompt("Copy this text", text);
    } else if ((v = t.getAttribute("data-calday"))) {
      if (Desk.calendar) Desk.calendar.go(v, "day");
      a.setView("calendar");
    } else if ((v = t.getAttribute("data-href"))) {
      window.open(v, "_blank", "noopener");
    }
  }

  Desk.review = { render: render };
})();
