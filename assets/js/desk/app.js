/* ==========================================================================
   Research desk - shell, data and the Today / Board / Notion views.
   Loaded last by the loader in _pages/research-ideas.html, after core.js,
   editor.js and calendar.js have registered themselves on window.Desk.
   Server: workers/desk (Cloudflare Worker). Nothing private is in this file;
   everything shown comes from the Worker after the passphrase unlocks it.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk;
  var C = Desk.core;
  var host = document.getElementById("desk");
  if (!host || !C) return;

  var KEY = { token: "desk.token", cache: "desk.cache.v1", ui: "desk.ui.v1" };
  var VIEWS = [
    { id: "today", label: "Today", icon: "fa-sun" },
    { id: "board", label: "Board", icon: "fa-th-large" },
    { id: "calendar", label: "Calendar", icon: "fa-calendar-alt" },
    { id: "notion", label: "Research OS", icon: "fa-database" }
  ];
  var README = "https://github.com/s-elim/s-elim.github.io/blob/master/workers/desk/README.md";
  var AUTO_REFRESH_MS = 5 * 60e3;

  var S = {
    endpoint: (host.getAttribute("data-endpoint") || "").replace(/\/+$/, ""),
    token: "",
    health: null,
    entries: [],          // [{ id, version, e }]
    deskTasks: [],        // raw docs from the "tasks" collection
    prefs: { id: "prefs", version: 0, data: { watched: C.DEFAULT_WATCH.slice(), notionHome: "", lastExportAt: "" } },
    sync: null,           // last /sync payload
    syncing: false,
    offline: false,
    conferences: [],
    ui: { view: "today", collapsed: false, focus: false, density: "comfy", quickMode: "task",
          board: { q: "", kind: "all", axis: "all", status: "open", sort: "pinned", layout: "cards" },
          notionHideDone: true, showDoneTasks: false }
  };

  /* ---- small helpers -------------------------------------------------- */
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeUrl(u) { u = String(u || "").trim(); return /^https?:\/\//i.test(u) ? u : ""; }
  function store(k, v) { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function load(k) { try { var r = localStorage.getItem(k); return r ? JSON.parse(r) : null; } catch (e) { return null; } }
  function today() { return C.ymd(new Date()); }
  function tz() { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { return ""; } }
  function newId(prefix) { return prefix + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function fmtDate(ymdStr, opts) {
    if (!C.isYmd(ymdStr)) return "";
    return C.parseYmd(ymdStr).toLocaleDateString(undefined, opts || { day: "numeric", month: "short" });
  }
  function hhmm(d) { return C.pad2(d.getHours()) + ":" + C.pad2(d.getMinutes()); }
  function plural(n, w) { return n + " " + w + (n === 1 ? "" : "s"); }

  // Rich text from the editor is stored as HTML; only this whitelist survives.
  var OK_TAGS = { B: 1, STRONG: 1, I: 1, EM: 1, U: 1, S: 1, STRIKE: 1, CODE: 1, BR: 1, UL: 1, OL: 1, LI: 1, P: 1, DIV: 1, SPAN: 1, MARK: 1, A: 1 };
  var OK_CLASS = /^(tc-[1-6]|hl-[1-5]|pin)$/;
  function scrub(n) {
    if (n.nodeType === 3) return;
    if (n.nodeType !== 1) { n.parentNode.removeChild(n); return; }
    var tag = n.tagName.toUpperCase(), i;
    if (!OK_TAGS[tag]) {
      var p = n.parentNode, moved = [];
      while (n.firstChild) { moved.push(n.firstChild); p.insertBefore(n.firstChild, n); }
      p.removeChild(n);
      for (i = 0; i < moved.length; i++) scrub(moved[i]);
      return;
    }
    Array.prototype.slice.call(n.attributes).forEach(function (a) {
      var name = a.name.toLowerCase();
      if (tag === "A" && name === "href" && safeUrl(a.value)) return;
      if ((tag === "SPAN" || tag === "MARK") && name === "class") {
        var keep = a.value.split(/\s+/).filter(function (c) { return OK_CLASS.test(c); });
        if (keep.length) { n.setAttribute("class", keep.join(" ")); return; }
      }
      n.removeAttribute(a.name);
    });
    if (tag === "A" && n.getAttribute("href")) { n.setAttribute("target", "_blank"); n.setAttribute("rel", "noopener noreferrer"); }
    Array.prototype.slice.call(n.childNodes).forEach(scrub);
  }
  function sanitize(html) {
    var box = document.createElement("div");
    box.innerHTML = String(html == null ? "" : html).slice(0, 60000);
    Array.prototype.slice.call(box.childNodes).forEach(scrub);
    return box.innerHTML;
  }
  function plain(html) { return C.htmlToText(sanitize(html)); }
  function pinsIn(html) {
    var box = document.createElement("div");
    box.innerHTML = sanitize(html);
    return Array.prototype.slice.call(box.querySelectorAll("mark.pin")).map(function (m) { return (m.textContent || "").trim(); }).filter(Boolean);
  }

  /* ---- network -------------------------------------------------------- */
  function api(method, path, body) {
    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 30000) : null;
    var headers = {};
    if (S.token) headers.Authorization = "Bearer " + S.token;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    return fetch(S.endpoint + path, {
      method: method, headers: headers, body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctrl ? ctrl.signal : undefined, cache: "no-store"
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (r.status === 401 && path !== "/auth") { signOut("Your session ended. Unlock the desk again."); }
        if (!r.ok || j.ok === false) {
          var err = new Error(j.error || "The desk server answered " + r.status + ".");
          err.status = r.status; err.body = j;
          throw err;
        }
        return j;
      });
    }, function (e) {
      var err = new Error(e && e.name === "AbortError" ? "The desk server took too long to answer." : "Cannot reach the desk server.");
      err.offline = true;
      throw err;
    }).then(function (j) { if (timer) clearTimeout(timer); return j; }, function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  function persist() {
    store(KEY.cache, { entries: S.entries, deskTasks: S.deskTasks, prefs: S.prefs, sync: S.sync });
  }
  function saveUi() { store(KEY.ui, S.ui); }

  /* ---- toasts and notices -------------------------------------------- */
  var toastTimer = null;
  function toast(msg, opts) {
    var el = $("dk-toast");
    if (!el) return;
    opts = opts || {};
    el.innerHTML = '<span>' + esc(msg) + '</span>' +
      (opts.action ? '<button type="button" class="dk-toast__act">' + esc(opts.action) + '</button>' : "") +
      '<button type="button" class="dk-toast__x" aria-label="Dismiss"><i class="fas fa-times" aria-hidden="true"></i></button>';
    el.className = "dk-toast is-on" + (opts.error ? " is-error" : "");
    var act = el.querySelector(".dk-toast__act");
    if (act) act.addEventListener("click", function () { hideToast(); opts.onAction(); });
    el.querySelector(".dk-toast__x").addEventListener("click", hideToast);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, opts.error ? 9000 : 4500);
  }
  function hideToast() { var el = $("dk-toast"); if (el) el.className = "dk-toast"; }
  function failed(err, what) {
    toast((what ? what + ": " : "") + (err && err.message ? err.message : "something went wrong."), { error: true });
  }

  /* ---- entries -------------------------------------------------------- */
  function entryDoc(id) {
    for (var i = 0; i < S.entries.length; i++) if (S.entries[i].id === id) return S.entries[i];
    return null;
  }
  function upsertEntry(doc) {
    var rec = { id: doc.id, version: doc.version, e: C.normaliseEntry(doc.id, doc.data) };
    var i = S.entries.findIndex(function (x) { return x.id === doc.id; });
    if (doc.deleted) { if (i !== -1) S.entries.splice(i, 1); }
    else if (i === -1) S.entries.push(rec);
    else S.entries[i] = rec;
  }
  function entryData(e) {
    var out = {};
    Object.keys(e).forEach(function (k) { if (k !== "id") out[k] = e[k]; });
    return out;
  }
  // The one write path for entries: optimistic locally, versioned on the server.
  function saveEntry(id, data, baseVersion) {
    data.updatedAt = new Date().toISOString();
    if (!data.addedAt) data.addedAt = data.updatedAt;
    return api("PUT", "/docs/entries/" + encodeURIComponent(id), { data: data, baseVersion: baseVersion })
      .then(function (r) { upsertEntry(r.doc); persist(); render(); return r.doc; }, function (err) {
        if (err.status === 409 && err.body && err.body.doc) {
          upsertEntry(err.body.doc); persist(); render();
          toast("This entry changed on another device, so the newer copy is shown. Reapply your edit.", { error: true });
        }
        throw err;
      });
  }
  function patchEntry(id, delta) {
    var rec = entryDoc(id);
    if (!rec) return Promise.resolve();
    var data = Object.assign(entryData(rec.e), delta);
    return saveEntry(id, data, rec.version).catch(function (err) { if (err.status !== 409) failed(err, "Not saved"); });
  }
  function deleteEntry(id) {
    var rec = entryDoc(id);
    if (!rec) return Promise.resolve();
    return api("DELETE", "/docs/entries/" + encodeURIComponent(id) + "?base=" + rec.version).then(function (r) {
      upsertEntry(r.doc); persist(); render();
      toast("Entry deleted. Its history is kept on the server.");
    });
  }

  /* ---- desk tasks (used when Google Tasks is not connected) ----------- */
  function saveDeskTask(id, data, baseVersion) {
    return api("PUT", "/docs/tasks/" + encodeURIComponent(id), { data: data, baseVersion: baseVersion }).then(function (r) {
      var i = S.deskTasks.findIndex(function (d) { return d.id === id; });
      if (i === -1) S.deskTasks.push(r.doc); else S.deskTasks[i] = r.doc;
      persist(); render();
    });
  }

  function googleReady() { return !!(S.sync && S.sync.google && S.sync.google.ok); }
  function notionReady() { return !!(S.sync && S.sync.notion && S.sync.notion.configured); }

  function toggleTask(key, done) {
    var t = allTasks().filter(function (x) { return x.key === key; })[0];
    if (!t) return;
    if (t.source === "google") {
      var g = S.sync.google.tasks.filter(function (x) { return x.id === t.id && x.listId === t.listId; })[0];
      if (g) { g.done = done; g.completed = done ? new Date().toISOString() : ""; render(); }
      api("POST", "/google", { action: "setTask", listId: t.listId, id: t.id, done: done }).then(persist, function (err) {
        if (g) { g.done = !done; render(); }
        failed(err, "Google Tasks");
      });
    } else {
      var d = S.deskTasks.filter(function (x) { return x.id === t.id; })[0];
      if (!d) return;
      var data = Object.assign({}, d.data, { done: done, completedAt: done ? new Date().toISOString() : "" });
      saveDeskTask(d.id, data, d.version).catch(function (err) { failed(err, "Task not saved"); });
    }
  }
  function deleteDeskTask(id) {
    var d = S.deskTasks.filter(function (x) { return x.id === id; })[0];
    if (!d) return;
    api("DELETE", "/docs/tasks/" + encodeURIComponent(id) + "?base=" + d.version).then(function () {
      S.deskTasks = S.deskTasks.filter(function (x) { return x.id !== id; });
      persist(); render();
    }, function (err) { failed(err, "Task not deleted"); });
  }
  function allTasks() {
    return C.unifyTasks(S.sync && S.sync.google && S.sync.google.tasks, S.deskTasks);
  }

  /* ---- sync ----------------------------------------------------------- */
  function defaultRange() {
    var t = new Date(), from = C.addDays(t, -21), to = C.addDays(t, 120);
    return { from: C.ymd(from), to: C.ymd(to), timeMin: from.toISOString(), timeMax: C.addDays(to, 1).toISOString() };
  }
  function syncQuery(r) {
    return "/sync?from=" + r.from + "&to=" + r.to + "&timeMin=" + encodeURIComponent(r.timeMin) +
      "&timeMax=" + encodeURIComponent(r.timeMax) + "&tz=" + encodeURIComponent(tz());
  }
  function fetchSync(range) { return api("GET", syncQuery(range)); }

  function loadDocs() {
    return Promise.all([api("GET", "/docs/entries"), api("GET", "/docs/tasks"), api("GET", "/docs/settings")]).then(function (res) {
      S.entries = [];
      res[0].docs.forEach(upsertEntry);
      S.deskTasks = res[1].docs;
      var p = res[2].docs.filter(function (d) { return d.id === "prefs"; })[0];
      if (p) S.prefs = { id: "prefs", version: p.version, data: Object.assign({}, S.prefs.data, p.data) };
    });
  }

  function refresh(quiet) {
    if (S.syncing || !S.token) return Promise.resolve();
    S.syncing = true;
    renderStatus();
    return Promise.all([loadDocs(), fetchSync(defaultRange())]).then(function (res) {
      S.sync = res[1];
      S.offline = false;
      if (Desk.calendar) Desk.calendar.invalidate();
      persist();
      if (!quiet) toast("Up to date.");
    }, function (err) {
      S.offline = !!err.offline;
      if (err.status !== 401) failed(err, "Refresh failed");
    }).then(function () {
      S.syncing = false;
      render();
    });
  }

  function savePrefs(delta) {
    var data = Object.assign({}, S.prefs.data, delta);
    S.prefs.data = data;
    render();
    return api("PUT", "/docs/settings/prefs", { data: data, baseVersion: S.prefs.version || undefined }).then(function (r) {
      S.prefs = { id: "prefs", version: r.doc.version, data: r.doc.data };
      persist();
    }, function (err) {
      if (err.status === 409 && err.body && err.body.doc) S.prefs = { id: "prefs", version: err.body.doc.version, data: err.body.doc.data };
      failed(err, "Settings not saved");
    });
  }

  /* ---- auth ----------------------------------------------------------- */
  function signOut(msg) {
    S.token = "";
    store(KEY.token, null);
    store(KEY.cache, null);
    S.entries = []; S.deskTasks = []; S.sync = null;
    renderSignIn(msg || "");
  }

  function renderSignIn(msg) {
    host.hidden = false;
    host.className = "desk desk--locked" + (standalone ? " desk--standalone" : "");
    document.documentElement.classList.remove("desk-focus");
    placeHost(false);
    host.innerHTML =
      '<div class="dk-signin">' +
        '<span class="dk-signin__mark" aria-hidden="true"><i class="fas fa-lock"></i></span>' +
        '<div class="dk-signin__text"><h2 class="dk-signin__title">Research Desk</h2>' +
        '<p>Private workspace for ideas, plans, tasks, deadlines and the calendar. Owner only.</p></div>' +
        '<form class="dk-signin__form" id="dk-signin" autocomplete="on">' +
          '<input type="text" name="username" value="desk" autocomplete="username" hidden>' +
          '<input type="password" id="dk-pass" name="password" autocomplete="current-password" placeholder="Passphrase" required aria-label="Passphrase">' +
          '<button type="submit" class="dk-btn dk-btn--primary" id="dk-unlock">Unlock</button>' +
        '</form>' +
        '<p class="dk-signin__msg" id="dk-signin-msg" role="status">' + esc(msg) + '</p>' +
      '</div>';
    $("dk-signin").addEventListener("submit", function (e) {
      e.preventDefault();
      var pass = $("dk-pass").value;
      if (!pass) return;
      $("dk-unlock").disabled = true;
      $("dk-signin-msg").textContent = "Checking…";
      api("POST", "/auth", { passphrase: pass }).then(function (r) {
        S.token = r.token;
        store(KEY.token, r.token);
        mount();
        refresh(true);
      }, function (err) {
        $("dk-unlock").disabled = false;
        $("dk-signin-msg").textContent = err.offline
          ? "The desk server at " + S.endpoint + " is not answering. Deploy it first (workers/desk/README.md)."
          : err.message;
      });
    });
    if (location.hash === "#desk") setTimeout(function () { var p = $("dk-pass"); if (p) p.focus(); }, 50);
  }

  /* ---- shell ---------------------------------------------------------- */
  var standalone = host.hasAttribute("data-standalone");
  var TITLES = {
    today: function () {
      var n = new Date();
      return ["Week " + isoWeek(n) + " · Today", n.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })];
    },
    board: function () { return ["Ideas · plans · goals · targets", "Board"]; },
    calendar: function () { return ["Google Calendar · tasks · deadlines", "Calendar"]; },
    notion: function () { return ["Notion", "Research OS"]; }
  };

  function mount() {
    host.hidden = false;
    host.className = "desk" + (standalone ? " desk--standalone" : "");
    host.innerHTML =
      '<div class="dk-app">' +
        '<aside class="dk-side" aria-label="Desk navigation">' +
          '<div class="dk-brand"><span class="dk-brand__mark" aria-hidden="true"><i class="fas fa-compass"></i></span>' +
            '<span class="dk-brand__text"><span class="dk-brand__title">Research Desk</span><span class="dk-brand__kicker">Physical Super Intelligence</span></span></div>' +
          '<nav class="dk-nav" role="tablist" aria-label="Desk views">' + VIEWS.map(function (v, i) {
            return '<button type="button" role="tab" class="dk-navi" data-view="' + v.id + '" title="' + v.label + ' (' + (i + 1) + ')">' +
              '<i class="fas ' + v.icon + '" aria-hidden="true"></i><span>' + v.label + '</span><span class="dk-navi__n" data-count="' + v.id + '"></span></button>';
          }).join("") + '</nav>' +
          '<div class="dk-minical" id="dk-minical"></div>' +
          '<div class="dk-side__foot">' +
            '<div class="dk-sync" id="dk-sync" role="status"></div>' +
            '<div class="dk-side__btns">' +
              '<button type="button" class="dk-icon" id="dk-settings" title="Settings and connections" aria-label="Settings"><i class="fas fa-cog" aria-hidden="true"></i></button>' +
              (standalone
                ? '<a class="dk-icon" href="/research-ideas/" title="Back to the site" aria-label="Back to the site"><i class="fas fa-arrow-left" aria-hidden="true"></i></a>'
                : '<button type="button" class="dk-icon" id="dk-focus" title="Full screen (F)" aria-label="Full screen" aria-pressed="false"><i class="fas fa-expand" aria-hidden="true"></i></button>' +
                  '<a class="dk-icon" href="/desk/" title="Open the desk on its own page" aria-label="Open the desk on its own page"><i class="fas fa-external-link-alt" aria-hidden="true"></i></a>' +
                  '<button type="button" class="dk-icon" id="dk-collapse" title="Minimise" aria-label="Minimise"><i class="fas fa-window-minimize" aria-hidden="true"></i></button>') +
            '</div>' +
          '</div>' +
        '</aside>' +
        '<section class="dk-main">' +
          '<header class="dk-top"><div class="dk-top__t"><span class="dk-top__k" id="dk-kicker"></span><h2 class="dk-top__h" id="dk-title"></h2></div>' +
            '<div class="dk-top__a">' +
              '<button type="button" class="dk-icon" id="dk-refresh" title="Refresh from Google and Notion (R)" aria-label="Refresh"><i class="fas fa-sync-alt" aria-hidden="true"></i></button>' +
              '<button type="button" class="dk-btn dk-btn--primary" id="dk-new" title="New entry (N)"><i class="fas fa-plus" aria-hidden="true"></i> New entry</button>' +
            '</div></header>' +
          '<div class="dk-body" id="dk-body"></div>' +
        '</section>' +
      '</div>' +
      '<button type="button" class="dk-strip" id="dk-strip" aria-label="Open the research desk">' +
        '<span class="dk-brand__mark" aria-hidden="true"><i class="fas fa-compass"></i></span>' +
        '<span class="dk-strip__t">Research Desk</span><span class="dk-strip__s" id="dk-strip-sum"></span>' +
        '<i class="fas fa-chevron-down" aria-hidden="true"></i></button>' +
      '<div class="dk-toast" id="dk-toast" role="status" aria-live="polite"></div>';

    if ($("dk-collapse")) $("dk-collapse").addEventListener("click", function () { S.ui.collapsed = true; S.ui.focus = false; saveUi(); render(); });
    $("dk-strip").addEventListener("click", function () { S.ui.collapsed = false; saveUi(); render(); });
    host.querySelector(".dk-nav").addEventListener("click", function (e) {
      var b = e.target.closest("[data-view]");
      if (b) setView(b.getAttribute("data-view"));
    });
    $("dk-minical").addEventListener("click", onMiniClick);
    $("dk-refresh").addEventListener("click", function () { refresh(false); });
    if ($("dk-focus")) $("dk-focus").addEventListener("click", toggleFocus);
    $("dk-settings").addEventListener("click", openSettings);
    $("dk-new").addEventListener("click", function () { Desk.editor.open(null); });
    $("dk-body").addEventListener("click", onBodyClick);
    $("dk-body").addEventListener("change", onBodyChange);
    $("dk-body").addEventListener("input", onBodyInput);
    $("dk-body").addEventListener("submit", onBodySubmit);
    render();
  }

  function setView(v) {
    if (!VIEWS.some(function (x) { return x.id === v; })) return;
    S.ui.view = v;
    S.ui.collapsed = false;
    saveUi();
    render();
    var body = $("dk-body");
    if (body) body.scrollTop = 0;
  }
  function toggleFocus() {
    if (standalone) return;
    S.ui.focus = !S.ui.focus;
    saveUi();
    render();
  }

  // Full screen lifts the desk out of the page: an ancestor with a transform
  // would otherwise turn position:fixed into "fixed to that ancestor".
  var homeMarker = null;
  function placeHost(full) {
    if (standalone) return;
    if (full && host.parentNode !== document.body) {
      homeMarker = homeMarker || document.createComment("desk");
      host.parentNode.insertBefore(homeMarker, host);
      document.body.appendChild(host);
    } else if (!full && homeMarker && homeMarker.parentNode && host.parentNode === document.body) {
      homeMarker.parentNode.insertBefore(host, homeMarker);
      host.scrollIntoView({ block: "start" });
    }
  }

  function render() {
    if (!S.token || !$("dk-body")) return;
    var collapsed = !standalone && !!S.ui.collapsed;
    var full = standalone || (!!S.ui.focus && !collapsed);
    placeHost(full);
    document.documentElement.classList.toggle("desk-focus", full);
    host.classList.toggle("is-collapsed", collapsed);
    host.classList.toggle("is-compact", S.ui.density === "compact");
    if ($("dk-focus")) {
      $("dk-focus").setAttribute("aria-pressed", String(!!S.ui.focus));
      $("dk-focus").innerHTML = '<i class="fas ' + (S.ui.focus ? "fa-compress" : "fa-expand") + '" aria-hidden="true"></i>';
    }
    host.querySelectorAll(".dk-navi").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.getAttribute("data-view") === S.ui.view));
    });
    var tt = TITLES[S.ui.view]();
    $("dk-kicker").textContent = tt[0];
    $("dk-title").textContent = tt[1];
    renderStatus();
    renderCounts();
    renderMini();
    $("dk-strip-sum").textContent = stripSummary();
    if (collapsed) return;
    var body = $("dk-body");
    if (S.ui.view === "today") {
      // A background refresh must not eat what is being typed into quick add.
      var q = $("dk-quick-text"), typed = q ? q.value : "", focused = q && document.activeElement === q, caret = q ? q.selectionStart : 0;
      body.innerHTML = viewToday();
      q = $("dk-quick-text");
      if (typed) q.value = typed;
      if (focused) { q.focus(); try { q.setSelectionRange(caret, caret); } catch (e) {} }
      paintQuickPreview();
    }
    else if (S.ui.view === "board") renderBoardInto(body);
    else if (S.ui.view === "calendar") Desk.calendar.render(body);
    else body.innerHTML = viewNotion();
  }

  function stripSummary() {
    var t = today(), b = C.bucketTasks(allTasks(), t);
    var next = deadlines().filter(function (d) { return !d.done && d.days >= 0; })[0];
    var bits = [];
    var open = b.overdue.length + b.today.length;
    bits.push(open ? plural(open, "task") + " due" : "no tasks due");
    if (next) bits.push("next deadline: " + next.title + ", " + C.countdown(next.days));
    return bits.join(" · ");
  }

  function renderStatus() {
    var el = $("dk-sync");
    if (!el) return;
    var btn = $("dk-refresh");
    if (btn) btn.classList.toggle("is-spinning", !!S.syncing);
    var g = S.sync && S.sync.google, n = S.sync && S.sync.notion;
    var at = S.sync && S.sync.at ? new Date(S.sync.at) : null;
    var dot = function (name, on, bad, title) {
      return '<span class="dk-dot' + (on ? " is-on" : "") + (bad ? " is-bad" : "") + '" title="' + esc(title) + '">' + name + '</span>';
    };
    el.innerHTML =
      '<span class="dk-sync__text' + (S.offline ? " is-bad" : "") + '">' +
        (S.syncing ? "Syncing…" : at ? (S.offline ? "Offline · " : "Synced ") + esc(hhmm(at)) : "Not synced yet") + '</span>' +
      '<span class="dk-sync__dots">' +
      dot("Calendar", g && g.ok, g && g.configured && !g.ok, g ? (g.ok ? "Google Calendar and Tasks connected" : g.configured ? "Google: " + (g.error || "error") : "Google not connected") : "Google") +
      dot("Notion", n && n.ok, n && n.configured && !n.ok, n ? (n.ok ? "Notion connected" : n.configured ? "Notion: " + (n.error || "every source failed") : "Notion not connected") : "Notion") +
      '</span>';
  }

  function renderCounts() {
    var t = today();
    var b = C.bucketTasks(allTasks(), t);
    var dl = deadlines().filter(function (d) { return !d.done && d.days >= 0 && d.days <= 7; }).length;
    var set = function (v, n) { var el = host.querySelector('[data-count="' + v + '"]'); if (el) el.textContent = n ? String(n) : ""; };
    set("today", b.overdue.length + b.today.length + dl);
    set("board", S.entries.filter(function (r) { return r.e.status !== "done" && r.e.status !== "parked"; }).length);
    var n = S.sync && S.sync.notion;
    set("notion", n && n.sources ? n.sources.reduce(function (k, s) { return k + (s.rows || []).filter(function (r) { return !r.done; }).length; }, 0) : 0);
    set("calendar", "");
  }

  // Month glance in the sidebar: a dot under each day that has a deadline or an event.
  var miniAnchor = new Date();
  function renderMini() {
    var el = $("dk-minical");
    if (!el) return;
    var first = new Date(miniAnchor.getFullYear(), miniAnchor.getMonth(), 1), start = C.startOfWeek(first), t = today();
    var marks = {};
    deadlines().forEach(function (d) {
      if (d.done) return;
      var rank = { past: 3, hot: 3, near: 2, far: 1 }[d.urgency] || 1;
      if (!marks[d.date] || marks[d.date] < rank) marks[d.date] = rank;
    });
    var busy = {};
    events().forEach(function (e) { if (!e.allDay) busy[C.ymd(e.start)] = true; });
    var dows = "";
    for (var j = 0; j < 7; j++) dows += '<span>' + C.addDays(start, j).toLocaleDateString(undefined, { weekday: "narrow" }) + '</span>';
    var cells = "";
    for (var i = 0; i < 42; i++) {
      var d = C.addDays(start, i), key = C.ymd(d);
      var mark = marks[key] ? ' data-mark="' + marks[key] + '"' : "";
      cells += '<button type="button" class="dk-mc' + (d.getMonth() !== first.getMonth() ? " is-out" : "") + (key === t ? " is-today" : "") + (busy[key] ? " is-busy" : "") + '"' + mark +
        ' data-miniday="' + key + '" aria-label="' + esc(d.toLocaleDateString(undefined, { day: "numeric", month: "long" })) + '">' + d.getDate() + '</button>';
    }
    el.innerHTML = '<div class="dk-minical__head"><button type="button" class="dk-icon dk-icon--sm" data-minishift="-1" aria-label="Previous month"><i class="fas fa-chevron-left" aria-hidden="true"></i></button>' +
      '<span>' + esc(first.toLocaleDateString(undefined, { month: "long", year: "numeric" })) + '</span>' +
      '<button type="button" class="dk-icon dk-icon--sm" data-minishift="1" aria-label="Next month"><i class="fas fa-chevron-right" aria-hidden="true"></i></button></div>' +
      '<div class="dk-minical__grid">' + dows.replace(/<span>/g, '<span class="dk-minical__dow">') + cells + '</div>';
  }
  function onMiniClick(e) {
    var b = e.target.closest("button");
    if (!b) return;
    var v = b.getAttribute("data-minishift");
    if (v) { miniAnchor = new Date(miniAnchor.getFullYear(), miniAnchor.getMonth() + (+v), 1); renderMini(); return; }
    v = b.getAttribute("data-miniday");
    if (v && Desk.calendar) { Desk.calendar.go(v, "day"); setView("calendar"); }
  }

  /* ---- shared derived data ------------------------------------------- */
  function deadlines() {
    return C.collectDeadlines({
      today: today(),
      entries: S.entries.map(function (r) { return r.e; }),
      notion: S.sync && S.sync.notion && S.sync.notion.sources,
      conferences: S.conferences,
      watched: S.prefs.data.watched
    });
  }
  function events() {
    var g = S.sync && S.sync.google;
    return ((g && g.events) || []).map(C.normEvent).filter(Boolean).sort(function (a, b) { return a.start - b.start; });
  }

  /* ---- Today ---------------------------------------------------------- */
  function viewToday() {
    var t = today();
    var modes = [["task", "Task", "fa-check-square"], ["event", "Event", "fa-calendar-plus"], ["idea", "Idea", "fa-lightbulb"]];
    var head =
      '<form class="dk-quick" id="dk-quick" autocomplete="off">' +
        '<div class="dk-quick__row">' +
          '<span class="dk-quick__icon" aria-hidden="true"><i class="fas fa-plus"></i></span>' +
          '<input type="text" id="dk-quick-text" class="dk-quick__input" placeholder="Add a task, event or idea · try “Draft rebuttal fri 14:00 #icra”" aria-label="Quick add">' +
          '<div class="dk-seg" role="group" aria-label="What to add">' + modes.map(function (m) {
            return '<button type="button" class="dk-seg__b" data-quick="' + m[0] + '" aria-pressed="' + (S.ui.quickMode === m[0]) + '"><i class="fas ' + m[2] + '" aria-hidden="true"></i> ' + m[1] + '</button>';
          }).join("") + '</div>' +
          '<button type="submit" class="dk-btn dk-btn--primary">Add</button>' +
        '</div>' +
        '<p class="dk-quick__preview" id="dk-quick-preview" aria-live="polite"></p>' +
      '</form>';
    return '<div class="dk-today">' + head + exportNudge() +
      '<div class="dk-today__grid">' + panelAgenda(t) + panelTasks(t) + panelDeadlines() + '</div>' +
      panelPinned() + '</div>';
  }

  function isoWeek(d) {
    var x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    var day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    var y0 = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    return Math.ceil(((x - y0) / 864e5 + 1) / 7);
  }

  function exportNudge() {
    var last = S.prefs.data.lastExportAt;
    var age = last ? (Date.now() - Date.parse(last)) / 864e5 : Infinity;
    if (age < 90 || S.entries.length === 0) return "";
    return '<div class="dk-nudge"><i class="fas fa-archive" aria-hidden="true"></i><span>' +
      (last ? "Last export " + Math.round(age) + " days ago." : "No export yet.") +
      ' A quarterly JSON export keeps the desk independent of any one service.</span>' +
      '<button type="button" class="dk-link" data-act="export">Export now</button></div>';
  }

  function connectCta(what) {
    return '<div class="dk-empty dk-empty--cta"><p>' + esc(what) + ' is not connected.</p>' +
      '<button type="button" class="dk-link" data-act="settings">How to connect</button></div>';
  }

  function eventRow(e, now, compact) {
    var past = !e.allDay && e.end < now;
    var when = e.allDay ? "All day" : hhmm(e.start) + "–" + hhmm(e.end);
    return '<li class="dk-ev' + (past ? " is-past" : "") + (compact ? " is-compact" : "") + '" style="--c:' + esc(e.color) + '">' +
      '<button type="button" class="dk-ev__b" data-event="' + esc(e.id) + '">' +
        '<span class="dk-ev__time">' + esc(when) + '</span>' +
        '<span class="dk-ev__title">' + esc(e.title) + '</span>' +
        (e.location ? '<span class="dk-ev__meta"><i class="fas fa-map-marker-alt" aria-hidden="true"></i> ' + esc(e.location) + '</span>' : "") +
      '</button>' +
      (safeUrl(e.video) && !past ? '<a class="dk-ev__join" href="' + esc(safeUrl(e.video)) + '" target="_blank" rel="noopener">Join</a>' : "") +
    '</li>';
  }

  function panelAgenda(t) {
    var g = S.sync && S.sync.google;
    var body;
    if (g && !g.configured) body = connectCta("Google Calendar");
    else if (g && !g.ok) body = '<div class="dk-empty is-bad"><p>' + esc(g.error || "Google failed.") + '</p></div>';
    else if (!S.sync) body = '<div class="dk-empty"><p>Waiting for the first sync…</p></div>';
    else {
      var now = new Date(), all = events();
      var todays = all.filter(function (e) { return C.eventOnDay(e, t); });
      var tom = C.ymd(C.addDays(now, 1));
      var tomorrows = all.filter(function (e) { return C.eventOnDay(e, tom); });
      var list = "", nowPlaced = false;
      todays.forEach(function (e) {
        if (!nowPlaced && !e.allDay && e.start > now) {
          list += '<li class="dk-now" aria-label="Now"><span>' + hhmm(now) + '</span></li>';
          nowPlaced = true;
        }
        list += eventRow(e, now);
      });
      if (!nowPlaced && todays.length) list += '<li class="dk-now"><span>' + hhmm(now) + '</span></li>';
      body = (todays.length ? '<ol class="dk-evs">' + list + '</ol>' : '<p class="dk-quiet">Nothing scheduled today.</p>') +
        '<h4 class="dk-sub">Tomorrow</h4>' +
        (tomorrows.length ? '<ol class="dk-evs">' + tomorrows.map(function (e) { return eventRow(e, now, true); }).join("") + '</ol>' : '<p class="dk-quiet">Free.</p>');
    }
    return '<section class="dk-panel dk-panel--agenda" aria-label="Agenda"><header class="dk-panel__head"><h3><i class="fas fa-clock" aria-hidden="true"></i> Agenda</h3>' +
      '<button type="button" class="dk-link" data-go="calendar">Calendar</button></header>' + body + '</section>';
  }

  function taskRow(task, t) {
    var due = task.due ? (task.due === t ? "" : C.countdown(C.dayDiff(t, task.due))) : "";
    var multi = S.sync && S.sync.google && (S.sync.google.tasklists || []).length > 1;
    return '<li class="dk-task' + (task.done ? " is-done" : "") + (task.parent ? " is-sub" : "") + '">' +
      '<label class="dk-check"><input type="checkbox" data-task="' + esc(task.key) + '"' + (task.done ? " checked" : "") + '>' +
      '<span class="dk-check__box" aria-hidden="true"></span><span class="dk-task__title">' + esc(task.title) + '</span></label>' +
      (task.time ? '<span class="dk-task__time">' + esc(task.time) + '</span>' : "") +
      (due ? '<span class="dk-task__due' + (task.due < t && !task.done ? " is-late" : "") + '">' + esc(due) + '</span>' : "") +
      ((multi && task.source === "google") || task.source === "desk" ? '<span class="dk-task__list">' + esc(task.list) + '</span>' : "") +
      (task.source === "desk" ? '<button type="button" class="dk-x" data-deltask="' + esc(task.id) + '" aria-label="Delete task"><i class="fas fa-times" aria-hidden="true"></i></button>' : "") +
    '</li>';
  }

  function panelTasks(t) {
    var b = C.bucketTasks(allTasks(), t);
    var soon = C.ymd(C.addDays(C.parseYmd(t), 7));
    var upcoming = b.upcoming.filter(function (x) { return x.due <= soon; });
    var later = b.upcoming.length - upcoming.length;
    var group = function (title, list, cls) {
      if (!list.length) return "";
      return '<h4 class="dk-sub ' + (cls || "") + '">' + title + ' <span>' + list.length + '</span></h4><ul class="dk-tasks">' +
        list.map(function (x) { return taskRow(x, t); }).join("") + '</ul>';
    };
    var g = S.sync && S.sync.google;
    var open = b.overdue.length + b.today.length + upcoming.length + b.undated.length;
    var html = group("Overdue", b.overdue, "is-late") + group("Today", b.today) + group("Next 7 days", upcoming) +
      (later ? '<p class="dk-quiet">' + plural(later, "more task") + ' after next week.</p>' : "") +
      group("No date", b.undated);
    if (!open) html = '<p class="dk-quiet">' + (g && !g.configured ? "No desk tasks. Add one above." : "Nothing open. Good.") + '</p>' + html;
    if (b.done.length) {
      html += '<button type="button" class="dk-link dk-link--sub" data-act="toggle-done">' + (S.ui.showDoneTasks ? "Hide" : "Show") + " " + plural(b.done.length, "finished task") + '</button>' +
        (S.ui.showDoneTasks ? '<ul class="dk-tasks">' + b.done.map(function (x) { return taskRow(x, t); }).join("") + '</ul>' : "");
    }
    var note = g && !g.configured ? '<p class="dk-hint">Tasks are kept on the desk until Google Tasks is connected.</p>' : "";
    return '<section class="dk-panel dk-panel--tasks" aria-label="Tasks"><header class="dk-panel__head"><h3><i class="fas fa-check-square" aria-hidden="true"></i> Tasks</h3>' +
      (g && g.ok ? '<a class="dk-link" href="https://calendar.google.com/calendar/u/0/r/tasks" target="_blank" rel="noopener">Google Tasks</a>' : "") +
      '</header>' + html + note + '</section>';
  }

  function deadlineRow(d) {
    var target = d.entryId ? 'data-entry="' + esc(d.entryId) + '"' : "";
    var href = safeUrl(d.url);
    var inner =
      '<span class="dk-cd dk-cd--' + d.urgency + '">' + esc(C.countdown(d.days)) + '</span>' +
      '<span class="dk-dl__main"><span class="dk-dl__title">' + esc(d.title) + '</span>' +
      '<span class="dk-dl__meta"><i class="dk-swatch" style="--c:' + esc(d.color) + '"></i>' + esc(d.source) +
      (d.status ? " · " + esc(d.status) : "") + ' · ' + esc(fmtDate(d.date, { weekday: "short", day: "numeric", month: "short" })) +
      (d.time ? " " + esc(d.time) + (d.tz ? " " + esc(d.tz) : "") : "") + '</span></span>';
    if (target) return '<li class="dk-dl"><button type="button" class="dk-dl__b" ' + target + '>' + inner + '</button></li>';
    if (href) return '<li class="dk-dl"><a class="dk-dl__b" href="' + esc(href) + '" target="_blank" rel="noopener">' + inner + '</a></li>';
    return '<li class="dk-dl"><span class="dk-dl__b">' + inner + '</span></li>';
  }

  function panelDeadlines() {
    var list = deadlines().filter(function (d) { return !d.done; });
    var groups = [
      ["Overdue", function (d) { return d.days < 0; }],
      ["This week", function (d) { return d.days >= 0 && d.days <= 7; }],
      ["This month", function (d) { return d.days > 7 && d.days <= 31; }],
      ["Later", function (d) { return d.days > 31; }]
    ];
    var html = groups.map(function (g) {
      var rows = list.filter(g[1]);
      if (!rows.length) return "";
      var shown = g[0] === "Later" ? rows.slice(0, 8) : rows;
      return '<h4 class="dk-sub' + (g[0] === "Overdue" ? " is-late" : "") + '">' + g[0] + ' <span>' + rows.length + '</span></h4>' +
        '<ul class="dk-dls">' + shown.map(deadlineRow).join("") + '</ul>' +
        (rows.length > shown.length ? '<p class="dk-quiet">' + (rows.length - shown.length) + ' more in the calendar.</p>' : "");
    }).join("");
    if (!html) html = '<p class="dk-quiet">No deadlines in the next four months.</p>';
    var n = S.sync && S.sync.notion;
    var errs = n && n.sources ? n.sources.filter(function (s) { return s.error; }) : [];
    if (errs.length) html += '<p class="dk-hint is-bad">Notion: ' + esc(errs.map(function (s) { return s.label; }).join(", ")) + ' could not be read. <button type="button" class="dk-link" data-go="notion">Details</button></p>';
    return '<section class="dk-panel dk-panel--deadlines" aria-label="Deadlines"><header class="dk-panel__head"><h3><i class="fas fa-flag-checkered" aria-hidden="true"></i> Deadlines</h3>' +
      '<a class="dk-link" href="/deadlines/">Conferences</a></header>' + html + '</section>';
  }

  function panelPinned() {
    var pinned = S.entries.filter(function (r) { return r.e.pinned; }).map(function (r) { return r.e; });
    var passages = [];
    S.entries.forEach(function (r) {
      C.RT_FIELDS.forEach(function (f) { pinsIn(r.e[f]).forEach(function (text) { passages.push({ id: r.id, title: r.e.title, field: C.RT_LABEL[f], text: text }); }); });
    });
    if (!pinned.length && !passages.length) return "";
    return '<section class="dk-pinned" aria-label="Pinned"><h3 class="dk-pinned__h"><i class="fas fa-thumbtack" aria-hidden="true"></i> Pinned</h3>' +
      '<div class="dk-pinned__grid">' + pinned.map(cardHtml).join("") +
      passages.map(function (p) {
        return '<button type="button" class="dk-quote" data-entry="' + esc(p.id) + '"><span class="dk-quote__text">' + esc(p.text) + '</span>' +
          '<span class="dk-quote__src">' + esc(p.field) + ' · ' + esc(p.title) + '</span></button>';
      }).join("") + '</div></section>';
  }

  /* ---- quick add ------------------------------------------------------ */
  function paintQuickPreview() {
    var inp = $("dk-quick-text"), out = $("dk-quick-preview");
    if (!inp || !out) return;
    var v = inp.value.trim();
    if (!v) { out.innerHTML = '<span class="dk-quiet">Dates: today, tomorrow, fri, next mon, 3/2, nov 20, in 2w, 2026-11-16 · times: 14:00, 2pm, 10-11:30 · #tags</span>'; return; }
    var p = C.parseQuick(v), mode = S.ui.quickMode;
    var bits = [mode === "task" ? (googleReady() ? "Google task" : "Desk task") : mode === "event" ? (googleReady() ? "Calendar event" : "Opens Google Calendar") : "Board idea"];
    bits.push("“" + (p.title || v) + "”");
    if (p.date) bits.push(fmtDate(p.date, { weekday: "short", day: "numeric", month: "short" }));
    else if (mode === "event") bits.push("today");
    if (p.start) bits.push(p.start + (p.end ? "–" + p.end : ""));
    else if (mode === "event") bits.push("all day");
    if (p.tags.length) bits.push(p.tags.map(function (x) { return "#" + x; }).join(" "));
    out.textContent = bits.join(" · ");
  }

  function quickAdd() {
    var inp = $("dk-quick-text");
    var raw = inp.value.trim();
    if (!raw) { inp.focus(); return; }
    var p = C.parseQuick(raw), mode = S.ui.quickMode, title = p.title || raw;
    var done = function (msg, opts) { inp.value = ""; paintQuickPreview(); toast(msg, opts); };
    if (mode === "idea") {
      var id = newId("e");
      saveEntry(id, entryData(C.normaliseEntry(id, { title: title, tags: p.tags, deadline: p.date }))).then(function () {
        done("Idea added to the board.", { action: "Open", onAction: function () { Desk.editor.open(id); } });
      }, function (err) { failed(err, "Not saved"); });
      return;
    }
    if (mode === "event") {
      var ev = { title: title, date: p.date || today(), start: p.start, end: p.end || "", allDay: !p.start, tz: tz() };
      if (!googleReady()) {
        window.open(C.gcalTemplateUrl(ev), "_blank", "noopener");
        done("Opened Google Calendar with the event filled in.");
        return;
      }
      api("POST", "/google", { action: "createEvent", title: ev.title, date: ev.date, start: ev.start, end: ev.end, allDay: ev.allDay, tz: ev.tz })
        .then(function () { done("Event added to Google Calendar."); refresh(true); }, function (err) { failed(err, "Google Calendar"); });
      return;
    }
    if (googleReady()) {
      api("POST", "/google", { action: "createTask", title: title, due: p.date, notes: p.start ? "At " + p.start + (p.end ? "–" + p.end : "") : "" }).then(function (r) {
        S.sync.google.tasks.push(r.task);
        persist();
        done("Task added to Google Tasks.");
        render();
      }, function (err) { failed(err, "Google Tasks"); });
      return;
    }
    var tid = newId("t");
    saveDeskTask(tid, { title: title, due: p.date, time: p.start, done: false, createdAt: new Date().toISOString(), tags: p.tags })
      .then(function () { done("Task added."); }, function (err) { failed(err, "Task not saved"); });
  }

  /* ---- Board ---------------------------------------------------------- */
  function cardHtml(e) {
    var ax = C.byId(C.AXES, e.axis), kind = C.byId(C.KINDS, e.kind), st = C.byId(C.STATUSES, e.status);
    var dots = "";
    for (var i = 1; i <= 5; i++) dots += '<i class="' + (i <= e.conviction ? "is-on" : "") + '"></i>';
    var due = "";
    if (C.isYmd(e.deadline)) {
      var days = C.dayDiff(today(), e.deadline);
      due = '<span class="dk-cd dk-cd--' + (e.status === "done" ? "done" : C.urgency(days)) + '" title="' + esc(fmtDate(e.deadline, { day: "numeric", month: "short", year: "numeric" })) + '">' + esc(C.countdown(days)) + '</span>';
    }
    var thesis = plain(e.thesis);
    return '<article class="dk-card' + (e.pinned ? " is-pinned" : "") + (e.status === "done" || e.status === "parked" ? " is-quiet" : "") + '" style="--ax:' + ax.color + '">' +
      '<button type="button" class="dk-card__open" data-entry="' + esc(e.id) + '" aria-label="Open ' + esc(e.title || "entry") + '"></button>' +
      '<header class="dk-card__head"><span class="dk-kind">' + esc(kind.label) + '</span>' +
        '<span class="dk-st dk-st--' + esc(e.status) + '">' + esc(st.label) + '</span>' + due +
        '<button type="button" class="dk-pin' + (e.pinned ? " is-on" : "") + '" data-pin="' + esc(e.id) + '" aria-pressed="' + e.pinned + '" title="' + (e.pinned ? "Unpin" : "Pin to Today") + '"><i class="fas fa-thumbtack" aria-hidden="true"></i></button>' +
      '</header>' +
      '<h3 class="dk-card__title">' + esc(e.title || "Untitled") + '</h3>' +
      (thesis ? '<p class="dk-card__thesis">' + esc(thesis.slice(0, 420)) + '</p>' : "") +
      '<footer class="dk-card__meta"><span class="dk-axis"><i class="dk-swatch" style="--c:' + ax.color + '"></i>' + esc(ax.label) + '</span>' +
        '<span class="dk-conv" title="Conviction ' + e.conviction + ' of 5">' + dots + '</span>' +
        (e.venue ? '<span class="dk-venue">' + esc(e.venue) + '</span>' : "") +
        e.tags.slice(0, 4).map(function (t) { return '<span class="dk-tag">#' + esc(t) + '</span>'; }).join("") +
        (safeUrl(e.notionUrl) ? '<a class="dk-ext" href="' + esc(safeUrl(e.notionUrl)) + '" target="_blank" rel="noopener" title="Open in Notion"><i class="fas fa-database" aria-hidden="true"></i></a>' : "") +
        (e.images.length ? '<span class="dk-tag" title="Images"><i class="fas fa-image" aria-hidden="true"></i> ' + e.images.length + '</span>' : "") +
      '</footer></article>';
  }

  function boardRows() {
    var f = S.ui.board, q = f.q.trim().toLowerCase();
    var rows = S.entries.map(function (r) { return r.e; }).filter(function (e) {
      if (f.kind !== "all" && e.kind !== f.kind) return false;
      if (f.axis !== "all" && e.axis !== f.axis) return false;
      if (f.status === "open" && (e.status === "done" || e.status === "parked")) return false;
      if (f.status !== "open" && f.status !== "all" && e.status !== f.status) return false;
      if (!q) return true;
      var hay = [e.title, e.venue, e.sourceLabel, e.tags.join(" "), plain(e.thesis), plain(e.gap), plain(e.experiment), plain(e.risk)].join(" ").toLowerCase();
      return hay.indexOf(q) !== -1;
    });
    rows.sort(function (a, b) {
      if (f.sort === "pinned" && a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      if (f.sort === "conviction" && a.conviction !== b.conviction) return b.conviction - a.conviction;
      if (f.sort === "deadline") {
        var da = a.deadline || "9999", db = b.deadline || "9999";
        if (da !== db) return da < db ? -1 : 1;
      }
      if (f.sort === "title") return a.title.localeCompare(b.title);
      return String(b.updatedAt || b.addedAt).localeCompare(String(a.updatedAt || a.addedAt));
    });
    return rows;
  }

  function renderBoardInto(body) {
    var f = S.ui.board;
    // Keep the search box (and its caret) alive while typing; only redraw results.
    if (!$("dk-board-results")) {
      body.innerHTML = '<div class="dk-board">' +
        '<div class="dk-tools">' +
          '<label class="dk-search"><i class="fas fa-search" aria-hidden="true"></i><input type="search" id="dk-q" placeholder="Search titles, notes, tags (/)" value="' + esc(f.q) + '" aria-label="Search the board"></label>' +
          '<select class="dk-select" id="dk-f-kind" aria-label="Type"><option value="all">All types</option>' + C.KINDS.map(function (k) { return '<option value="' + k.id + '">' + esc(k.label) + '</option>'; }).join("") + '</select>' +
          '<select class="dk-select" id="dk-f-status" aria-label="Status"><option value="open">Open</option><option value="all">Any status</option>' + C.STATUSES.map(function (s) { return '<option value="' + s.id + '">' + esc(s.label) + '</option>'; }).join("") + '</select>' +
          '<select class="dk-select" id="dk-f-sort" aria-label="Sort"><option value="pinned">Pinned first</option><option value="updated">Recently changed</option><option value="deadline">Nearest deadline</option><option value="conviction">Conviction</option><option value="title">Title</option></select>' +
          '<div class="dk-seg" role="group" aria-label="Layout"><button type="button" class="dk-seg__b" data-layout="cards" title="Cards"><i class="fas fa-th-large" aria-hidden="true"></i></button><button type="button" class="dk-seg__b" data-layout="lanes" title="Lanes by status"><i class="fas fa-columns" aria-hidden="true"></i></button></div>' +
        '</div>' +
        '<div class="dk-chips" role="group" aria-label="Axis"><button type="button" class="dk-chip" data-axis="all">All axes</button>' +
          C.AXES.map(function (a) { return '<button type="button" class="dk-chip" data-axis="' + a.id + '"><i class="dk-swatch" style="--c:' + a.color + '"></i>' + esc(a.label) + '</button>'; }).join("") + '</div>' +
        '<div id="dk-board-results"></div></div>';
    }
    $("dk-f-kind").value = f.kind; $("dk-f-status").value = f.status; $("dk-f-sort").value = f.sort;
    body.querySelectorAll("[data-layout]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-layout") === f.layout)); });
    body.querySelectorAll(".dk-chip[data-axis]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-axis") === f.axis)); });
    var rows = boardRows(), out = $("dk-board-results");
    if (!S.entries.length) { out.innerHTML = '<div class="dk-empty"><p>The board is empty.</p><p>Press <b>New</b>, or use quick add on Today with <b>Idea</b> selected.</p></div>'; return; }
    if (f.layout === "lanes") { out.innerHTML = lanesHtml(rows); return; }
    out.innerHTML = rows.length ? '<div class="dk-cards">' + rows.map(cardHtml).join("") + '</div>' : '<div class="dk-empty"><p>Nothing matches these filters.</p></div>';
  }

  function lanesHtml(rows) {
    var statuses = S.ui.board.status === "open" ? C.STATUSES.filter(function (s) { return s.id !== "done" && s.id !== "parked"; }) : C.STATUSES;
    return '<div class="dk-lanes">' + statuses.map(function (s) {
      var lane = rows.filter(function (e) { return e.status === s.id; });
      return '<section class="dk-lane" data-lane="' + s.id + '"><h4 class="dk-lane__h">' + esc(s.label) + ' <span>' + lane.length + '</span></h4>' +
        lane.map(function (e) {
          var ax = C.byId(C.AXES, e.axis);
          return '<div class="dk-mini" draggable="true" data-drag="' + esc(e.id) + '" style="--ax:' + ax.color + '"><button type="button" class="dk-mini__b" data-entry="' + esc(e.id) + '">' +
            '<b>' + esc(e.title || "Untitled") + '</b><span>' + esc(C.byId(C.KINDS, e.kind).label) + (e.deadline ? " · " + esc(C.countdown(C.dayDiff(today(), e.deadline))) : "") + '</span></button></div>';
        }).join("") + '</section>';
    }).join("") + '</div>';
  }

  function wireLanes() {
    var dragId = null;
    host.addEventListener("dragstart", function (e) {
      var m = e.target.closest && e.target.closest("[data-drag]");
      if (!m) return;
      dragId = m.getAttribute("data-drag");
      try { e.dataTransfer.setData("text/plain", dragId); e.dataTransfer.effectAllowed = "move"; } catch (err) {}
    });
    host.addEventListener("dragover", function (e) {
      var lane = e.target.closest && e.target.closest("[data-lane]");
      if (!lane) return;
      e.preventDefault();
      host.querySelectorAll(".dk-lane.is-over").forEach(function (l) { if (l !== lane) l.classList.remove("is-over"); });
      lane.classList.add("is-over");
    });
    host.addEventListener("drop", function (e) {
      var lane = e.target.closest && e.target.closest("[data-lane]");
      if (!lane || !dragId) return;
      e.preventDefault();
      lane.classList.remove("is-over");
      var rec = entryDoc(dragId), to = lane.getAttribute("data-lane");
      dragId = null;
      if (rec && rec.e.status !== to) { rec.e.status = to; render(); patchEntry(rec.id, { status: to }); }
    });
  }

  /* ---- Notion --------------------------------------------------------- */
  function viewNotion() {
    var n = S.sync && S.sync.notion;
    var home = safeUrl(S.prefs.data.notionHome);
    var head = '<div class="dk-tools dk-tools--notion"><p class="dk-hint">Dated rows from Research OS, read on every refresh. Edit them in Notion; send board entries there from the editor.</p>' +
      '<label class="dk-toggle"><input type="checkbox" id="dk-n-hide"' + (S.ui.notionHideDone ? " checked" : "") + '> Hide finished</label>' +
      (home ? '<a class="dk-btn" href="' + esc(home) + '" target="_blank" rel="noopener"><i class="fas fa-external-link-alt" aria-hidden="true"></i> Open Research OS</a>' : "") + '</div>';
    if (!n) return head + '<div class="dk-empty"><p>Waiting for the first sync…</p></div>';
    if (!n.configured) return head + connectCta("Notion");
    var t = today();
    return head + '<div class="dk-nsources">' + (n.sources || []).map(function (src) {
      var rows = (src.rows || []).filter(function (r) { return !(S.ui.notionHideDone && r.done); });
      var color = C.SOURCE_COLORS[src.label] || "#475569";
      var body = src.error ? '<p class="dk-hint is-bad">' + esc(src.error) + '</p>' :
        rows.length ? '<ul class="dk-nrows">' + rows.map(function (r) {
          var d = String(r.date || "").slice(0, 10), days = C.isYmd(d) ? C.dayDiff(t, d) : null;
          return '<li class="dk-nrow' + (r.done ? " is-done" : "") + '">' +
            (days === null ? "" : '<span class="dk-cd dk-cd--' + (r.done ? "done" : C.urgency(days)) + '">' + esc(C.countdown(days)) + '</span>') +
            (safeUrl(r.url) ? '<a class="dk-nrow__t" href="' + esc(safeUrl(r.url)) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a>' : '<span class="dk-nrow__t">' + esc(r.title) + '</span>') +
            (r.status ? '<span class="dk-st">' + esc(r.status) + '</span>' : "") +
            '<span class="dk-nrow__d">' + esc(fmtDate(d, { day: "numeric", month: "short", year: "numeric" })) + '</span></li>';
        }).join("") + '</ul>' : '<p class="dk-quiet">Nothing dated in the next four months.</p>';
      return '<section class="dk-nsource" style="--c:' + color + '"><h4 class="dk-nsource__h"><i class="dk-swatch" style="--c:' + color + '"></i>' + esc(src.label) +
        ' <span>' + rows.length + '</span></h4>' + body + '</section>';
    }).join("") + '</div>';
  }

  /* ---- event delegation ---------------------------------------------- */
  function onBodyClick(e) {
    var t = e.target.closest("button, a");
    if (!t) return;
    var v;
    if ((v = t.getAttribute("data-entry"))) { Desk.editor.open(v); return; }
    if ((v = t.getAttribute("data-pin"))) { var r = entryDoc(v); if (r) { r.e.pinned = !r.e.pinned; render(); patchEntry(v, { pinned: r.e.pinned }); } return; }
    if ((v = t.getAttribute("data-event"))) { openEvent(v); return; }
    if ((v = t.getAttribute("data-go"))) { setView(v); return; }
    if ((v = t.getAttribute("data-quick"))) { S.ui.quickMode = v; saveUi(); host.querySelectorAll("[data-quick]").forEach(function (b) { b.setAttribute("aria-pressed", String(b === t)); }); paintQuickPreview(); $("dk-quick-text").focus(); return; }
    if ((v = t.getAttribute("data-deltask"))) { deleteDeskTask(v); return; }
    if ((v = t.getAttribute("data-layout"))) { S.ui.board.layout = v; saveUi(); render(); return; }
    if ((v = t.getAttribute("data-axis"))) { S.ui.board.axis = v; saveUi(); render(); return; }
    if ((v = t.getAttribute("data-act"))) {
      if (v === "settings") openSettings();
      else if (v === "export") exportJson();
      else if (v === "toggle-done") { S.ui.showDoneTasks = !S.ui.showDoneTasks; saveUi(); render(); }
    }
  }
  function onBodyChange(e) {
    var t = e.target;
    if (t.matches("input[data-task]")) { toggleTask(t.getAttribute("data-task"), t.checked); return; }
    if (t.id === "dk-f-kind") { S.ui.board.kind = t.value; saveUi(); render(); }
    else if (t.id === "dk-f-status") { S.ui.board.status = t.value; saveUi(); render(); }
    else if (t.id === "dk-f-sort") { S.ui.board.sort = t.value; saveUi(); render(); }
    else if (t.id === "dk-n-hide") { S.ui.notionHideDone = t.checked; saveUi(); render(); }
  }
  function onBodyInput(e) {
    if (e.target.id === "dk-q") { S.ui.board.q = e.target.value; render(); }
    else if (e.target.id === "dk-quick-text") paintQuickPreview();
  }
  function onBodySubmit(e) {
    if (e.target.id === "dk-quick") { e.preventDefault(); quickAdd(); }
  }

  /* ---- dialogs: event detail and settings ----------------------------- */
  function dialog(id, title, bodyHtml, footHtml) {
    var d = $(id);
    if (!d) {
      d = document.createElement("dialog");
      d.id = id;
      d.className = "dk-dialog";
      document.body.appendChild(d);
      d.addEventListener("click", function (e) { if (e.target === d) d.close(); });
    }
    d.innerHTML = '<div class="dk-dialog__in"><header class="dk-dialog__head"><h3>' + esc(title) + '</h3>' +
      '<button type="button" class="dk-icon" data-close aria-label="Close"><i class="fas fa-times" aria-hidden="true"></i></button></header>' +
      '<div class="dk-dialog__body">' + bodyHtml + '</div>' + (footHtml ? '<footer class="dk-dialog__foot">' + footHtml + '</footer>' : "") + '</div>';
    d.querySelector("[data-close]").addEventListener("click", function () { d.close(); });
    if (!d.open) d.showModal();
    return d;
  }

  function openEvent(id) {
    var e = events().filter(function (x) { return x.id === id; })[0];
    if (!e && Desk.calendar) e = Desk.calendar.findEvent(id);
    if (!e) return;
    var when = e.start.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }) +
      (e.allDay ? " · all day" : " · " + hhmm(e.start) + "–" + hhmm(e.end));
    var rows = [["When", esc(when)], ["Calendar", esc(e.calendar)]];
    if (e.location) rows.push(["Where", esc(e.location)]);
    if (e.attendees) rows.push(["Guests", String(e.attendees)]);
    if (safeUrl(e.video)) rows.push(["Call", '<a href="' + esc(safeUrl(e.video)) + '" target="_blank" rel="noopener">Join the call</a>']);
    if (e.description) rows.push(["Notes", '<span class="dk-pre">' + esc(e.description) + '</span>']);
    dialog("dk-event", e.title, '<dl class="dk-kv">' + rows.map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + r[1] + "</dd>"; }).join("") + '</dl>',
      safeUrl(e.link) ? '<a class="dk-btn" href="' + esc(safeUrl(e.link)) + '" target="_blank" rel="noopener">Open in Google Calendar</a>' : "");
  }

  function openSettings() {
    var h = S.health || {}, cfg = h.configured || {}, g = S.sync && S.sync.google, n = S.sync && S.sync.notion;
    var line = function (ok, label, detail) {
      return '<li class="dk-conn' + (ok === true ? " is-on" : ok === false ? " is-bad" : "") + '"><i class="dk-dot is-on' + (ok === false ? " is-bad" : "") + '"></i><b>' + esc(label) + '</b><span>' + detail + '</span></li>';
    };
    var names = [];
    S.conferences.forEach(function (c) { if (names.indexOf(c.name) === -1) names.push(c.name); });
    names.sort();
    var watched = S.prefs.data.watched || [];
    var body =
      '<section class="dk-set"><h4>Connections</h4><ul class="dk-conns">' +
        line(true, "Desk server", esc(S.endpoint) + (h.version ? " · v" + esc(h.version) : "")) +
        line(g && g.ok ? true : cfg.google || (g && g.configured) ? false : null, "Google Calendar + Tasks",
          g && g.ok ? plural((g.calendars || []).length, "calendar") + ", " + plural((g.tasklists || []).length, "task list") + (g.warnings && g.warnings.length ? " · " + esc(g.warnings.join("; ")) : "")
            : g && g.configured ? esc(g.error || "failing") : "Not connected. Deploy the Apps Script bridge, then set GOOGLE_BRIDGE_URL and GOOGLE_BRIDGE_SECRET.") +
        line(n && n.ok ? true : n && n.configured ? false : null, "Notion Research OS",
          n && n.configured ? (n.sources || []).map(function (s) { return esc(s.label) + (s.error ? " (failing)" : " (" + s.rows.length + ")"); }).join(", ")
            : "Not connected. Create an internal integration, share Research OS with it, set NOTION_TOKEN.") +
      '</ul><p class="dk-hint"><a href="' + README + '" target="_blank" rel="noopener">Step-by-step setup</a> · Refresh after changing a setting in Cloudflare.</p></section>' +
      '<section class="dk-set"><h4>Conference deadlines on the desk</h4><div class="dk-chips" id="dk-watch">' + names.map(function (nm) {
        return '<button type="button" class="dk-chip" data-watch="' + esc(nm) + '" aria-pressed="' + (watched.indexOf(nm) !== -1) + '">' + esc(nm) + '</button>';
      }).join("") + '</div></section>' +
      '<section class="dk-set"><h4>Research OS link</h4><div class="dk-row"><input type="url" class="dk-input" id="dk-notion-home" placeholder="https://www.notion.so/…" value="' + esc(S.prefs.data.notionHome || "") + '">' +
        '<button type="button" class="dk-btn" id="dk-notion-home-save">Save</button></div></section>' +
      '<section class="dk-set"><h4>Display on this device</h4><div class="dk-row">' +
        '<label class="dk-toggle"><input type="checkbox" id="dk-compact"' + (S.ui.density === "compact" ? " checked" : "") + '> Compact</label>' +
        '<label class="dk-toggle"><input type="checkbox" id="dk-focus-default"' + (S.ui.focus ? " checked" : "") + '> Full screen</label></div></section>' +
      '<section class="dk-set"><h4>Your data</h4><p class="dk-hint">Every save keeps a revision on the server. Export a JSON copy each quarter' +
        (S.prefs.data.lastExportAt ? " (last: " + esc(fmtDate(S.prefs.data.lastExportAt.slice(0, 10), { day: "numeric", month: "short", year: "numeric" })) + ")" : "") + '.</p>' +
        '<div class="dk-row"><button type="button" class="dk-btn" id="dk-export"><i class="fas fa-download" aria-hidden="true"></i> Export JSON</button>' +
        '<label class="dk-btn dk-file"><i class="fas fa-upload" aria-hidden="true"></i> Import JSON<input type="file" id="dk-import" accept="application/json,.json" hidden></label></div>' +
        '<p class="dk-hint" id="dk-import-msg" role="status"></p></section>' +
      '<section class="dk-set"><h4>Keyboard</h4><p class="dk-hint"><kbd>1</kbd>–<kbd>4</kbd> views · <kbd>N</kbd> new entry · <kbd>T</kbd> quick add · <kbd>/</kbd> search · <kbd>R</kbd> refresh · <kbd>F</kbd> full screen · <kbd>[</kbd> <kbd>]</kbd> move the calendar · <kbd>Ctrl</kbd>+<kbd>S</kbd> save in the editor</p></section>';
    var d = dialog("dk-settings-d", "Desk settings", body, '<button type="button" class="dk-btn dk-btn--danger" id="dk-signout"><i class="fas fa-sign-out-alt" aria-hidden="true"></i> Sign out on this device</button>');
    d.querySelector("#dk-watch").addEventListener("click", function (e) {
      var b = e.target.closest("[data-watch]");
      if (!b) return;
      var nm = b.getAttribute("data-watch"), list = (S.prefs.data.watched || []).slice(), i = list.indexOf(nm);
      if (i === -1) list.push(nm); else list.splice(i, 1);
      b.setAttribute("aria-pressed", String(i === -1));
      savePrefs({ watched: list });
    });
    d.querySelector("#dk-notion-home-save").addEventListener("click", function () {
      var v = d.querySelector("#dk-notion-home").value.trim();
      if (v && !safeUrl(v)) { toast("Use a full https:// link.", { error: true }); return; }
      savePrefs({ notionHome: v }).then(function () { toast("Saved."); });
    });
    d.querySelector("#dk-compact").addEventListener("change", function (e) { S.ui.density = e.target.checked ? "compact" : "comfy"; saveUi(); render(); });
    d.querySelector("#dk-focus-default").addEventListener("change", function (e) { S.ui.focus = e.target.checked; saveUi(); render(); });
    d.querySelector("#dk-export").addEventListener("click", exportJson);
    d.querySelector("#dk-import").addEventListener("change", importJson);
    d.querySelector("#dk-signout").addEventListener("click", function () { d.close(); signOut("Signed out on this device."); });
    api("GET", "/health").then(function (r) { S.health = r; }, function () {});
  }

  function exportJson() {
    api("GET", "/export?images=1").then(function (r) {
      var blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "research_desk_" + today().replace(/-/g, "_") + ".json";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
      savePrefs({ lastExportAt: new Date().toISOString() });
      toast("Exported " + Object.keys(r.docs).reduce(function (n, k) { return n + r.docs[k].length; }, 0) + " documents.");
    }, function (err) { failed(err, "Export failed"); });
  }

  function importJson(e) {
    var file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    var msg = $("dk-import-msg");
    file.text().then(function (text) {
      var data = JSON.parse(text);
      var docs = data.docs;
      var list = [];
      if (Array.isArray(docs)) list = docs;
      else if (docs) Object.keys(docs).forEach(function (c) { (docs[c] || []).forEach(function (r) { list.push({ collection: c, id: r.id, data: r.data }); }); });
      if (!list.length) throw new Error("No documents in that file.");
      var chunks = [];
      for (var i = 0; i < list.length; i += 200) chunks.push(list.slice(i, i + 200));
      var total = { written: 0, unchanged: 0, skipped: 0 };
      return chunks.reduce(function (p, chunk) {
        return p.then(function () {
          return api("POST", "/import", { docs: chunk }).then(function (r) { total.written += r.written; total.unchanged += r.unchanged; total.skipped += r.skipped.length; });
        });
      }, Promise.resolve()).then(function () {
        msg.textContent = "Imported " + total.written + ", unchanged " + total.unchanged + (total.skipped ? ", skipped " + total.skipped : "") + ".";
        return refresh(true);
      });
    }).catch(function (err) { msg.textContent = "Import failed: " + (err && err.message ? err.message : "unreadable file."); });
  }

  /* ---- keyboard ------------------------------------------------------- */
  function onKey(e) {
    if (!S.token || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable) return;
    if (document.querySelector("dialog[open]")) return;
    var k = e.key;
    if (k >= "1" && k <= "4") { setView(VIEWS[+k - 1].id); e.preventDefault(); }
    else if (k === "n") { Desk.editor.open(null); e.preventDefault(); }
    else if (k === "r") { refresh(false); e.preventDefault(); }
    else if (k === "f") { toggleFocus(); e.preventDefault(); }
    else if (k === "t") { setView("today"); setTimeout(function () { var q = $("dk-quick-text"); if (q) q.focus(); }, 0); e.preventDefault(); }
    else if (k === "/") { setView("board"); setTimeout(function () { var q = $("dk-q"); if (q) q.focus(); }, 0); e.preventDefault(); }
    else if ((k === "[" || k === "]") && S.ui.view === "calendar") { Desk.calendar.shift(k === "]" ? 1 : -1); e.preventDefault(); }
    else if (k === "Escape" && S.ui.focus && !standalone) { toggleFocus(); }
  }

  /* ---- boot ----------------------------------------------------------- */
  Desk.app = {
    S: S, api: api, esc: esc, safeUrl: safeUrl, sanitize: sanitize, plain: plain, toast: toast, failed: failed, render: render,
    today: today, tz: tz, hhmm: hhmm, fmtDate: fmtDate, newId: newId, dialog: dialog, deadlines: deadlines, events: events,
    allTasks: allTasks, entryDoc: entryDoc, entryData: entryData, saveEntry: saveEntry, deleteEntry: deleteEntry,
    googleReady: googleReady, notionReady: notionReady, fetchSync: fetchSync, syncQuery: syncQuery, openEvent: openEvent,
    toggleTask: toggleTask, refresh: refresh, cardHtml: cardHtml
  };

  function boot() {
    // Public conference dates for the watched-venue deadlines; fetched, not inlined,
    // so visitors to the page never download them.
    var confUrl = host.getAttribute("data-conferences");
    if (confUrl) fetch(confUrl).then(function (r) { return r.json(); }).then(function (list) {
      S.conferences = Array.isArray(list) ? list : [];
      render();
    }, function () {});
    var ui = load(KEY.ui);
    if (ui) { S.ui = Object.assign(S.ui, ui); S.ui.board = Object.assign({}, S.ui.board, ui.board || {}); }
    S.token = load(KEY.token) || "";
    if (!S.endpoint) { host.hidden = false; host.innerHTML = '<p class="dk-empty">The desk endpoint is not set in _config.yml (desk.endpoint).</p>'; return; }
    document.addEventListener("keydown", onKey);
    wireLanes();
    api("GET", "/health").then(function (r) { S.health = r; }, function () {});
    if (!S.token) { renderSignIn(""); return; }
    var cache = load(KEY.cache);
    if (cache) {
      S.entries = cache.entries || [];
      S.deskTasks = cache.deskTasks || [];
      if (cache.prefs) S.prefs = cache.prefs;
      S.sync = cache.sync || null;
    }
    mount();
    refresh(true);
    setInterval(function () {
      if (document.visibilityState === "visible" && !S.ui.collapsed && S.token) refresh(true);
    }, AUTO_REFRESH_MS);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState !== "visible" || !S.token || !S.sync) return;
      if (Date.now() - Date.parse(S.sync.at) > 2 * 60e3) refresh(true);
    });
    if (location.hash === "#desk" && !standalone) host.scrollIntoView({ block: "start" });
  }
  boot();
})();
