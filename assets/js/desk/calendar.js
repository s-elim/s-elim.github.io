/* ==========================================================================
   Research desk - Calendar view. Month, week and day ranges over three
   layers: Google events, tasks (Google or desk) and deadlines (desk entries,
   Notion rows, watched conferences). Ranges outside the default sync window
   are fetched on demand.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var DAY_START = 6, DAY_END = 24, HOUR_PX = 46;
  var UI_KEY = "desk.cal.v1";

  // A phone opens on the day view until a range is picked; a week of columns is
  // too narrow to read there.
  var narrow = window.matchMedia && window.matchMedia("(max-width: 560px)").matches;
  var cal = { mode: narrow ? "day" : "week", anchor: new Date(), layers: { events: true, tasks: true, deadlines: true }, extra: null, loading: false, err: "" };
  try {
    var saved = JSON.parse(localStorage.getItem(UI_KEY) || "null");
    if (saved) { cal.mode = saved.mode || cal.mode; cal.layers = Object.assign(cal.layers, saved.layers || {}); }
  } catch (e) {}
  function remember() { try { localStorage.setItem(UI_KEY, JSON.stringify({ mode: cal.mode, layers: cal.layers })); } catch (e) {} }

  function range() {
    var a = cal.anchor, s, e;
    if (cal.mode === "month") { s = C.startOfWeek(new Date(a.getFullYear(), a.getMonth(), 1)); e = C.addDays(s, 42); }
    else if (cal.mode === "week") { s = C.startOfWeek(a); e = C.addDays(s, 7); }
    else { s = new Date(a.getFullYear(), a.getMonth(), a.getDate()); e = C.addDays(s, 1); }
    return { start: s, end: e, from: C.ymd(s), to: C.ymd(C.addDays(e, -1)) };
  }
  function covers(sync, r) { return !!(sync && sync.range && sync.range.from <= r.from && sync.range.to >= r.to); }

  // The sync payload that covers the visible range, fetching one when needed.
  function dataFor(r) {
    var S = A().S;
    if (covers(S.sync, r)) return S.sync;
    if (covers(cal.extra, r)) return cal.extra;
    if (!cal.loading) {
      cal.loading = true; cal.err = "";
      var from = C.addDays(r.start, -7), to = C.addDays(r.end, 7);
      A().fetchSync({ from: C.ymd(from), to: C.ymd(to), timeMin: from.toISOString(), timeMax: to.toISOString() }).then(function (res) {
        cal.extra = res;
      }, function (err) { cal.err = err.message; }).then(function () { cal.loading = false; A().render(); });
    }
    return null;
  }

  function label() {
    var a = cal.anchor, r = range();
    if (cal.mode === "month") return a.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    if (cal.mode === "day") return a.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    var last = C.addDays(r.start, 6);
    return r.start.toLocaleDateString(undefined, { day: "numeric", month: "short" }) + " – " + last.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  /* ---- items in range ------------------------------------------------- */
  function itemsFor(r, data) {
    var a = A(), S = a.S, out = { events: [], tasks: [], deadlines: [] };
    if (data && cal.layers.events) {
      out.events = ((data.google && data.google.events) || []).map(C.normEvent).filter(function (e) { return e && e.start < r.end && e.end > r.start; });
    }
    if (cal.layers.tasks) {
      var g = data && data.google && data.google.tasks;
      out.tasks = C.unifyTasks(g || (S.sync && S.sync.google && S.sync.google.tasks), S.deskTasks).filter(function (t) { return t.due && t.due >= r.from && t.due <= r.to; });
    }
    if (cal.layers.deadlines) {
      S.entries.forEach(function (rec) {
        var e = rec.e;
        if (C.isYmd(e.deadline) && e.deadline >= r.from && e.deadline <= r.to) {
          out.deadlines.push({ title: e.title, date: e.deadline, color: C.byId(C.AXES, e.axis).color, entryId: e.id, done: e.status === "done", source: "Desk" });
        }
      });
      var src = (data && data.notion && data.notion.sources) || [];
      src.forEach(function (s) {
        (s.rows || []).forEach(function (row) {
          var d = String(row.date || "").slice(0, 10);
          if (C.isYmd(d) && d >= r.from && d <= r.to) out.deadlines.push({ title: row.title, date: d, color: C.SOURCE_COLORS[s.label] || "#475569", url: row.url, done: row.done, source: s.label });
        });
      });
      C.conferenceDeadlines(S.conferences, S.prefs.data.watched, r.from, r.to).forEach(function (d) {
        d.color = C.SOURCE_COLORS.Conference;
        out.deadlines.push(d);
      });
    }
    return out;
  }
  function onDay(items, key) {
    var list = [];
    items.events.forEach(function (e) { if (C.eventOnDay(e, key)) list.push({ k: "event", x: e }); });
    items.deadlines.forEach(function (d) { if (d.date === key) list.push({ k: "deadline", x: d }); });
    items.tasks.forEach(function (t) { if (t.due === key) list.push({ k: "task", x: t }); });
    list.sort(function (p, q) {
      var rank = function (it) { return it.k === "deadline" ? 0 : it.k === "event" && it.x.allDay ? 1 : it.k === "task" ? 3 : 2; };
      return rank(p) - rank(q) || (p.k === "event" && q.k === "event" ? p.x.start - q.x.start : 0);
    });
    return list;
  }

  function chip(it) {
    var a = A(), esc = a.esc, x = it.x;
    if (it.k === "event") {
      return '<button type="button" class="dk-chipev" style="--c:' + esc(x.color) + '" data-event="' + esc(x.id) + '" title="' + esc(x.title) + '">' +
        (x.allDay ? "" : '<span class="dk-chipev__t">' + a.hhmm(x.start) + '</span>') + esc(x.title) + '</button>';
    }
    if (it.k === "deadline") {
      var attr = x.entryId ? 'data-entry="' + esc(x.entryId) + '"' : a.safeUrl(x.url) ? 'data-href="' + esc(a.safeUrl(x.url)) + '"' : "";
      return '<button type="button" class="dk-chipev dk-chipev--dl' + (x.done ? " is-done" : "") + '" style="--c:' + esc(x.color) + '" ' + attr + ' title="' + esc(x.source + ": " + x.title) + '">' +
        '<i class="fas fa-flag" aria-hidden="true"></i> ' + esc(x.title) + '</button>';
    }
    return '<button type="button" class="dk-chipev dk-chipev--task' + (x.done ? " is-done" : "") + '" data-task="' + esc(x.key) + '" title="' + (x.done ? "Mark as not done" : "Mark as done") + ': ' + esc(x.title) + '">' +
      '<span class="dk-tick" aria-hidden="true"></span>' + (x.time ? '<span class="dk-chipev__t">' + esc(x.time) + '</span>' : "") + esc(x.title) + '</button>';
  }

  /* ---- views ---------------------------------------------------------- */
  function monthHtml(r, items) {
    var t = A().today(), month = cal.anchor.getMonth(), cells = "";
    for (var i = 0; i < 42; i++) {
      var d = C.addDays(r.start, i), key = C.ymd(d), list = onDay(items, key);
      cells += '<div class="dk-mcell' + (d.getMonth() !== month ? " is-out" : "") + (key === t ? " is-today" : "") + '" data-day="' + key + '">' +
        '<span class="dk-mcell__n">' + d.getDate() + '</span>' + list.slice(0, 4).map(chip).join("") +
        (list.length > 4 ? '<span class="dk-more">+' + (list.length - 4) + ' more</span>' : "") + '</div>';
    }
    var dows = [];
    for (var j = 0; j < 7; j++) dows.push('<span>' + C.addDays(r.start, j).toLocaleDateString(undefined, { weekday: "short" }) + '</span>');
    return '<div class="dk-cal dk-cal--month"><div class="dk-dow">' + dows.join("") + '</div><div class="dk-month">' + cells + '</div></div>';
  }

  function packColumns(list) {
    var sorted = list.slice().sort(function (p, q) { return p.start - q.start || p.end - q.end; });
    var cols = [], out = [];
    sorted.forEach(function (e) {
      for (var c = 0; c < cols.length; c++) {
        if (cols[c] <= e.start.getTime()) { cols[c] = e.end.getTime(); out.push({ e: e, col: c }); return; }
      }
      cols.push(e.end.getTime());
      out.push({ e: e, col: cols.length - 1 });
    });
    return { placed: out, n: Math.max(1, cols.length) };
  }

  function gridHtml(days, items) {
    var a = A(), esc = a.esc, t = a.today(), i;
    var gtc = "repeat(" + days.length + ",minmax(0,1fr))";
    var gutter = "";
    for (i = DAY_START; i < DAY_END; i++) gutter += '<div>' + C.pad2(i) + ':00</div>';
    var lines = "";
    for (i = 0; i <= DAY_END - DAY_START; i++) lines += '<div class="dk-hline" style="top:' + i * HOUR_PX + 'px"></div>';
    var head = days.map(function (d) {
      var key = C.ymd(d);
      return '<button type="button" class="dk-whead' + (key === t ? " is-today" : "") + '" data-dayview="' + key + '"><span>' + d.toLocaleDateString(undefined, { weekday: "short" }) + '</span><b>' + d.getDate() + '</b></button>';
    }).join("");
    var allday = days.map(function (d) {
      var key = C.ymd(d);
      return '<div class="dk-allday__c">' + onDay(items, key).filter(function (it) { return !(it.k === "event" && !it.x.allDay); }).map(chip).join("") + '</div>';
    }).join("");
    var cols = days.map(function (d) {
      var key = C.ymd(d), d0 = C.parseYmd(key).getTime() + DAY_START * 36e5, span = (DAY_END - DAY_START) * 36e5;
      var timed = items.events.filter(function (e) { return !e.allDay && C.eventOnDay(e, key); });
      var lay = packColumns(timed);
      var evs = lay.placed.map(function (p) {
        var e = p.e, top = Math.max(0, (e.start.getTime() - d0) / span), bot = Math.min(1, (e.end.getTime() - d0) / span);
        if (bot <= 0 || top >= 1) return "";
        var h = Math.max(0.03, bot - top), w = 100 / lay.n, move = movable(e);
        return '<button type="button" class="dk-tev' + (move ? " is-movable" : "") + '" style="--c:' + esc(e.color) + ';top:' + (top * 100).toFixed(2) + '%;height:' + (h * 100).toFixed(2) +
          '%;left:calc(' + (p.col * w).toFixed(2) + '% + 2px);width:calc(' + w.toFixed(2) + '% - 4px)" data-event="' + esc(e.id) + '">' +
          '<b>' + esc(e.title) + '</b><span>' + a.hhmm(e.start) + '–' + a.hhmm(e.end) + '</span>' +
          (move ? '<i class="dk-tev__grip" aria-hidden="true"></i>' : "") + '</button>';
      }).join("");
      return '<div class="dk-dcol" data-slot="' + key + '">' + lines + (key === t ? '<div class="dk-nowline" data-nowline></div>' : "") + evs + '</div>';
    }).join("");
    return '<div class="dk-cal dk-cal--grid' + (days.length > 1 ? " dk-cal--week" : "") + '">' +
      '<div class="dk-whead-row" style="grid-template-columns:54px ' + gtc + '"><span></span>' + head + '</div>' +
      '<div class="dk-allday" style="grid-template-columns:54px ' + gtc + '"><span class="dk-allday__l">all day</span>' + allday + '</div>' +
      '<div class="dk-tgrid" id="dk-tgrid"><div class="dk-gutter">' + gutter + '</div>' +
      '<div class="dk-dcols" style="grid-template-columns:' + gtc + ';height:' + (DAY_END - DAY_START) * HOUR_PX + 'px">' + cols + '</div></div></div>';
  }

  function positionNow(body) {
    var el = body.querySelector("[data-nowline]");
    if (!el) return;
    var n = new Date(), mins = n.getHours() * 60 + n.getMinutes() - DAY_START * 60, total = (DAY_END - DAY_START) * 60;
    el.hidden = mins < 0 || mins > total;
    el.style.top = (mins / total) * (DAY_END - DAY_START) * HOUR_PX + "px";
  }

  function render(body) {
    // A redraw replaces the grid, so a drag in progress would end up holding
    // detached nodes and measure nonsense; drop it instead.
    if (drag) endDrag();
    var a = A(), esc = a.esc, r = range(), data = dataFor(r), items = itemsFor(r, data);
    cal.shown = items.events;
    // Keep the scroll position while the same range is redrawn (after a drop,
    // an Undo or a refresh); a new range starts near the current hour.
    var oldGrid = body.querySelector("#dk-tgrid"), viewKey = cal.mode + ":" + r.from;
    var keepScroll = oldGrid && cal.viewKey === viewKey ? oldGrid.scrollTop : null;
    cal.viewKey = viewKey;
    var modes = [["month", "Month"], ["week", "Week"], ["day", "Day"]];
    var layers = [["events", "Events", "#3b82f6"], ["tasks", "Tasks", "#16a34a"], ["deadlines", "Deadlines", "#dc2626"]];
    var note = "";
    if (cal.err) note = '<p class="dk-hint is-bad">' + esc(cal.err) + '</p>';
    else if (!data && cal.loading) note = '<p class="dk-hint">Loading this range from Google and Notion…</p>';
    else if (data && data.google && !data.google.configured) note = '<p class="dk-hint">Google Calendar is not connected, so only tasks and deadlines show. <button type="button" class="dk-link" data-act="settings">Connect</button></p>';
    var html = '<div class="dk-calview">' +
      '<div class="dk-tools">' +
        '<div class="dk-seg" role="group" aria-label="Range">' + modes.map(function (m) {
          return '<button type="button" class="dk-seg__b" data-calmode="' + m[0] + '" aria-pressed="' + (cal.mode === m[0]) + '">' + m[1] + '</button>'; }).join("") + '</div>' +
        '<div class="dk-calnav"><button type="button" class="dk-icon" data-calnav="-1" aria-label="Previous ([)"><i class="fas fa-chevron-left" aria-hidden="true"></i></button>' +
          '<button type="button" class="dk-btn" data-calnav="0">Today</button>' +
          '<button type="button" class="dk-icon" data-calnav="1" aria-label="Next (])"><i class="fas fa-chevron-right" aria-hidden="true"></i></button></div>' +
        '<h3 class="dk-period">' + esc(label()) + '</h3>' +
        '<div class="dk-layers" role="group" aria-label="Layers">' + layers.map(function (l) {
          return '<button type="button" class="dk-layer" data-layer="' + l[0] + '" aria-pressed="' + cal.layers[l[0]] + '"><i class="dk-swatch" style="--c:' + l[2] + '"></i>' + l[1] + '</button>'; }).join("") + '</div>' +
      '</div>' + note;
    if (cal.mode === "month") html += monthHtml(r, items);
    else {
      var days = [];
      for (var i = 0; i < (cal.mode === "week" ? 7 : 1); i++) days.push(C.addDays(r.start, i));
      html += gridHtml(days, items);
    }
    html += '<p class="dk-hint dk-calhint">' + (cal.mode === "month" ? "Click a day to open it." :
      "Click or drag across empty time to add an event. Drag an event to move it, or its bottom edge to change its length. Click a day number to open that day.") + '</p></div>';
    body.innerHTML = html;
    if (!body.__dkCal) {
      body.__dkCal = true;
      body.addEventListener("click", swallowDragClick, true);
      body.addEventListener("click", onClick);
      body.addEventListener("pointerdown", onPointerDown);
    }
    positionNow(body);
    var g = body.querySelector("#dk-tgrid");
    if (g) g.scrollTop = keepScroll != null ? keepScroll : (Math.max(DAY_START, Math.min(new Date().getHours() - 1, DAY_END - 8)) - DAY_START) * HOUR_PX;
  }

  /* ---- drag: move, resize and draw events in the week and day grids -------
     Mouse and pen only, so on a touchscreen the grid still scrolls and a tap
     still opens or creates. A press that barely moves stays a click. */
  var SNAP = 15, drag = null, dragEndedAt = 0;

  function dayMinutes(d) { return d.getHours() * 60 + d.getMinutes(); }
  // Only events that start and end on the same day move: one that ends at
  // midnight would come back from the backend ending at 23:59.
  function movable(e) {
    return e.editable && !e.allDay && C.ymd(e.start) === C.ymd(e.end) && dayMinutes(e.start) >= DAY_START * 60;
  }
  function clock(m) { return m >= 24 * 60 ? "23:59" : C.pad2(Math.floor(m / 60)) + ":" + C.pad2(m % 60); }
  function rawMinutes(col, clientY) { return DAY_START * 60 + (clientY - col.getBoundingClientRect().top) / HOUR_PX * 60; }
  function snap(m) { return Math.round(m / SNAP) * SNAP; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function colAt(body, clientX) {
    var best = null, gap = Infinity;
    body.querySelectorAll(".dk-dcol").forEach(function (c) {
      var r = c.getBoundingClientRect(), dist = clientX < r.left ? r.left - clientX : clientX > r.right ? clientX - r.right : 0;
      if (dist < gap) { gap = dist; best = c; }
    });
    return best;
  }
  function place(el, s, e) {
    var span = (DAY_END - DAY_START) * 60;
    el.style.top = ((s - DAY_START * 60) / span * 100).toFixed(3) + "%";
    el.style.height = (Math.max(SNAP, e - s) / span * 100).toFixed(3) + "%";
    var label = el.querySelector("span");
    if (label) label.textContent = clock(s) + "–" + clock(e);
  }

  function onPointerDown(ev) {
    if (A().S.ui.view !== "calendar" || cal.mode === "month" || ev.button !== 0) return;
    if (ev.pointerType !== "mouse" && ev.pointerType !== "pen") return;
    var col = ev.target.closest(".dk-dcol");
    if (!col) return;
    var d = { body: ev.currentTarget, col0: col, col: col, x0: ev.clientX, y0: ev.clientY, moved: false };
    var tev = ev.target.closest(".dk-tev");
    if (tev) {
      var id = tev.getAttribute("data-event");
      var e = (cal.shown || []).filter(function (x) { return x.id === id; })[0];
      if (!e || !movable(e)) return;
      d.kind = ev.target.closest(".dk-tev__grip") ? "resize" : "move";
      d.el = tev; d.ev = e;
      d.s0 = dayMinutes(e.start); d.e0 = dayMinutes(e.end);
      d.grab = rawMinutes(col, ev.clientY) - d.s0;
    } else {
      d.kind = "create";
      d.anchor = clamp(Math.floor(rawMinutes(col, ev.clientY) / SNAP) * SNAP, DAY_START * 60, DAY_END * 60 - SNAP);
    }
    drag = d;
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", cancelDrag);
    window.addEventListener("keydown", onDragKey);
  }

  function beginDrag(d) {
    d.moved = true;
    d.grid = d.body.querySelector(".dk-cal--grid");
    d.grid.classList.add("is-dragging");
    if (d.kind === "create") {
      d.el = document.createElement("div");
      d.el.className = "dk-tev is-ghost";
      d.el.innerHTML = "<b>New event</b><span></span>";
      d.col0.appendChild(d.el);
    } else {
      d.el.classList.add("is-dragging");
      d.el.style.left = "2px";
      d.el.style.width = "calc(100% - 4px)";
    }
  }

  function onPointerMove(ev) {
    var d = drag;
    if (!d) return;
    if (!ev.buttons) { cancelDrag(); return; }
    if (!d.moved) {
      if (Math.abs(ev.clientX - d.x0) + Math.abs(ev.clientY - d.y0) < 6) return;
      beginDrag(d);
    }
    // Scroll the hour grid when the pointer nears its top or bottom edge.
    var grid = d.body.querySelector("#dk-tgrid"), gr = grid.getBoundingClientRect();
    if (ev.clientY > gr.bottom - 28) grid.scrollTop += 12;
    else if (ev.clientY < gr.top + 28) grid.scrollTop -= 12;
    var lo = DAY_START * 60, hi = DAY_END * 60;
    if (d.kind === "move") {
      var len = d.e0 - d.s0, col = colAt(d.body, ev.clientX);
      d.s = clamp(snap(rawMinutes(col, ev.clientY) - d.grab), lo, hi - len);
      d.e = d.s + len;
      if (col !== d.col) { col.appendChild(d.el); d.col = col; }
    } else if (d.kind === "resize") {
      d.s = d.s0;
      d.e = clamp(snap(rawMinutes(d.col0, ev.clientY)), d.s0 + SNAP, hi);
    } else {
      var at = clamp(snap(rawMinutes(d.col0, ev.clientY)), lo, hi);
      d.s = Math.min(d.anchor, at);
      d.e = Math.max(d.anchor, at);
      if (d.e - d.s < SNAP) d.e = d.s + SNAP;
    }
    place(d.el, d.s, d.e);
  }

  function endDrag() {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    window.removeEventListener("pointercancel", cancelDrag);
    window.removeEventListener("keydown", onDragKey);
    var d = drag;
    drag = null;
    if (d && d.moved) { dragEndedAt = Date.now(); d.grid.classList.remove("is-dragging"); }
    return d;
  }
  function onPointerUp() {
    var d = endDrag();
    if (!d || !d.moved) return; // a plain click: onClick takes it
    var date = d.col.getAttribute("data-slot");
    if (d.kind === "create") { d.el.remove(); newEvent(date, clock(d.s), clock(d.e)); return; }
    if (date === C.ymd(d.ev.start) && d.s === d.s0 && d.e === d.e0) { A().render(); return; }
    moveEvent(d.ev, date, clock(d.s), clock(d.e));
  }
  function cancelDrag() {
    var d = endDrag();
    if (!d || !d.moved) return;
    if (d.kind === "create") d.el.remove();
    else A().render();
  }
  function onDragKey(ev) { if (ev.key === "Escape") cancelDrag(); }
  // The click that ends a drag must not also open the event or a new-event form.
  function swallowDragClick(ev) {
    if (Date.now() - dragEndedAt < 400) { ev.stopPropagation(); ev.preventDefault(); }
  }

  // Optimistic: the event moves at once, and moves back if Google refuses.
  function setTimes(e, date, start, end) {
    var S = A().S, s = C.parseYmd(date), x = C.parseYmd(date);
    s.setMinutes(C.minutesOf(start));
    x.setMinutes(C.minutesOf(end));
    [S.sync, cal.extra].forEach(function (src) {
      ((src && src.google && src.google.events) || []).forEach(function (raw) {
        if (raw.id === e.eventId && raw.calendarId === e.calendarId) { raw.start = s.toISOString(); raw.end = x.toISOString(); }
      });
    });
  }
  function moveEvent(e, date, start, end) {
    var a = A(), to = { date: date, start: start, end: end };
    var before = { date: C.ymd(e.start), start: a.hhmm(e.start), end: a.hhmm(e.end) };
    var save = function (when) {
      setTimes(e, when.date, when.start, when.end);
      a.render();
      return a.call("updateEvent", { calendarId: e.calendarId, id: e.eventId, date: when.date, start: when.start, end: when.end, allDay: false, tz: a.tz() });
    };
    save(to).then(function () {
      a.resync();
      var label = a.fmtDate(date, { weekday: "short", day: "numeric", month: "short" }) + " " + start + "–" + end;
      a.toast("Moved “" + e.title + "” to " + label + (e.recurring ? " (this occurrence only)" : "") + ".", { action: "Undo", onAction: function () {
        save(before).then(function () { a.resync(); a.toast("Put back."); }, function (err) {
          setTimes(e, to.date, to.start, to.end);
          a.render();
          a.failed(err, "Not put back");
        });
      } });
    }, function (err) {
      setTimes(e, before.date, before.start, before.end);
      a.render();
      a.failed(err, "Not moved");
    });
  }

  function shift(n) {
    var a = cal.anchor;
    if (n === 0) cal.anchor = new Date();
    else if (cal.mode === "month") cal.anchor = new Date(a.getFullYear(), a.getMonth() + n, 1);
    else cal.anchor = C.addDays(a, (cal.mode === "week" ? 7 : 1) * n);
    A().render();
  }

  function onClick(e) {
    if (A().S.ui.view !== "calendar") return;
    var t = e.target.closest("button, [data-day], [data-slot]");
    if (!t) return;
    var v;
    if ((v = t.getAttribute("data-calmode"))) { cal.mode = v; remember(); A().render(); return; }
    if ((v = t.getAttribute("data-calnav")) !== null) { shift(+v); return; }
    if ((v = t.getAttribute("data-layer"))) { cal.layers[v] = !cal.layers[v]; remember(); A().render(); return; }
    if ((v = t.getAttribute("data-dayview"))) { cal.anchor = C.parseYmd(v); cal.mode = "day"; remember(); A().render(); return; }
    if ((v = t.getAttribute("data-href"))) { window.open(v, "_blank", "noopener"); return; }
    if ((v = t.getAttribute("data-task"))) { var task = A().allTasks().filter(function (x) { return x.key === v; })[0]; if (task) A().toggleTask(v, !task.done); return; }
    if (t.hasAttribute("data-event") || t.hasAttribute("data-entry") || t.hasAttribute("data-act")) return; // handled by the shell
    if ((v = t.getAttribute("data-day")) && cal.mode === "month") { cal.anchor = C.parseYmd(v); cal.mode = "day"; remember(); A().render(); return; }
    if ((v = t.getAttribute("data-slot"))) {
      var rect = t.getBoundingClientRect(), y = e.clientY - rect.top;
      var mins = Math.round((y / HOUR_PX) * 2) * 30 + DAY_START * 60;
      mins = Math.max(DAY_START * 60, Math.min(mins, 23 * 60));
      var start = C.pad2(Math.floor(mins / 60)) + ":" + C.pad2(mins % 60), endM = Math.min(mins + 60, 23 * 60 + 59);
      newEvent(v, start, C.pad2(Math.floor(endM / 60)) + ":" + C.pad2(endM % 60));
    }
  }

  // `title` prefills the form (Block time on a task). With more than one
  // writable calendar a picker appears; the last one used is remembered.
  function newEvent(date, start, end, title) {
    var a = A(), esc = a.esc, g = a.googleReady(), S = a.S;
    var cals = g ? (S.sync.google.calendars || []).filter(function (c) { return c.writable; }) : [];
    var pick = cals.filter(function (c) { return c.id === S.ui.newCal; })[0] || cals.filter(function (c) { return c.primary; })[0] || cals[0];
    var calField = cals.length > 1 ? '<label class="dk-field"><span>Calendar</span><select class="dk-input" id="dk-ne-cal">' + cals.map(function (c) {
      return '<option value="' + esc(c.id) + '"' + (c === pick ? " selected" : "") + '>' + esc(c.title || c.id) + '</option>';
    }).join("") + '</select></label>' : "";
    var d = a.dialog("dk-newev", "New event",
      '<label class="dk-field"><span>Title</span><input type="text" class="dk-input" id="dk-ne-title" placeholder="What is it?" value="' + esc(title || "") + '"></label>' +
      '<div class="dk-grid3"><label class="dk-field"><span>Date</span><input type="date" class="dk-input" id="dk-ne-date" value="' + date + '"></label>' +
      '<label class="dk-field"><span>Start</span><input type="time" class="dk-input" id="dk-ne-start" value="' + start + '"></label>' +
      '<label class="dk-field"><span>End</span><input type="time" class="dk-input" id="dk-ne-end" value="' + end + '"></label></div>' +
      '<label class="dk-toggle"><input type="checkbox" id="dk-ne-allday"> All day</label>' + calField +
      '<p class="dk-hint" id="dk-ne-msg" role="status">' + (g ? "" : "Google is not connected, so this opens Google Calendar with the event filled in.") + '</p>',
      '<button type="button" class="dk-btn dk-btn--primary" id="dk-ne-go">' + (g ? "Create" : "Open Google Calendar") + '</button>');
    var go = function () {
      var o = { title: document.getElementById("dk-ne-title").value.trim(), date: document.getElementById("dk-ne-date").value, start: document.getElementById("dk-ne-start").value,
        end: document.getElementById("dk-ne-end").value, allDay: document.getElementById("dk-ne-allday").checked, tz: a.tz() };
      if (!o.title) { document.getElementById("dk-ne-title").focus(); return; }
      if (!g) { window.open(C.gcalTemplateUrl(o), "_blank", "noopener"); d.close(); return; }
      var calSel = document.getElementById("dk-ne-cal"), calId = calSel ? calSel.value : "";
      if (calId) { S.ui.newCal = calId; a.saveUi(); }
      document.getElementById("dk-ne-go").disabled = true;
      a.call("createEvent", { title: o.title, date: o.date, start: o.start, end: o.end, allDay: o.allDay, tz: o.tz, calendarId: calId || undefined }).then(function () {
        d.close(); a.toast("Event created."); cal.extra = null; a.refresh(true);
      }, function (err) { document.getElementById("dk-ne-go").disabled = false; document.getElementById("dk-ne-msg").textContent = err.message; });
    };
    document.getElementById("dk-ne-go").addEventListener("click", go);
    document.getElementById("dk-ne-title").addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); go(); } });
    setTimeout(function () { document.getElementById("dk-ne-title").focus(); }, 30);
  }

  function findEvent(id) {
    var data = cal.extra;
    var list = ((data && data.google && data.google.events) || []).map(C.normEvent).filter(Boolean);
    return list.filter(function (e) { return e.id === id; })[0] || null;
  }

  setInterval(function () {
    var body = document.getElementById("dk-body");
    if (body && Desk.app && Desk.app.S.ui.view === "calendar") positionNow(body);
  }, 60e3);

  function go(dateYmd, mode) {
    cal.anchor = C.parseYmd(dateYmd);
    if (mode) { cal.mode = mode; remember(); }
  }

  Desk.calendar = { render: render, shift: shift, go: go, findEvent: findEvent, newEvent: newEvent, invalidate: function () { cal.extra = null; } };
})();
