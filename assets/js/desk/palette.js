/* ==========================================================================
   Research desk - command palette (Ctrl+K or Cmd+K). One box over views,
   entries, tasks, events and actions such as "move to tomorrow" or "block
   time"; anything typed can also be captured straight away as a task, event
   or idea with the same grammar as quick add. Uses Desk.app at call time.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var LIMIT = 14;
  var P = { el: null, shown: [], sel: 0 };

  function $(id) { return document.getElementById(id); }

  function build() {
    if (P.el) return;
    var d = document.createElement("dialog");
    d.id = "dk-palette";
    d.className = "dk-dialog dk-palette";
    d.setAttribute("aria-label", "Command palette");
    d.innerHTML =
      '<div class="dk-palette__in">' +
        '<label class="dk-palette__box"><i class="fas fa-terminal" aria-hidden="true"></i>' +
          '<input type="text" id="dk-pal-q" class="dk-palette__q" role="combobox" aria-expanded="true" aria-autocomplete="list" aria-controls="dk-pal-list" ' +
            'placeholder="Jump, act or capture: a view, an entry, a task, or “review GaussVLA fri 3pm 1h”" autocomplete="off" spellcheck="false"></label>' +
        '<ul id="dk-pal-list" class="dk-palette__list" role="listbox" aria-label="Matches"></ul>' +
        '<p class="dk-palette__hint"><kbd>↑</kbd><kbd>↓</kbd> choose · <kbd>Enter</kbd> run · <kbd>Esc</kbd> close · start with <kbd>+</kbd> to capture first</p>' +
      '</div>';
    document.body.appendChild(d);
    P.el = d;
    d.addEventListener("click", function (e) { if (e.target === d) d.close(); });
    d.addEventListener("close", function () { P.shown = []; });
    $("dk-pal-q").addEventListener("input", paint);
    $("dk-pal-q").addEventListener("keydown", onKey);
    $("dk-pal-list").addEventListener("click", function (e) {
      var li = e.target.closest("[data-pal]");
      if (li) run(+li.getAttribute("data-pal"));
    });
    $("dk-pal-list").addEventListener("mousemove", function (e) {
      var li = e.target.closest("[data-pal]");
      if (li && +li.getAttribute("data-pal") !== P.sel) { P.sel = +li.getAttribute("data-pal"); mark(); }
    });
  }

  /* ---- what can be found ------------------------------------------------ */
  function items(q) {
    var a = A(), S = a.S, t = a.today(), out = [];
    var view = function (id, label, icon, key) { out.push({ label: label, hint: "View · " + key, icon: icon, keywords: "view go " + id, boost: 8, run: function () { a.setView(id); } }); };
    view("today", "Today", "fa-sun", "1"); view("board", "Board", "fa-th-large", "2"); view("calendar", "Calendar", "fa-calendar-alt", "3");
    view("notion", "Research OS", "fa-database", "4"); view("review", "Week in review", "fa-chart-bar", "5");
    out.push({ label: "New entry", hint: "Action · N", icon: "fa-plus", keywords: "idea create board", boost: 6, run: function () { Desk.editor.open(null); } });
    out.push({ label: "Refresh from Google and Notion", hint: "Action · R", icon: "fa-sync-alt", keywords: "sync reload", boost: 2, run: function () { a.refresh(false); } });
    out.push({ label: "Settings and connections", hint: "Action", icon: "fa-cog", keywords: "preferences export import passcode", boost: 2, run: function () { a.openSettings(); } });
    out.push({ label: "Export JSON copy", hint: "Action", icon: "fa-download", keywords: "backup", run: function () { a.exportJson(); } });
    out.push({ label: "Calendar: today", hint: "Action", icon: "fa-calendar-day", keywords: "jump now", run: function () { if (Desk.calendar) { Desk.calendar.go(t, "day"); } a.setView("calendar"); } });
    var tomorrow = C.ymd(C.addDays(C.parseYmd(t), 1));
    a.allTasks().forEach(function (task) {
      if (task.done) return;
      var base = "task " + (task.list || "") + " " + (task.due || "undated");
      out.push({ label: task.title, hint: "Task" + (task.due ? " · due " + a.fmtDate(task.due, { weekday: "short", day: "numeric", month: "short" }) : ""), icon: "fa-check-square", keywords: base, run: function () { a.editTask(task.key); } });
      if (task.due !== tomorrow) out.push({ label: "Move to tomorrow: " + task.title, hint: "Task action", icon: "fa-arrow-right", keywords: "tmr postpone defer", quiet: true, run: function () { a.setTaskDue(task.key, tomorrow); } });
      if (task.due !== t) out.push({ label: "Move to today: " + task.title, hint: "Task action", icon: "fa-arrow-left", keywords: "pull now", quiet: true, run: function () { a.setTaskDue(task.key, t); } });
      out.push({ label: "Block time: " + task.title, hint: "Task action", icon: "fa-clock", keywords: "schedule plan slot", quiet: true, run: function () { a.blockTime(task.key); } });
      out.push({ label: "Mark done: " + task.title, hint: "Task action", icon: "fa-check", keywords: "complete finish", quiet: true, run: function () { a.toggleTask(task.key, true); } });
    });
    S.entries.forEach(function (r) {
      var e = r.e;
      out.push({ label: e.title || "Untitled", hint: "Entry · " + C.byId(C.STATUSES, e.status).label + " · " + C.byId(C.AXES, e.axis).label, icon: "fa-lightbulb",
        keywords: "entry " + e.kind + " " + e.tags.join(" ") + " " + e.venue, run: function () { Desk.editor.open(e.id); } });
      if (C.isYmd(e.deadline) && Desk.workback) out.push({ label: "Work back from: " + e.title, hint: "Deadline action · " + e.deadline, icon: "fa-flag-checkered", keywords: "plan tasks deadline", quiet: true,
        run: function () { Desk.workback.open({ title: e.title, date: e.deadline, source: "Desk" }); } });
    });
    var now = new Date();
    a.events().filter(function (e) { return e.end > now && C.dayDiff(t, C.ymd(e.start)) <= 7; }).slice(0, 60).forEach(function (e) {
      out.push({ label: e.title, hint: "Event · " + a.fmtDate(C.ymd(e.start), { weekday: "short", day: "numeric", month: "short" }) + (e.allDay ? "" : " " + a.hhmm(e.start)), icon: "fa-calendar", keywords: "event " + e.calendar, run: function () { a.openEvent(e.id); } });
    });
    a.deadlines().filter(function (d) { return !d.done && d.days >= 0; }).slice(0, 40).forEach(function (d) {
      if (d.entryId || !Desk.workback) return;
      out.push({ label: "Work back from: " + d.title, hint: "Deadline action · " + d.date, icon: "fa-flag-checkered", keywords: "plan tasks " + d.source, quiet: true,
        run: function () { Desk.workback.open({ title: d.title, date: d.date, source: d.source }); } });
    });
    return out;
  }

  // Capture rows for whatever is typed, after the matches unless "+" leads.
  function captureRows(q) {
    var a = A(), raw = q.replace(/^\+\s*/, "").trim();
    if (!raw) return [];
    var first = q.charAt(0) === "+", preview = function (mode) {
      var p = C.parseQuick(raw, null, { repeats: mode === "event" }), bits = [];
      if (p.date) bits.push(a.fmtDate(p.date, { weekday: "short", day: "numeric", month: "short" }));
      if (p.start) bits.push(p.start + (p.end ? "–" + p.end : ""));
      if (p.repeat) bits.push(C.repeatLabel(p.repeat, p.date || a.today()));
      return (p.title || raw) + (bits.length ? " · " + bits.join(" · ") : "");
    };
    var mk = function (mode, label, icon) {
      return { label: label + ": " + preview(mode), hint: "Capture", icon: icon, capture: true, boost: first ? 1000 : -1000, run: function () { return a.capture(raw, mode); } };
    };
    return [mk("task", "Add task", "fa-check-square"), mk("event", "Add event", "fa-calendar-plus"), mk("idea", "Add idea", "fa-lightbulb")];
  }

  /* ---- drawing ------------------------------------------------------------ */
  function paint() {
    var a = A(), esc = a.esc, q = $("dk-pal-q").value, bare = q.replace(/^\+\s*/, "");
    var all = items(q).filter(function (it) { return !it.quiet || bare.trim().length >= 2; });
    var matched = C.paletteFilter(all, bare, LIMIT);
    var caps = captureRows(q);
    P.shown = q.charAt(0) === "+" ? caps.concat(matched.slice(0, LIMIT - 3)) : matched.concat(caps);
    P.sel = 0;
    $("dk-pal-list").innerHTML = P.shown.length ? P.shown.map(function (it, i) {
      return '<li id="dk-pal-' + i + '" class="dk-palette__item' + (it.capture ? " is-capture" : "") + '" role="option" data-pal="' + i + '" aria-selected="' + (i === P.sel) + '">' +
        '<i class="fas ' + it.icon + '" aria-hidden="true"></i><span class="dk-palette__label">' + esc(it.label) + '</span><span class="dk-palette__hint">' + esc(it.hint || "") + '</span></li>';
    }).join("") : '<li class="dk-palette__empty" role="option" aria-selected="false">Nothing matches. Start with + to capture it as a task, event or idea.</li>';
    mark();
  }
  function mark() {
    var list = $("dk-pal-list").children;
    for (var i = 0; i < list.length; i++) list[i].setAttribute("aria-selected", String(i === P.sel));
    $("dk-pal-q").setAttribute("aria-activedescendant", P.shown.length ? "dk-pal-" + P.sel : "");
    var on = list[P.sel];
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
  }
  function onKey(e) {
    var n = P.shown.length;
    if (e.key === "ArrowDown") { if (n) { P.sel = (P.sel + 1) % n; mark(); } e.preventDefault(); }
    else if (e.key === "ArrowUp") { if (n) { P.sel = (P.sel - 1 + n) % n; mark(); } e.preventDefault(); }
    else if (e.key === "Home") { P.sel = 0; mark(); e.preventDefault(); }
    else if (e.key === "End") { P.sel = Math.max(0, n - 1); mark(); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); if (n) run(P.sel); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  }
  function run(i) {
    var it = P.shown[i];
    if (!it) return;
    close();
    // After the dialog closes, so a dialog the action opens is not closed with it.
    setTimeout(function () { it.run(); }, 0);
  }

  function open(prefill) {
    build();
    $("dk-pal-q").value = prefill || "";
    if (!P.el.open) P.el.showModal();
    paint();
    $("dk-pal-q").focus();
    $("dk-pal-q").select();
  }
  function close() { if (P.el && P.el.open) P.el.close(); }
  function toggle() { if (P.el && P.el.open) close(); else open(); }

  // Ctrl+K / Cmd+K anywhere on the desk, inputs included. Not when the
  // palette itself has focus (its own keys apply), nor before the desk mounted.
  document.addEventListener("keydown", function (e) {
    if (!(e.ctrlKey || e.metaKey) || e.altKey || String(e.key).toLowerCase() !== "k") return;
    if (!Desk.app || !Desk.app.S.mounted) return;
    e.preventDefault();
    toggle();
  }, true);

  Desk.palette = { open: open, close: close, toggle: toggle };
})();
