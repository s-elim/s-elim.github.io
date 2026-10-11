/* ==========================================================================
   Research desk - the entry editor: fields, rich text, images, revision
   history, "send to Notion" and "add to calendar". Uses Desk.app at call time,
   so it can load before app.js.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var TC = [["tc-1", "hsl(2 62% 42%)"], ["tc-2", "hsl(28 68% 42%)"], ["tc-3", "hsl(46 72% 36%)"], ["tc-4", "hsl(150 50% 32%)"], ["tc-5", "hsl(206 60% 40%)"], ["tc-6", "hsl(276 48% 44%)"]];
  var HL = [["hl-1", "hsl(48 86% 72%)"], ["hl-2", "hsl(150 56% 72%)"], ["hl-3", "hsl(204 76% 76%)"], ["hl-4", "hsl(318 66% 78%)"], ["hl-5", "hsl(2 72% 78%)"]];
  var PH = {
    thesis: ["Thesis", "the claim in one sentence", "What would be true if this worked?"],
    gap: ["Open question", "what nobody has shown yet", "The gap, stated so it can be attacked."],
    experiment: ["Plan", "the steps, or the cheapest test that could kill it", "Concrete enough to start on Monday."],
    risk: ["Risk", "what a reviewer attacks first", "The objection you cannot answer yet."]
  };
  var MAX_IMAGES = 8;

  var ed = { id: null, version: null, clean: "", forced: false, images: [], active: null, saving: false };

  function $(id) { return document.getElementById(id); }

  function build() {
    if ($("dk-editor")) return;
    var a = A(), esc = a.esc;
    var opts = function (list) { return list.map(function (x) { return '<option value="' + x.id + '">' + esc(x.label) + '</option>'; }).join(""); };
    var d = document.createElement("dialog");
    d.id = "dk-editor";
    d.className = "dk-dialog dk-dialog--side";
    d.innerHTML =
      '<form class="dk-dialog__in" id="dk-ed-form" novalidate>' +
        '<header class="dk-dialog__head"><h3 id="dk-ed-h">New entry</h3><span class="dk-ed__state" id="dk-ed-state" role="status"></span>' +
          '<button type="button" class="dk-icon" id="dk-ed-close" aria-label="Close"><i class="fas fa-times" aria-hidden="true"></i></button></header>' +
        '<div class="dk-dialog__body dk-ed">' +
          '<input type="text" class="dk-input dk-input--title" id="dk-ed-title" placeholder="What you will recognise in six months" aria-label="Title" maxlength="300">' +
          '<div class="dk-grid3">' +
            '<label class="dk-field"><span>Type</span><select class="dk-select" id="dk-ed-kind">' + opts(C.KINDS) + '</select></label>' +
            '<label class="dk-field"><span>Axis</span><select class="dk-select" id="dk-ed-axis">' + opts(C.AXES) + '</select></label>' +
            '<label class="dk-field"><span>Status</span><select class="dk-select" id="dk-ed-status">' + opts(C.STATUSES) + '</select></label>' +
          '</div>' +
          '<div class="dk-grid3">' +
            '<div class="dk-field"><span>Conviction</span><div class="dk-seg dk-seg--conv" id="dk-ed-conv" role="radiogroup" aria-label="Conviction">' +
              [1, 2, 3, 4, 5].map(function (n) { return '<button type="button" class="dk-seg__b" role="radio" data-conv="' + n + '">' + n + '</button>'; }).join("") + '</div></div>' +
            '<label class="dk-field"><span>Target venue</span><input type="text" class="dk-input" id="dk-ed-venue" placeholder="CoRL 2027"></label>' +
            '<label class="dk-field"><span>Deadline</span><input type="date" class="dk-input" id="dk-ed-deadline"></label>' +
          '</div>' +
          '<label class="dk-field"><span>Tags, comma separated</span><input type="text" class="dk-input" id="dk-ed-tags" placeholder="world-models, egocentric"></label>' +
          '<div class="dk-grid2">' +
            '<label class="dk-field"><span>Source</span><input type="text" class="dk-input" id="dk-ed-srclabel" placeholder="Where it came from"></label>' +
            '<label class="dk-field"><span>Source link</span><input type="url" class="dk-input" id="dk-ed-srcurl" placeholder="https://"></label>' +
          '</div>' +
          '<div class="dk-rtbar" id="dk-ed-toolbar" role="toolbar" aria-label="Formatting"></div>' +
          C.RT_FIELDS.map(function (f) {
            return '<div class="dk-field"><span>' + PH[f][0] + ' <em>' + PH[f][1] + '</em></span>' +
              '<div class="dk-rt dk-rt--edit" id="dk-ed-' + f + '" contenteditable="true" role="textbox" aria-multiline="true" aria-label="' + PH[f][0] + '" data-ph="' + PH[f][2] + '"></div></div>';
          }).join("") +
          '<div class="dk-field"><span>Images <em>kept in the “Research Desk images” Drive folder, visible to anyone with the link</em></span><div class="dk-thumbs" id="dk-ed-thumbs"></div>' +
            '<div class="dk-row"><label class="dk-btn dk-file"><i class="fas fa-image" aria-hidden="true"></i> Attach<input type="file" id="dk-ed-img" accept="image/*" multiple hidden></label>' +
            '<span class="dk-hint" id="dk-ed-imghint">Up to ' + MAX_IMAGES + '. Resized to 1600 px before upload.</span></div></div>' +
          '<p class="dk-hint" id="dk-ed-links"></p>' +
        '</div>' +
        '<footer class="dk-dialog__foot dk-ed__foot">' +
          '<div class="dk-ed__more">' +
            '<button type="button" class="dk-btn dk-btn--quiet" id="dk-ed-history" title="Earlier versions"><i class="fas fa-history" aria-hidden="true"></i> History</button>' +
            '<button type="button" class="dk-btn dk-btn--quiet" id="dk-ed-notion" title="Create a row in Research OS"><i class="fas fa-database" aria-hidden="true"></i> Notion</button>' +
            '<button type="button" class="dk-btn dk-btn--quiet" id="dk-ed-cal" title="Put this on Google Calendar"><i class="fas fa-calendar-plus" aria-hidden="true"></i> Calendar</button>' +
            '<button type="button" class="dk-btn dk-btn--quiet dk-btn--danger" id="dk-ed-del"><i class="fas fa-trash-alt" aria-hidden="true"></i> Delete</button>' +
          '</div>' +
          '<div class="dk-ed__save"><button type="button" class="dk-btn" id="dk-ed-cancel">Cancel</button>' +
          '<button type="submit" class="dk-btn dk-btn--primary" id="dk-ed-save">Save</button></div>' +
        '</footer>' +
      '</form>';
    document.body.appendChild(d);
    buildToolbar();
    wire(d);
  }

  function buildToolbar() {
    var h = "";
    h += '<button type="button" class="dk-tb" data-cmd="bold" title="Bold"><b>B</b></button>';
    h += '<button type="button" class="dk-tb" data-cmd="italic" title="Italic"><i>I</i></button>';
    h += '<button type="button" class="dk-tb" data-cmd="underline" title="Underline"><u>U</u></button>';
    h += '<button type="button" class="dk-tb" data-cmd="strikeThrough" title="Strikethrough"><s>S</s></button>';
    h += '<button type="button" class="dk-tb" data-wrap="code" title="Inline code"><i class="fas fa-code" aria-hidden="true"></i></button>';
    h += '<span class="dk-tb__sep"></span>';
    h += '<button type="button" class="dk-tb" data-cmd="insertUnorderedList" title="Bulleted list"><i class="fas fa-list-ul" aria-hidden="true"></i></button>';
    h += '<button type="button" class="dk-tb" data-cmd="insertOrderedList" title="Numbered list"><i class="fas fa-list-ol" aria-hidden="true"></i></button>';
    h += '<button type="button" class="dk-tb" data-link="1" title="Link"><i class="fas fa-link" aria-hidden="true"></i></button>';
    h += '<span class="dk-tb__sep"></span>';
    h += TC.map(function (c) { return '<button type="button" class="dk-sw" data-color="' + c[0] + '" style="background:' + c[1] + '" title="Text colour" aria-label="Text colour"></button>'; }).join("");
    h += '<span class="dk-tb__sep"></span>';
    h += HL.map(function (c) { return '<button type="button" class="dk-sw dk-sw--hl" data-hl="' + c[0] + '" style="background:' + c[1] + '" title="Highlight" aria-label="Highlight"></button>'; }).join("");
    h += '<span class="dk-tb__sep"></span>';
    h += '<button type="button" class="dk-tb" data-pinsel="1" title="Pin this passage to Today"><i class="fas fa-thumbtack" aria-hidden="true"></i></button>';
    h += '<button type="button" class="dk-tb" data-clear="1" title="Clear formatting"><i class="fas fa-remove-format" aria-hidden="true"></i></button>';
    $("dk-ed-toolbar").innerHTML = h;
  }

  function inActive(node) { return ed.active && node && ed.active.contains(node.nodeType === 1 ? node : node.parentNode); }
  function wrapSelection(tag, cls) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) return;
    var r = sel.getRangeAt(0);
    if (!inActive(r.commonAncestorContainer)) return;
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    try { r.surroundContents(el); } catch (err) { el.appendChild(r.extractContents()); r.insertNode(el); }
    sel.removeAllRanges();
    var nr = document.createRange(); nr.selectNodeContents(el); sel.addRange(nr);
    markDirty();
  }
  function clearFormatting() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !ed.active) return;
    try { document.execCommand("removeFormat"); } catch (e) {}
    var r = sel.getRangeAt(0), nodes = ed.active.querySelectorAll("span,mark,code");
    for (var i = nodes.length - 1; i >= 0; i--) {
      var n = nodes[i];
      if (!r.intersectsNode || r.intersectsNode(n)) {
        var p = n.parentNode;
        while (n.firstChild) p.insertBefore(n.firstChild, n);
        p.removeChild(n);
      }
    }
    markDirty();
  }

  // Dirty means "differs from what was last loaded or saved", not "an input
  // event fired": a text field fires change on blur even after a save.
  function snapshot() {
    var a = A(), out = [ed.images.join(",")];
    ["title", "kind", "axis", "status", "venue", "deadline", "tags", "srclabel", "srcurl"].forEach(function (k) { out.push($("dk-ed-" + k).value); });
    out.push($("dk-ed-conv").getAttribute("data-value"));
    C.RT_FIELDS.forEach(function (f) { out.push(a.sanitize($("dk-ed-" + f).innerHTML)); });
    return JSON.stringify(out);
  }
  function isDirty() { return ed.forced || snapshot() !== ed.clean; }
  function markClean() { ed.clean = snapshot(); ed.forced = false; }
  function markDirty() {
    $("dk-ed-state").textContent = isDirty() ? "Unsaved" : ed.version ? "Saved" : "";
  }

  function wire(d) {
    d.addEventListener("cancel", function (e) { e.preventDefault(); close(); });
    d.addEventListener("click", function (e) { if (e.target === d) close(); });
    $("dk-ed-close").addEventListener("click", close);
    $("dk-ed-cancel").addEventListener("click", close);
    $("dk-ed-form").addEventListener("submit", function (e) { e.preventDefault(); save(true); });
    $("dk-ed-form").addEventListener("input", markDirty);
    $("dk-ed-form").addEventListener("change", markDirty);
    d.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(false); }
    });
    $("dk-ed-conv").addEventListener("click", function (e) {
      var b = e.target.closest("[data-conv]");
      if (b) { setConv(+b.getAttribute("data-conv")); markDirty(); }
    });
    C.RT_FIELDS.forEach(function (f) {
      var el = $("dk-ed-" + f);
      el.addEventListener("focus", function () {
        ed.active = el;
        C.RT_FIELDS.forEach(function (g) { $("dk-ed-" + g).classList.toggle("is-active", g === f); });
      });
      el.addEventListener("paste", function (e) {
        e.preventDefault();
        var txt = "";
        try { txt = (e.clipboardData || window.clipboardData).getData("text/plain"); } catch (err) {}
        try { document.execCommand("insertText", false, txt); } catch (err) {}
      });
    });
    var tb = $("dk-ed-toolbar");
    tb.addEventListener("mousedown", function (e) { if (e.target.closest("button")) e.preventDefault(); });
    tb.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      if (!ed.active) { ed.active = $("dk-ed-thesis"); ed.active.focus(); }
      if (b.dataset.cmd) { try { document.execCommand(b.dataset.cmd, false, null); } catch (err) {} markDirty(); }
      else if (b.dataset.wrap) wrapSelection("code", "");
      else if (b.dataset.color) wrapSelection("span", b.dataset.color);
      else if (b.dataset.hl) wrapSelection("mark", b.dataset.hl);
      else if (b.dataset.pinsel) wrapSelection("mark", "pin");
      else if (b.dataset.clear) clearFormatting();
      else if (b.dataset.link) {
        var url = window.prompt("Link to (https://…)");
        if (url && /^https?:\/\//i.test(url.trim())) { try { document.execCommand("createLink", false, url.trim()); } catch (err) {} markDirty(); }
      }
    });
    $("dk-ed-img").addEventListener("change", attachImages);
    $("dk-ed-thumbs").addEventListener("click", function (e) {
      var b = e.target.closest("[data-rmimg]");
      if (b) { ed.images.splice(+b.getAttribute("data-rmimg"), 1); renderThumbs(); markDirty(); return; }
      var img = e.target.closest("img[data-full]");
      if (img) window.open(img.src, "_blank", "noopener");
    });
    $("dk-ed-history").addEventListener("click", openHistory);
    $("dk-ed-notion").addEventListener("click", openPush);
    $("dk-ed-cal").addEventListener("click", openCal);
    $("dk-ed-del").addEventListener("click", function () {
      if (!ed.id || !window.confirm("Delete this entry? Its history stays on the server and an export can restore it.")) return;
      var id = ed.id;
      markClean();
      $("dk-editor").close();
      A().deleteEntry(id).catch(function (err) { A().failed(err, "Delete failed"); });
    });
  }

  function setConv(n) {
    $("dk-ed-conv").querySelectorAll("[data-conv]").forEach(function (b) {
      b.setAttribute("aria-checked", String(+b.getAttribute("data-conv") === n));
      b.setAttribute("aria-pressed", String(+b.getAttribute("data-conv") === n));
    });
    $("dk-ed-conv").setAttribute("data-value", String(n));
  }

  function fill(e) {
    var a = A();
    $("dk-ed-title").value = e.title;
    $("dk-ed-kind").value = e.kind;
    $("dk-ed-axis").value = e.axis;
    $("dk-ed-status").value = e.status;
    setConv(e.conviction);
    $("dk-ed-venue").value = e.venue;
    $("dk-ed-deadline").value = e.deadline;
    $("dk-ed-tags").value = e.tags.join(", ");
    $("dk-ed-srclabel").value = e.sourceLabel;
    $("dk-ed-srcurl").value = e.sourceUrl;
    C.RT_FIELDS.forEach(function (f) { $("dk-ed-" + f).innerHTML = a.sanitize(e[f]); });
    ed.images = e.images.slice();
    renderThumbs();
    var links = [];
    if (a.safeUrl(e.notionUrl)) links.push('<a href="' + a.esc(e.notionUrl) + '" target="_blank" rel="noopener"><i class="fas fa-database" aria-hidden="true"></i> In Notion</a>');
    if (a.safeUrl(e.calendarUrl)) links.push('<a href="' + a.esc(e.calendarUrl) + '" target="_blank" rel="noopener"><i class="fas fa-calendar" aria-hidden="true"></i> On the calendar</a>');
    if (e.addedAt) links.push("Added " + a.esc(new Date(e.addedAt).toLocaleDateString()));
    $("dk-ed-links").innerHTML = links.join(" · ");
  }

  function collect() {
    var a = A(), prev = ed.id && a.entryDoc(ed.id) ? a.entryData(a.entryDoc(ed.id).e) : {};
    var data = Object.assign({}, prev, {
      title: $("dk-ed-title").value.trim().slice(0, 300),
      kind: $("dk-ed-kind").value, axis: $("dk-ed-axis").value, status: $("dk-ed-status").value,
      conviction: +$("dk-ed-conv").getAttribute("data-value") || 3,
      venue: $("dk-ed-venue").value.trim().slice(0, 200), deadline: $("dk-ed-deadline").value || "",
      tags: $("dk-ed-tags").value.split(",").map(function (s) { return s.trim().replace(/^#/, ""); }).filter(Boolean).slice(0, 16),
      sourceLabel: $("dk-ed-srclabel").value.trim().slice(0, 300), sourceUrl: $("dk-ed-srcurl").value.trim().slice(0, 1000),
      images: ed.images.slice(0, MAX_IMAGES)
    });
    C.RT_FIELDS.forEach(function (f) { data[f] = a.sanitize($("dk-ed-" + f).innerHTML).slice(0, 40000); });
    return data;
  }

  function open(id, preset) {
    build();
    var a = A();
    var rec = id ? a.entryDoc(id) : null;
    ed.id = rec ? rec.id : a.newId("e");
    ed.version = rec ? rec.version : null;
    ed.isNew = !rec;
    ed.active = null;
    $("dk-ed-h").textContent = rec ? "Edit entry" : "New entry";
    $("dk-ed-save").textContent = rec ? "Save" : "Add to board";
    ["dk-ed-history", "dk-ed-notion", "dk-ed-cal", "dk-ed-del"].forEach(function (b) { $(b).hidden = !rec; });
    fill(rec ? rec.e : C.normaliseEntry(ed.id, preset || {}));
    markClean();
    $("dk-ed-state").textContent = rec && rec.e.updatedAt ? "Saved " + new Date(rec.e.updatedAt).toLocaleString() : "";
    C.RT_FIELDS.forEach(function (g) { $("dk-ed-" + g).classList.remove("is-active"); });
    var d = $("dk-editor");
    if (!d.open) d.showModal();
    setTimeout(function () { $("dk-ed-title").focus(); }, 30);
  }

  function close() {
    if (isDirty() && !window.confirm("Discard unsaved changes?")) return;
    $("dk-editor").close();
  }

  function save(andClose) {
    if (ed.saving) return;
    var title = $("dk-ed-title").value.trim();
    if (!title) { $("dk-ed-title").focus(); $("dk-ed-state").textContent = "Give it a title"; return; }
    ed.saving = true;
    $("dk-ed-save").disabled = true;
    $("dk-ed-state").textContent = "Saving…";
    A().saveEntry(ed.id, collect(), ed.version).then(function (doc) {
      ed.version = doc.version;
      ed.isNew = false;
      markClean();
      $("dk-ed-state").textContent = "Saved";
      ["dk-ed-history", "dk-ed-notion", "dk-ed-cal", "dk-ed-del"].forEach(function (b) { $(b).hidden = false; });
      $("dk-ed-save").textContent = "Save";
      if (andClose) $("dk-editor").close();
    }, function (err) {
      $("dk-ed-state").textContent = err.status === 409 ? "Changed elsewhere" : "Not saved";
      if (err.status === 409) { var rec = A().entryDoc(ed.id); if (rec) ed.version = rec.version; }
      else A().failed(err, "Not saved");
    }).then(function () { ed.saving = false; $("dk-ed-save").disabled = false; });
  }

  /* ---- images --------------------------------------------------------- */
  function renderThumbs() {
    var box = $("dk-ed-thumbs");
    if (!ed.images.length) { box.innerHTML = '<span class="dk-quiet">None.</span>'; return; }
    box.innerHTML = ed.images.map(function (im, i) {
      var url = im && A().safeUrl(im.url);
      return '<span class="dk-thumb">' + (url ? '<img alt="Attachment ' + (i + 1) + '" src="' + A().esc(url) + '" data-full="1" loading="lazy">' : '<span class="dk-quiet">Image ' + (i + 1) + '</span>') +
        '<button type="button" data-rmimg="' + i + '" aria-label="Remove image"><i class="fas fa-times" aria-hidden="true"></i></button></span>';
    }).join("");
  }

  function downscale(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var max = 1600, w = img.naturalWidth, h = img.naturalHeight, k = Math.min(1, max / Math.max(w, h));
        var cv = document.createElement("canvas");
        cv.width = Math.round(w * k); cv.height = Math.round(h * k);
        var g = cv.getContext("2d");
        g.fillStyle = "#fff"; g.fillRect(0, 0, cv.width, cv.height);
        g.drawImage(img, 0, 0, cv.width, cv.height);
        URL.revokeObjectURL(url);
        var q = 0.86, out = cv.toDataURL("image/jpeg", q);
        while (out.length > 1.3e6 && q > 0.4) { q -= 0.12; out = cv.toDataURL("image/jpeg", q); }
        resolve({ url: out, w: cv.width, h: cv.height });
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("That file is not an image the browser can read.")); };
      img.src = url;
    });
  }

  function attachImages(e) {
    var files = Array.prototype.slice.call(e.target.files || []);
    e.target.value = "";
    var hint = $("dk-ed-imghint"), room = MAX_IMAGES - ed.images.length;
    if (room <= 0) { hint.textContent = MAX_IMAGES + " images is the limit for one entry."; return; }
    files = files.slice(0, room);
    hint.textContent = "Uploading " + files.length + "…";
    files.reduce(function (p, file) {
      return p.then(function () {
        return downscale(file).then(function (img) {
          return A().call("uploadImage", { name: file.name.slice(0, 100), dataUrl: img.url }).then(function (r) {
            ed.images.push({ id: r.image.id, url: r.image.url });
            markDirty();
            renderThumbs();
          });
        });
      });
    }, Promise.resolve()).then(function () { hint.textContent = "Attached. Save to keep them on the entry."; },
      function (err) { hint.textContent = "Upload failed: " + err.message; });
  }

  /* ---- history -------------------------------------------------------- */
  function openHistory() {
    var a = A(), id = ed.id;
    var d = a.dialog("dk-history", "Earlier versions", '<p class="dk-quiet">Loading…</p>');
    a.call("revisions", { collection: "entries", id: id }).then(function (r) {
      var body = d.querySelector(".dk-dialog__body");
      if (!r.revisions.length) { body.innerHTML = '<p class="dk-quiet">No history yet.</p>'; return; }
      body.innerHTML = '<ol class="dk-revs">' + r.revisions.map(function (v) {
        return '<li><button type="button" class="dk-rev" data-rev="' + v.version + '"><b>Version ' + v.version + '</b>' +
          '<span>' + a.esc(new Date(v.savedAt).toLocaleString()) + (v.deleted ? " · deleted" : "") + " · " + Math.max(1, Math.round(v.size / 1024)) + ' KB</span></button></li>';
      }).join("") + '</ol><div class="dk-revview" id="dk-revview"></div>';
      body.querySelector(".dk-revs").addEventListener("click", function (e) {
        var b = e.target.closest("[data-rev]");
        if (!b) return;
        body.querySelectorAll(".dk-rev").forEach(function (x) { x.classList.toggle("is-on", x === b); });
        a.call("revision", { collection: "entries", id: id, version: +b.getAttribute("data-rev") }).then(function (rv) {
          var e2 = C.normaliseEntry(id, rv.revision.data);
          $("dk-revview").innerHTML = '<h4>' + a.esc(e2.title) + '</h4>' +
            C.RT_FIELDS.map(function (f) { var t = a.plain(e2[f]); return t ? '<p><b>' + C.RT_LABEL[f] + ':</b> ' + a.esc(t.slice(0, 600)) + '</p>' : ""; }).join("") +
            '<button type="button" class="dk-btn dk-btn--primary" id="dk-rev-load">Load this version into the editor</button>' +
            '<p class="dk-hint">Loading does not save. Press Save afterwards to make it the current version; the newer versions stay in history.</p>';
          $("dk-rev-load").addEventListener("click", function () {
            fill(e2);
            ed.forced = true;
            markDirty();
            d.close();
          });
        }, function (err) { a.failed(err, "History"); });
      });
    }, function (err) { d.close(); a.failed(err, "History"); });
  }

  /* ---- send to Notion ------------------------------------------------- */
  function openPush() {
    var a = A(), rec = a.entryDoc(ed.id);
    if (!rec) return;
    var e = C.normaliseEntry(ed.id, collect());
    var d = a.dialog("dk-push", "Send to Research OS", '<p class="dk-quiet">Reading your Notion databases…</p>',
      '<button type="button" class="dk-btn" data-close2>Cancel</button><button type="button" class="dk-btn dk-btn--primary" id="dk-push-go" disabled>Create the row</button>');
    d.querySelector("[data-close2]").addEventListener("click", function () { d.close(); });
    var body = d.querySelector(".dk-dialog__body");
    var schema = null;
    a.call("notionTargets").then(function (r) {
      if (!r.notion) { body.innerHTML = '<p class="dk-hint is-bad">Notion is not connected. See Settings.</p>'; return; }
      body.innerHTML =
        (e.notionUrl ? '<p class="dk-hint">This entry already has a Notion row. Creating another adds a second row; nothing is overwritten.</p>' : "") +
        '<label class="dk-field"><span>Database</span><select class="dk-select" id="dk-push-db">' + r.targets.map(function (t) { return '<option value="' + a.esc(t.id) + '">' + a.esc(t.label) + '</option>'; }).join("") + '</select></label>' +
        '<label class="dk-field"><span>Title</span><input type="text" class="dk-input" id="dk-push-title" value="' + a.esc(e.title) + '"></label>' +
        '<div class="dk-pushfields" id="dk-push-fields"></div>' +
        '<div class="dk-field"><span>Page body</span><pre class="dk-preview">' + a.esc(C.entryMarkdown(e)) + '</pre></div>' +
        '<p class="dk-hint" id="dk-push-msg" role="status"></p>';
      var pick = function () {
        $("dk-push-go").disabled = true;
        $("dk-push-fields").innerHTML = '<p class="dk-quiet">Reading columns…</p>';
        a.call("notionSchema", { id: $("dk-push-db").value }).then(function (s) {
          schema = s;
          var defs = C.notionDefaults(e, s.fields);
          $("dk-push-fields").innerHTML = s.fields.filter(function (f) { return f.type !== "title"; }).map(function (f, i) {
            var v = defs[f.name] || "", label = '<span>' + a.esc(f.name) + ' <em>' + a.esc(f.type.replace("_", " ")) + '</em></span>';
            if (f.type === "select" || f.type === "status") {
              return '<label class="dk-field">' + label + '<select class="dk-select" data-pf="' + a.esc(f.name) + '"><option value="">(leave empty)</option>' +
                f.options.map(function (o) { return '<option' + (o === v ? " selected" : "") + '>' + a.esc(o) + '</option>'; }).join("") + '</select></label>';
            }
            if (f.type === "date") return '<label class="dk-field">' + label + '<input type="date" class="dk-input" data-pf="' + a.esc(f.name) + '" value="' + a.esc(v) + '"></label>';
            if (f.type === "checkbox") return '<label class="dk-toggle"><input type="checkbox" data-pf="' + a.esc(f.name) + '" data-check="1"> ' + a.esc(f.name) + '</label>';
            return '<label class="dk-field">' + label + '<textarea class="dk-input" rows="' + (v.length > 120 ? 3 : 1) + '" data-pf="' + a.esc(f.name) + '"' +
              (f.type === "multi_select" ? ' placeholder="' + a.esc(f.options.slice(0, 4).join(", ")) + '"' : "") + '>' + a.esc(v) + '</textarea></label>';
          }).join("");
          $("dk-push-go").disabled = false;
        }, function (err) { $("dk-push-fields").innerHTML = '<p class="dk-hint is-bad">' + a.esc(err.message) + '</p>'; });
      };
      $("dk-push-db").addEventListener("change", pick);
      pick();
    }, function (err) { body.innerHTML = '<p class="dk-hint is-bad">' + a.esc(err.message) + '</p>'; });

    $("dk-push-go").addEventListener("click", function () {
      if (!schema) return;
      var fields = {};
      d.querySelectorAll("[data-pf]").forEach(function (el) {
        var v = el.getAttribute("data-check") ? (el.checked ? "true" : "") : el.value.trim();
        if (v) fields[el.getAttribute("data-pf")] = v;
      });
      $("dk-push-go").disabled = true;
      $("dk-push-msg").textContent = "Creating…";
      a.call("notionCreate", { target: $("dk-push-db").value, title: $("dk-push-title").value.trim() || e.title, fields: fields, body: C.entryMarkdown(e) }).then(function (r) {
        $("dk-push-msg").innerHTML = 'Created. ' + (a.safeUrl(r.url) ? '<a href="' + a.esc(r.url) + '" target="_blank" rel="noopener">Open it in Notion</a>.' : "");
        var cur = a.entryDoc(ed.id);
        if (cur && r.url) {
          a.saveEntry(ed.id, Object.assign(a.entryData(cur.e), { notionUrl: r.url }), cur.version).then(function (doc) { ed.version = doc.version; fill(C.normaliseEntry(ed.id, doc.data)); });
        }
      }, function (err) {
        $("dk-push-go").disabled = false;
        $("dk-push-msg").textContent = err.message + (err.offline ? " The row may or may not exist; check Notion before trying again." : "");
      });
    });
  }

  /* ---- add to calendar ------------------------------------------------ */
  function openCal() {
    var a = A(), e = C.normaliseEntry(ed.id, collect());
    var title = C.byId(C.KINDS, e.kind).label + ": " + e.title;
    var details = [a.plain(e.thesis), a.plain(e.experiment)].filter(Boolean).join("\n\n").slice(0, 1400);
    var g = a.googleReady(), cals = g ? (a.S.sync.google.calendars || []).filter(function (c) { return c.writable; }) : [];
    var d = a.dialog("dk-addcal", "Put this on Google Calendar",
      '<label class="dk-field"><span>Title</span><input type="text" class="dk-input" id="dk-c-title" value="' + a.esc(title.slice(0, 250)) + '"></label>' +
      (cals.length > 1 ? '<label class="dk-field"><span>Calendar</span><select class="dk-select" id="dk-c-cal">' + cals.map(function (c) {
        return '<option value="' + a.esc(c.id) + '"' + (c.primary ? " selected" : "") + '>' + a.esc(c.title) + '</option>'; }).join("") + '</select></label>' : "") +
      '<div class="dk-grid3"><label class="dk-field"><span>Date</span><input type="date" class="dk-input" id="dk-c-date" value="' + a.esc(e.deadline || a.today()) + '"></label>' +
      '<label class="dk-field"><span>Start</span><input type="time" class="dk-input" id="dk-c-start" value="09:00"></label>' +
      '<label class="dk-field"><span>End</span><input type="time" class="dk-input" id="dk-c-end" value="10:00"></label></div>' +
      '<label class="dk-toggle"><input type="checkbox" id="dk-c-allday"> All day</label>' +
      '<label class="dk-field"><span>Description</span><textarea class="dk-input" id="dk-c-desc" rows="4">' + a.esc(details) + '</textarea></label>' +
      '<p class="dk-hint" id="dk-c-msg" role="status">' + (g ? "" : "Google is not connected, so this opens Google Calendar with the event filled in.") + '</p>',
      '<button type="button" class="dk-btn dk-btn--primary" id="dk-c-go">' + (g ? "Create the event" : "Open Google Calendar") + '</button>');
    $("dk-c-allday").addEventListener("change", function (ev) { $("dk-c-start").disabled = ev.target.checked; $("dk-c-end").disabled = ev.target.checked; });
    $("dk-c-go").addEventListener("click", function () {
      var o = { title: $("dk-c-title").value.trim() || title, date: $("dk-c-date").value || a.today(), start: $("dk-c-start").value, end: $("dk-c-end").value,
        allDay: $("dk-c-allday").checked, description: $("dk-c-desc").value.trim(), tz: a.tz() };
      if (!g) { window.open(C.gcalTemplateUrl({ title: o.title, date: o.date, start: o.allDay ? "" : o.start, end: o.end, allDay: o.allDay, details: o.description, tz: o.tz }), "_blank", "noopener"); d.close(); return; }
      $("dk-c-go").disabled = true;
      $("dk-c-msg").textContent = "Creating…";
      a.call("createEvent", { title: o.title, date: o.date, start: o.start, end: o.end, allDay: o.allDay, description: o.description, tz: o.tz,
        calendarId: $("dk-c-cal") ? $("dk-c-cal").value : undefined }).then(function (r) {
        $("dk-c-msg").innerHTML = "Created. " + (a.safeUrl(r.link) ? '<a href="' + a.esc(r.link) + '" target="_blank" rel="noopener">Open it</a>.' : "");
        var cur = a.entryDoc(ed.id);
        if (cur && r.link) a.saveEntry(ed.id, Object.assign(a.entryData(cur.e), { calendarUrl: r.link }), cur.version).then(function (doc) { ed.version = doc.version; });
        a.refresh(true);
      }, function (err) { $("dk-c-go").disabled = false; $("dk-c-msg").textContent = err.message; });
    });
  }

  Desk.editor = { open: open };
})();
