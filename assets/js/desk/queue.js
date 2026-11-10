/* ==========================================================================
   Research desk - offline write queue. When the backend cannot be reached, a
   write is kept on this device and answered as if it had succeeded; it is
   sent when the connection is back. Puts carry the baseVersion the device
   last saw, so the server still refuses to overwrite a newer copy; a refused
   put is kept as a separate "(offline copy)" document rather than lost.
   Uses Desk.app at call time, so it can load before app.js.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var KEY = "desk.queue.v1";
  // Actions that can wait. Reads, auth, images and imports cannot.
  var QUEUEABLE = { put: 1, "delete": 1, setTask: 1, createTask: 1, createEvent: 1, updateEvent: 1 };

  var Q = { items: load(), replaying: false };

  function load() {
    try { var r = localStorage.getItem(KEY), l = r ? JSON.parse(r) : []; return Array.isArray(l) ? l : []; } catch (e) { return []; }
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(Q.items)); } catch (e) {} }
  function size() { return Q.items.length; }
  function clear() { Q.items = []; save(); }

  function add(action, payload) {
    var item = { action: action, payload: payload || {}, at: new Date().toISOString() };
    Q.items = C.queueAdd(Q.items, item);
    save();
    return item;
  }

  // The answer the caller would have had from the server, so the page carries
  // on; `pending` marks what has not reached the server yet.
  function synth(action, payload) {
    var p = payload || {}, now = new Date().toISOString();
    if (action === "put") {
      return { ok: true, queued: true, doc: { collection: p.collection, id: p.id, version: Number(p.baseVersion) || 0, updatedAt: now, deleted: false, data: p.data, pending: true } };
    }
    if (action === "delete") {
      return { ok: true, queued: true, doc: { collection: p.collection, id: p.id, version: Number(p.base) || 0, updatedAt: now, deleted: true, data: {}, pending: true } };
    }
    if (action === "createTask") {
      return { ok: true, queued: true, task: { id: "pending-" + Date.now().toString(36), listId: p.listId || "@default", list: "", title: p.title || "Untitled",
        notes: p.notes || "", due: p.due || "", done: false, completed: "", link: "", parent: "", pending: true } };
    }
    if (action === "createEvent") return { ok: true, queued: true, event: null, repeat: "" };
    return { ok: true, queued: true };
  }

  function shift() { Q.items.shift(); save(); }

  // A put the server refused: its copy wins on the page, and the offline text
  // is kept beside it so nothing typed is lost. Settings merge instead.
  function resolveConflict(it, serverDoc) {
    var a = A(), p = it.payload;
    if (it.action === "delete") { a.applyDoc(serverDoc); return Promise.resolve(); }
    if (p.collection === "settings") {
      var merged = p.id === "prefs" ? Object.assign({}, serverDoc.data, p.data) : serverDoc.data;
      return a.call("put", { collection: "settings", id: p.id, data: merged, baseVersion: serverDoc.version }, { direct: true })
        .then(function (r) { a.applyDoc(r.doc); }, function () { a.applyDoc(serverDoc); });
    }
    a.applyDoc(serverDoc);
    var copy = Object.assign({}, p.data, { title: String((p.data && p.data.title) || "Untitled") + " (offline copy)", pinned: false });
    return a.call("put", { collection: p.collection, id: a.newId(p.collection === "entries" ? "e" : "t"), data: copy }, { direct: true })
      .then(function (r) { a.applyDoc(r.doc); }, function () {});
  }

  function replay() {
    var a = A();
    if (!a || Q.replaying || !Q.items.length) return Promise.resolve(null);
    if (typeof navigator !== "undefined" && navigator.onLine === false) return Promise.resolve(null);
    Q.replaying = true;
    a.render();
    var n = { sent: 0, conflicts: 0, failed: 0 };
    var step = function () {
      if (!Q.items.length) return Promise.resolve();
      var it = Q.items[0];
      return a.call(it.action, it.payload, { direct: true }).then(function (r) {
        n.sent++;
        shift();
        if (r && r.doc) a.applyDoc(r.doc);
        return step();
      }, function (err) {
        if (err.offline) throw err; // still unreachable: keep the rest for later
        shift();
        if (err.status === 409 && err.body && err.body.doc) { n.conflicts++; return resolveConflict(it, err.body.doc).then(step); }
        n.failed++;
        a.toast("One offline change was refused: " + err.message, { error: true });
        return step();
      });
    };
    return step().then(function () { return true; }, function () { return false; }).then(function (reached) {
      Q.replaying = false;
      if (n.sent || n.conflicts || n.failed) {
        var bits = [];
        if (n.sent) bits.push(n.sent + " synced");
        if (n.conflicts) bits.push(n.conflicts + " kept as offline copies after a conflict");
        if (n.failed) bits.push(n.failed + " refused");
        a.toast("Offline changes: " + bits.join(", ") + ".", { error: !!(n.conflicts || n.failed) });
      }
      a.render();
      return reached ? n : null;
    });
  }

  window.addEventListener("online", function () { setTimeout(replay, 500); });

  Desk.queue = { QUEUEABLE: QUEUEABLE, add: add, synth: synth, replay: replay, size: size, clear: clear, items: function () { return Q.items.slice(); } };
})();
