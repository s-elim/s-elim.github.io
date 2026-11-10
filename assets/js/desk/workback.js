/* ==========================================================================
   Research desk - work back from a deadline. A conference date, a Notion
   deadline or an entry's own deadline becomes a short chain of dated tasks
   (outline, freeze experiments, full draft...), each editable before it is
   created. The template is remembered in the desk's settings when asked.
   Uses Desk.app at call time.
   ========================================================================== */
(function () {
  "use strict";

  var Desk = window.Desk = window.Desk || {};
  var C = Desk.core;
  var A = function () { return Desk.app; };
  var MAX_STEPS = 12;

  function $(id) { return document.getElementById(id); }

  function template() {
    var a = A(), saved = a.S.prefs.data.workback;
    var tpl = C.normTemplate(saved);
    return tpl.length ? tpl : C.WORKBACK_DEFAULT.slice();
  }

  function rowHtml(r, i) {
    var esc = A().esc;
    return '<li class="dk-wb__row" data-wb="' + i + '">' +
      '<input type="text" class="dk-input dk-wb__title" value="' + esc(r.title) + '" aria-label="Step ' + (i + 1) + ' title" maxlength="200">' +
      '<label class="dk-wb__before"><input type="number" class="dk-input" min="0" max="365" value="' + r.before + '" aria-label="Days before the deadline"><span>d before</span></label>' +
      '<span class="dk-wb__due" aria-live="polite"></span>' +
      '<button type="button" class="dk-icon dk-icon--sm" data-wbrm="' + i + '" aria-label="Remove step ' + (i + 1) + '"><i class="fas fa-times" aria-hidden="true"></i></button>' +
    '</li>';
  }

  function readRows(d) {
    return Array.prototype.map.call(d.querySelectorAll(".dk-wb__row"), function (li) {
      return { title: li.querySelector(".dk-wb__title").value, before: li.querySelector("input[type=number]").value };
    });
  }

  function paintDues(d) {
    var a = A(), date = $("dk-wb-date").value, t = a.today();
    var rows = readRows(d), plan = C.workBack(date, rows, t);
    Array.prototype.forEach.call(d.querySelectorAll(".dk-wb__row"), function (li) {
      var r = rows[+li.getAttribute("data-wb")], hit = null;
      for (var i = 0; i < plan.length; i++) if (plan[i].title === String(r.title).trim() && plan[i].before === (Math.max(0, Math.min(365, Math.round(Number(r.before)) || 0)))) { hit = plan[i]; break; }
      li.classList.toggle("is-skipped", !!(hit && hit.clamped));
      li.querySelector(".dk-wb__due").textContent = !hit ? "" : hit.clamped ? "Skipped, the date has passed" : a.fmtDate(hit.due, { weekday: "short", day: "numeric", month: "short" });
    });
    var count = plan.filter(function (s) { return !s.clamped; }).length;
    $("dk-wb-go").textContent = count ? "Create " + count + (count === 1 ? " task" : " tasks") : "Nothing to create";
    $("dk-wb-go").disabled = !count || !C.isYmd(date);
  }

  // ref: { title, date, source }
  function open(ref) {
    var a = A(), esc = a.esc;
    if (!ref || !C.isYmd(ref.date)) { a.toast("That deadline has no date to work back from.", { error: true }); return; }
    var dest = a.tasksReady() ? "Google Tasks" : "desk tasks" + (a.googleReady() ? "" : " (Google Tasks is not connected)");
    var tpl = template();
    var d = a.dialog("dk-workback", "Work back from a deadline",
      '<p class="dk-hint">Each step becomes a dated task in ' + esc(dest) + '. Edit the titles and the lead times first; a step whose date has already passed is skipped.</p>' +
      '<div class="dk-grid2"><label class="dk-field"><span>Deadline</span><input type="text" class="dk-input" id="dk-wb-title" value="' + esc(ref.title) + '" maxlength="200"></label>' +
      '<label class="dk-field"><span>Date</span><input type="date" class="dk-input" id="dk-wb-date" value="' + esc(ref.date) + '"></label></div>' +
      '<ol class="dk-wb" id="dk-wb-rows">' + tpl.map(rowHtml).join("") + '</ol>' +
      '<div class="dk-row"><button type="button" class="dk-btn" id="dk-wb-add"><i class="fas fa-plus" aria-hidden="true"></i> Add a step</button>' +
      '<button type="button" class="dk-btn dk-btn--quiet" id="dk-wb-reset">Default steps</button></div>' +
      '<label class="dk-toggle"><input type="checkbox" id="dk-wb-save"> Remember these steps as my template</label>' +
      '<p class="dk-hint" id="dk-wb-msg" role="status"></p>',
      '<button type="button" class="dk-btn dk-btn--primary" id="dk-wb-go">Create tasks</button>');
    var rows = $("dk-wb-rows");
    var renumber = function () {
      Array.prototype.forEach.call(rows.querySelectorAll(".dk-wb__row"), function (li, i) {
        li.setAttribute("data-wb", String(i));
        li.querySelector("[data-wbrm]").setAttribute("data-wbrm", String(i));
      });
      paintDues(d);
    };
    rows.addEventListener("input", function () { paintDues(d); });
    rows.addEventListener("click", function (e) {
      var b = e.target.closest("[data-wbrm]");
      if (b) { b.closest("li").remove(); renumber(); }
    });
    $("dk-wb-date").addEventListener("input", function () { paintDues(d); });
    $("dk-wb-add").addEventListener("click", function () {
      if (rows.children.length >= MAX_STEPS) { $("dk-wb-msg").textContent = "Up to " + MAX_STEPS + " steps."; return; }
      rows.insertAdjacentHTML("beforeend", rowHtml({ title: "", before: 0 }, rows.children.length));
      renumber();
      var last = rows.lastElementChild.querySelector(".dk-wb__title");
      if (last) last.focus();
    });
    $("dk-wb-reset").addEventListener("click", function () { rows.innerHTML = C.WORKBACK_DEFAULT.map(rowHtml).join(""); paintDues(d); });
    $("dk-wb-go").addEventListener("click", function () { create(d, ref); });
    paintDues(d);
  }

  function create(d, ref) {
    var a = A(), msg = $("dk-wb-msg"), title = $("dk-wb-title").value.trim() || ref.title, date = $("dk-wb-date").value;
    var tplRows = C.normTemplate(readRows(d)), plan = C.workBack(date, tplRows, a.today()).filter(function (s) { return !s.clamped; });
    if (!plan.length) return;
    $("dk-wb-go").disabled = true;
    msg.textContent = "Creating…";
    var note = "Work-back for " + title + " (deadline " + date + ")";
    var made = 0;
    var one = function (step) {
      var text = step.title + ": " + title;
      if (a.tasksReady()) return a.call("createTask", { title: text, due: step.due, notes: note }).then(function (r) { if (r.task && a.S.sync && a.S.sync.google) a.S.sync.google.tasks.push(r.task); made++; });
      return a.saveDeskTask(a.newId("t"), { title: text, due: step.due, time: "", done: false, notes: note, createdAt: new Date().toISOString(), tags: ["work-back"] }).then(function () { made++; });
    };
    plan.reduce(function (p, step) { return p.then(function () { return one(step); }); }, Promise.resolve()).then(function () {
      if ($("dk-wb-save").checked) a.savePrefs({ workback: tplRows });
      a.persist();
      a.render();
      d.close();
      a.toast(made + (made === 1 ? " task" : " tasks") + " created, working back from " + a.fmtDate(date, { day: "numeric", month: "short" }) + ".");
      if (a.tasksReady()) a.resync();
    }, function (err) {
      $("dk-wb-go").disabled = false;
      msg.textContent = (made ? made + " created, then: " : "") + err.message;
      a.render();
    });
  }

  Desk.workback = { open: open };
})();
