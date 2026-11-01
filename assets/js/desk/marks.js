/* ==========================================================================
   Research desk - title styles on Agenda events and tasks: colour, bold,
   italic, highlight and a star. Google keeps titles as plain text, so the
   styles live on the desk, in the settings/marks document (keys and the mark
   shape are in core.js, markKey / normMark). Uses Desk.app at call time, so it
   can load before app.js.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var DOC_ID = "marks";
  var SAVE_DELAY_MS = 900;   // a burst of clicks becomes one write
  var MAX_RETRIES = 3;       // after "changed elsewhere", merge and try again

  // items: what the page shows (server copy with local edits on top).
  // dirty: key -> sequence number of the last local edit not yet saved.
  var M = { version: 0, items: {}, dirty: {}, seq: 0, timer: null, saving: false, again: false, retries: 0 };

  /* ---- state ------------------------------------------------------------ */
  // A server (or cached) copy arrives; local edits still on their way win.
  // A load that set off before a save can answer after it: the older copy
  // is ignored. Edits whose save failed get another try here.
  function apply(doc) {
    if (!doc || !doc.data || (doc.version || 0) < M.version) return;
    var items = C.normMarks(doc.data.items), mine = M.items;
    Object.keys(M.dirty).forEach(function (k) { if (mine[k]) items[k] = mine[k]; else delete items[k]; });
    M.items = items;
    M.version = doc.version || 0;
    if (Object.keys(M.dirty).length && !M.saving) schedule(SAVE_DELAY_MS);
  }
  function dump() { return { version: M.version, data: { items: M.items } }; }
  // Signing out forgets everything, unsaved edits included.
  function reset() {
    clearTimeout(M.timer);
    M = { version: 0, items: {}, dirty: {}, seq: 0, timer: null, saving: false, again: false, retries: 0 };
  }
  function get(key) { return M.items[key] || null; }
  function starred(key) { return !!(M.items[key] && M.items[key].s); }

  function set(key, mark) {
    if (!C.isMarkKey(key)) return;
    var m = C.normMark(Object.assign({}, mark, { at: A().today() }));
    var next = Object.assign({}, M.items);
    if (m) next[key] = m; else delete next[key];
    M.items = next;
    M.dirty[key] = ++M.seq;
    A().render();
    schedule(SAVE_DELAY_MS);
  }

  /* ---- saving ----------------------------------------------------------- */
  function schedule(ms) {
    clearTimeout(M.timer);
    M.timer = setTimeout(flush, ms);
  }
  // What is in view, or null when the last Google read was partial: a
  // calendar or Tasks that failed once must not make their styles look stale.
  function liveKeys() {
    var a = A(), g = a.S.sync && a.S.sync.google;
    if (!g || (g.configured && (!g.ok || (g.warnings || []).length))) return null;
    return a.events().map(C.eventMarkKey).concat(a.allTasks().map(C.taskMarkKey));
  }
  function flush() {
    if (!Object.keys(M.dirty).length) return;
    if (M.saving) { M.again = true; return; }
    var sentSeq = M.seq, a = A(), live = liveKeys();
    var data = { items: live ? C.pruneMarks(M.items, live, a.today()) : M.items };
    M.saving = true;
    // Version 0 is a real base: "create it, unless someone already has".
    a.call("put", { collection: "settings", id: DOC_ID, data: data, baseVersion: M.version }).then(function (r) {
      M.version = r.doc.version;
      M.retries = 0;
      Object.keys(M.dirty).forEach(function (k) { if (M.dirty[k] <= sentSeq) delete M.dirty[k]; });
      a.persist();
    }, function (err) {
      // Someone else saved styles meanwhile: take theirs, keep ours on top, retry.
      if (err.status === 409 && err.body && err.body.doc && M.retries < MAX_RETRIES) {
        M.retries++;
        apply(err.body.doc);
        a.render();
        M.again = true;
        return;
      }
      M.retries = 0;
      a.failed(err, "Style not saved");
    }).then(function () {
      M.saving = false;
      if (M.again) { M.again = false; schedule(0); }
    });
  }

  /* ---- markup ----------------------------------------------------------- */
  // A title, escaped, inside its style span when it has one.
  function title(key, text) {
    var a = A(), m = get(key), t = a.esc(text);
    if (!m) return t;
    return '<span class="' + C.markClass(m) + '">' +
      (m.s ? '<i class="fas fa-star dk-mk__star" aria-hidden="true"></i><span class="sr-only">Starred: </span>' : "") + t + '</span>';
  }
  function eventTitle(e) { return title(C.eventMarkKey(e), e.title); }
  function taskTitle(t) { return title(C.taskMarkKey(t), t.title); }

  function pressed(on) { return ' aria-pressed="' + !!on + '"'; }
  function bar(key) {
    var esc = A().esc, m = get(key) || {};
    // on === null: an action, not a toggle.
    var tb = function (attr, on, label, inner) {
      return '<button type="button" class="dk-tb" ' + attr + (on === null ? "" : pressed(on)) + ' title="' + label + '" aria-label="' + label + '">' + inner + '</button>';
    };
    return '<div class="dk-mkbar" role="group" aria-label="Title style" data-mkkey="' + esc(key) + '">' +
      tb('data-mk="b"', m.b, "Bold", "<b>B</b>") +
      tb('data-mk="i"', m.i, "Italic", "<i>I</i>") +
      tb('data-mk="s"', m.s, "Star: keeps a task at the top of its group", '<i class="fas fa-star" aria-hidden="true"></i>') +
      '<span class="dk-tb__sep"></span>' +
      C.TEXT_COLORS.map(function (c) {
        return '<button type="button" class="dk-sw" data-mkc="' + c.n + '"' + pressed(m.c === c.n) + ' style="background:' + c.swatch + '" title="' + c.name + ' text" aria-label="' + c.name + ' text"></button>';
      }).join("") +
      '<span class="dk-tb__sep"></span>' +
      C.HIGHLIGHTS.map(function (c) {
        return '<button type="button" class="dk-sw dk-sw--hl" data-mkh="' + c.n + '"' + pressed(m.h === c.n) + ' style="background:' + c.swatch + '" title="' + c.name + ' highlight" aria-label="' + c.name + ' highlight"></button>';
      }).join("") +
      '<span class="dk-tb__sep"></span>' +
      tb('data-mk="clear"', null, "Clear the style", '<i class="fas fa-remove-format" aria-hidden="true"></i>') +
    '</div>';
  }
  function paintBar(el, key) {
    var m = get(key) || {};
    el.querySelectorAll("[data-mk]").forEach(function (b) { var k = b.getAttribute("data-mk"); if (k !== "clear") b.setAttribute("aria-pressed", String(!!m[k])); });
    el.querySelectorAll("[data-mkc]").forEach(function (b) { b.setAttribute("aria-pressed", String(m.c === +b.getAttribute("data-mkc"))); });
    el.querySelectorAll("[data-mkh]").forEach(function (b) { b.setAttribute("aria-pressed", String(m.h === +b.getAttribute("data-mkh"))); });
  }
  // A swatch pressed again takes its colour off; Clear takes everything off.
  function wire(el, key, onChange) {
    if (!el) return;
    el.addEventListener("mousedown", function (e) { if (e.target.closest("button")) e.preventDefault(); });
    el.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      var m = Object.assign({}, get(key) || {}), v;
      if ((v = b.getAttribute("data-mk"))) { if (v === "clear") m = {}; else m[v] = !m[v]; }
      else if ((v = b.getAttribute("data-mkc"))) m.c = m.c === +v ? 0 : +v;
      else if ((v = b.getAttribute("data-mkh"))) m.h = m.h === +v ? 0 : +v;
      else return;
      set(key, m);
      paintBar(el, key);
      if (onChange) onChange(get(key));
    });
  }
  // A title field in a dialog shows colour, bold and italic as they are picked.
  function styleInput(input, key) {
    var base = input.className.replace(/\s*\bdk-mk\b.*$/, "");
    var paint = function (m) { input.className = base + (m ? " " + C.markClass(m, { text: true }) : ""); };
    paint(get(key));
    return paint;
  }
  // The "Style" field for the task and event dialogs.
  function field(key) {
    return '<div class="dk-field"><span>Style <em>saved as you click · shown on the desk, not in Google</em></span>' + bar(key) + '</div>';
  }

  /* ---- right-click popover ---------------------------------------------
     On any event or task in Today and the calendar. Uses the Popover API for
     outside-click and Escape; without it, the same bar opens in a dialog. */
  var pop = { el: null, anchor: null, anchorSel: "", anchorIdx: 0 };
  // macOS, Linux and touch fire contextmenu with the button still down, and an
  // auto popover shown then closes when it is released outside it; so the
  // popover waits for the release (with a fallback should it never come).
  var held = false;
  document.addEventListener("pointerdown", function () { held = true; }, true);
  ["pointerup", "pointercancel"].forEach(function (t) { document.addEventListener(t, function () { held = false; }, true); });
  window.addEventListener("blur", function () { held = false; });
  function afterRelease(fn) {
    if (!held) { fn(); return; }
    var done = false, timer = null;
    var go = function () {
      if (done) return;
      done = true;
      clearTimeout(timer);
      document.removeEventListener("pointerup", go, true);
      document.removeEventListener("pointercancel", go, true);
      setTimeout(fn, 0);
    };
    document.addEventListener("pointerup", go, true);
    document.addEventListener("pointercancel", go, true);
    timer = setTimeout(go, 1500);
  }
  function targetOf(node) {
    var a = A(), el = node && node.closest && node.closest("[data-event], [data-edittask], button[data-task], [data-mkfor]");
    if (!el) return null;
    var v;
    if ((v = el.getAttribute("data-mkfor"))) return { el: el, key: v, label: el.getAttribute("data-mklabel") || "" };
    if ((v = el.getAttribute("data-event"))) {
      var e = a.findEvent(v);
      return e ? { el: el, key: C.eventMarkKey(e), label: e.title } : null;
    }
    v = el.getAttribute("data-edittask") || el.getAttribute("data-task");
    var t = a.allTasks().filter(function (x) { return x.key === v; })[0];
    return t ? { el: el, key: C.taskMarkKey(t), label: t.title } : null;
  }
  function onContext(e) {
    var tg = targetOf(e.target);
    if (!tg) return;
    e.preventDefault();
    var r = tg.el.getBoundingClientRect();
    // The context-menu key reports the corner of the window, not the item.
    var x = e.clientX || r.left, y = e.clientY || r.bottom;
    afterRelease(function () { open(tg, x, y); });
  }
  function openFor(btn) {
    var tg = targetOf(btn);
    if (!tg) return;
    var r = btn.getBoundingClientRect();
    open(tg, r.left, r.bottom + 4);
  }
  function open(tg, x, y) {
    var a = A(), esc = a.esc;
    var body = '<p class="dk-mkpop__t" title="' + esc(tg.label) + '">' + title(tg.key, tg.label) + '</p>' + bar(tg.key);
    if (!HTMLElement.prototype.showPopover) {
      var d = a.dialog("dk-mkdlg", "Style", body);
      wire(d.querySelector(".dk-mkbar"), tg.key, function () { d.querySelector(".dk-mkpop__t").innerHTML = title(tg.key, tg.label); });
      return;
    }
    if (!pop.el) {
      pop.el = document.createElement("div");
      pop.el.id = "dk-mkpop";
      pop.el.className = "dk-mkpop";
      pop.el.setAttribute("popover", "auto");
      pop.el.setAttribute("role", "dialog");
      pop.el.setAttribute("aria-label", "Title style");
      document.body.appendChild(pop.el);
      // Back to the item on close. A style change redraws the list, so the
      // item is found again by the attribute it was opened from.
      // Deferred: when the popover hides, focus may still sit on its hidden
      // button until the browser's focus fixup runs.
      pop.el.addEventListener("toggle", function (ev) {
        if (ev.newState !== "closed" || !pop.anchor) return;
        setTimeout(function () {
          var at = document.activeElement;
          if (at && at !== document.body && !pop.el.contains(at)) return; // the user moved on
          var all = !document.contains(pop.anchor) && pop.anchorSel ? document.querySelectorAll(pop.anchorSel) : [];
          var el = document.contains(pop.anchor) ? pop.anchor : all[pop.anchorIdx] || all[0];
          if (el) el.focus();
        }, 0);
      });
    }
    if (pop.el.matches(":popover-open")) pop.el.hidePopover();
    pop.anchor = tg.el;
    pop.anchorSel = ["data-mkfor", "data-event", "data-edittask", "data-task"].filter(function (n) { return tg.el.hasAttribute(n); })
      .map(function (n) { return "#dk-body [" + n + '="' + CSS.escape(tg.el.getAttribute(n)) + '"]'; })[0] || "";
    // The same event can show twice (Now / Next and the Agenda): remember which.
    pop.anchorIdx = pop.anchorSel ? Math.max(0, Array.prototype.indexOf.call(document.querySelectorAll(pop.anchorSel), tg.el)) : 0;
    pop.el.innerHTML = body + '<button type="button" class="dk-btn dk-btn--quiet dk-mkpop__done">Done</button>';
    wire(pop.el.querySelector(".dk-mkbar"), tg.key, function () { pop.el.querySelector(".dk-mkpop__t").innerHTML = title(tg.key, tg.label); });
    pop.el.querySelector(".dk-mkpop__done").addEventListener("click", function () { pop.el.hidePopover(); });
    pop.el.style.left = "0px";
    pop.el.style.top = "0px";
    pop.el.showPopover();
    // Keep it on screen: flip above the pointer when there is no room below.
    var w = pop.el.offsetWidth, h = pop.el.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    pop.el.style.left = Math.max(8, Math.min(x, vw - w - 8)) + "px";
    pop.el.style.top = (y + h + 8 > vh ? Math.max(8, y - h - 8) : y) + "px";
    var first = pop.el.querySelector(".dk-mkbar button");
    if (first) first.focus();
  }

  Desk.marks = {
    DOC_ID: DOC_ID, apply: apply, dump: dump, reset: reset, get: get, set: set, starred: starred,
    title: title, eventTitle: eventTitle, taskTitle: taskTitle, bar: bar, field: field, wire: wire, styleInput: styleInput,
    onContext: onContext, openFor: openFor
  };
})();
