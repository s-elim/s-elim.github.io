/* ==========================================================================
   Research desk - pure logic (no DOM). Loaded before the UI scripts in
   assets/js/desk/ and tested in Node by workers/desk/test/core.test.mjs.
   Everything here takes plain data and returns plain data.
   ========================================================================== */
(function (root) {
  "use strict";

  var AXES = [
    { id: "perception", label: "Perception & 4D", color: "#0891b2", notionArea: "Robot Learning" },
    { id: "world", label: "World models", color: "#7c3aed", notionArea: "World Models" },
    { id: "policy", label: "VLA & policy", color: "#0d9488", notionArea: "VLA" },
    { id: "data", label: "Data & benchmarks", color: "#ca8a04", notionArea: "Robot Learning" },
    { id: "systems", label: "Agentic & systems", color: "#ea7317", notionArea: "Agentic Policy" }
  ];
  var KINDS = [
    { id: "idea", label: "Idea" },
    { id: "short", label: "Short-term plan" },
    { id: "long", label: "Long-term plan" },
    { id: "goal", label: "Goal" },
    { id: "target", label: "Target" }
  ];
  var STATUSES = [
    { id: "inbox", label: "Inbox" },
    { id: "shortlist", label: "Shortlist" },
    { id: "scoping", label: "Scoping" },
    { id: "active", label: "Active" },
    { id: "parked", label: "Parked" },
    { id: "done", label: "Done" }
  ];
  // Deadline sources and their colours. Notion sources not listed fall back to
  // the default so a new database needs no code.
  var SOURCE_COLORS = {
    Desk: "#2563eb", Conference: "#dc2626", Publications: "#0891b2", Opportunities: "#7c3aed",
    Projects: "#0d9488", Milestones: "#ea7317", "Follow-ups": "#64748b"
  };
  var DEFAULT_WATCH = ["CVPR", "ICCV", "ECCV", "NeurIPS", "ICLR", "ICML", "ICRA", "IROS", "RSS", "CoRL"];
  var WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  var MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

  function byId(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return list[0];
  }

  /* ---- dates (local calendar days; times as "HH:MM") ------------------ */
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function ymd(d) { return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()); }
  function parseYmd(s) {
    var p = String(s || "").split("-");
    return new Date(+p[0], (+p[1] || 1) - 1, +p[2] || 1);
  }
  function addDays(d, n) { var x = new Date(d.getFullYear(), d.getMonth(), d.getDate()); x.setDate(x.getDate() + n); return x; }
  function startOfWeek(d) { return addDays(d, -((d.getDay() + 6) % 7)); } // Monday
  function dayDiff(fromYmd, toYmd) {
    return Math.round((parseYmd(toYmd) - parseYmd(fromYmd)) / 864e5);
  }
  function isYmd(s) { return /^\d{4}-\d{2}-\d{2}$/.test(String(s || "")); }

  function countdown(days) {
    if (days === 0) return "today";
    if (days === 1) return "tomorrow";
    if (days === -1) return "yesterday";
    if (days < 0) return -days + " d ago";
    if (days < 60) return days + " d";
    return Math.round(days / 7) + " wk";
  }
  function urgency(days) {
    if (days < 0) return "past";
    if (days <= 3) return "hot";
    if (days <= 14) return "near";
    return "far";
  }

  /* ---- quick add -------------------------------------------------------
     "Draft rebuttal fri 14:00-15:30 #icra" -> title, date, start, end, tags.
     Unrecognised words stay in the title, so nothing typed is ever lost. */
  function parseTime(tok) {
    var m = /^(\d{1,2})(?::(\d{2}))?(am|pm)?$/i.exec(tok);
    if (!m) return "";
    var h = +m[1], min = m[2] ? +m[2] : 0, ap = (m[3] || "").toLowerCase();
    if (!m[2] && !ap) return ""; // a bare number is not a time
    if (ap === "pm" && h < 12) h += 12;
    if (ap === "am" && h === 12) h = 0;
    if (h > 23 || min > 59) return "";
    return pad2(h) + ":" + pad2(min);
  }
  function parseQuick(text, now) {
    now = now || new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var words = String(text || "").trim().split(/\s+/).filter(Boolean);
    var out = { title: "", date: "", start: "", end: "", tags: [] };
    var keep = [];
    for (var i = 0; i < words.length; i++) {
      var w = words[i], lw = w.toLowerCase(), m;
      if (/^#[\w-]{1,40}$/.test(w)) { out.tags.push(w.slice(1).toLowerCase()); continue; }
      if (!out.date) {
        if (lw === "today" || lw === "tod") { out.date = ymd(today); continue; }
        if (lw === "tomorrow" || lw === "tmr" || lw === "tmrw") { out.date = ymd(addDays(today, 1)); continue; }
        if (isYmd(w)) { out.date = w; continue; }
        if ((m = /^in$/.exec(lw)) && /^\d{1,3}[dw]$/i.test(words[i + 1] || "")) {
          var n = parseInt(words[i + 1], 10) * (/w$/i.test(words[i + 1]) ? 7 : 1);
          out.date = ymd(addDays(today, n)); i++; continue;
        }
        if ((m = /^(\d{1,2})\/(\d{1,2})$/.exec(w))) {
          var md = new Date(today.getFullYear(), +m[1] - 1, +m[2]);
          if (md < today) md = new Date(today.getFullYear() + 1, +m[1] - 1, +m[2]);
          out.date = ymd(md); continue;
        }
        var wd = WEEKDAYS.indexOf(lw.slice(0, 3));
        if (wd !== -1 && /^(sun|mon|tue|wed|thu|fri|sat)[a-z]*$/.test(lw)) {
          var ahead = (wd - today.getDay() + 7) % 7 || 7;
          if ((words[i - 1] || "").toLowerCase() === "next" && keep[keep.length - 1] && keep[keep.length - 1].toLowerCase() === "next") keep.pop();
          out.date = ymd(addDays(today, ahead)); continue;
        }
        var mo = MONTHS.indexOf(lw.slice(0, 3));
        if (mo !== -1 && /^[a-z]{3,9}$/.test(lw) && /^\d{1,2}$/.test(words[i + 1] || "")) {
          var dm = new Date(today.getFullYear(), mo, +words[i + 1]);
          if (dm < today) dm = new Date(today.getFullYear() + 1, mo, +words[i + 1]);
          out.date = ymd(dm); i++; continue;
        }
      }
      if (!out.start) {
        if ((m = /^([\d:apm]+)-([\d:apm]+)$/i.exec(w)) && parseTime(m[1]) && parseTime(m[2])) {
          out.start = parseTime(m[1]); out.end = parseTime(m[2]); continue;
        }
        var t = parseTime(w);
        if (t) { out.start = t; continue; }
      }
      keep.push(w);
    }
    out.title = keep.join(" ");
    return out;
  }

  /* ---- deadlines ------------------------------------------------------- */
  function conferenceDeadlines(confs, watched, fromYmd, toYmd) {
    var want = {};
    (watched || []).forEach(function (n) { want[String(n).toLowerCase()] = true; });
    var out = [];
    (confs || []).forEach(function (c) {
      if (!want[String(c.name || "").toLowerCase()]) return;
      (c.timeline || []).forEach(function (st) {
        if (!isYmd(st.date) || st.date < fromYmd || st.date > toYmd) return;
        out.push({
          key: "conf:" + c.name + ":" + c.edition + ":" + st.label,
          title: c.name + " " + c.edition + " " + st.label,
          date: st.date, time: st.time || "", tz: st.tz || "",
          source: "Conference", url: c.website || "", done: false, external: true
        });
      });
    });
    return out;
  }

  function collectDeadlines(opts) {
    var today = opts.today, horizon = opts.horizon || 120, back = opts.back == null ? 21 : opts.back;
    var from = ymd(addDays(parseYmd(today), -back)), to = ymd(addDays(parseYmd(today), horizon));
    var out = [];
    (opts.entries || []).forEach(function (e) {
      if (!isYmd(e.deadline)) return;
      out.push({
        key: "desk:" + e.id, title: e.title || "Untitled", date: e.deadline, time: "",
        source: "Desk", entryId: e.id, color: byId(AXES, e.axis).color,
        done: e.status === "done" || e.status === "parked"
      });
    });
    (opts.notion || []).forEach(function (src) {
      (src.rows || []).forEach(function (r) {
        var d = String(r.date || "").slice(0, 10);
        if (!isYmd(d)) return;
        out.push({
          key: "notion:" + r.id, title: r.title, date: d, time: String(r.date).length > 10 ? String(r.date).slice(11, 16) : "",
          source: src.label, url: r.url, status: r.status, done: !!r.done
        });
      });
    });
    out = out.concat(conferenceDeadlines(opts.conferences, opts.watched, from, to));
    out = out.filter(function (d) {
      if (d.date > to) return false;
      // A missed date of yours stays until it is marked done; a conference date
      // that has passed is simply gone.
      if (d.date < today) return !d.done && !d.external && d.date >= from;
      return true;
    });
    out.forEach(function (d) {
      d.days = dayDiff(today, d.date);
      d.color = d.color || SOURCE_COLORS[d.source] || "#475569";
      d.urgency = d.done ? "done" : urgency(d.days);
    });
    out.sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : (a.time || "99") < (b.time || "99") ? -1 : 1; });
    return out;
  }

  /* ---- events and tasks from the sync payload -------------------------- */
  function normEvent(ev) {
    if (!ev || !ev.start) return null;
    var allDay = !!ev.allDay || isYmd(ev.start);
    var start = allDay ? parseYmd(String(ev.start).slice(0, 10)) : new Date(ev.start);
    var end = ev.end ? (allDay ? parseYmd(String(ev.end).slice(0, 10)) : new Date(ev.end)) : null;
    if (isNaN(start.getTime())) return null;
    if (!end || isNaN(end.getTime()) || end <= start) end = allDay ? addDays(start, 1) : new Date(start.getTime() + 36e5);
    return {
      id: ev.id + "@" + (ev.calendarId || ""), title: ev.title || "(no title)", start: start, end: end, allDay: allDay,
      color: ev.color || "#3b82f6", calendar: ev.calendar || "", link: ev.link || "", video: ev.video || "",
      location: ev.location || "", description: ev.description || "", attendees: ev.attendees || 0
    };
  }
  // Does an event touch a given local day? All-day ends are exclusive.
  function eventOnDay(e, dayYmd) {
    var d0 = parseYmd(dayYmd), d1 = addDays(d0, 1);
    return e.start < d1 && e.end > d0;
  }

  function unifyTasks(google, desk) {
    var out = [];
    (google || []).forEach(function (t) {
      out.push({ key: "g:" + t.listId + ":" + t.id, source: "google", id: t.id, listId: t.listId, list: t.list || "",
        title: t.title, due: t.due || "", time: "", done: !!t.done, notes: t.notes || "", link: t.link || "", parent: t.parent || "",
        completed: t.completed || "" });
    });
    (desk || []).forEach(function (d) {
      var t = d.data || {};
      out.push({ key: "d:" + d.id, source: "desk", id: d.id, version: d.version, list: "Desk", title: t.title || "",
        due: t.due || "", time: t.time || "", done: !!t.done, notes: t.notes || "", completed: t.completedAt || "" });
    });
    return out;
  }
  function bucketTasks(tasks, today) {
    var b = { overdue: [], today: [], upcoming: [], undated: [], done: [] };
    tasks.forEach(function (t) {
      if (t.done) { if (String(t.completed).slice(0, 10) >= ymd(addDays(parseYmd(today), -1)) || t.due === today) b.done.push(t); return; }
      if (!t.due) b.undated.push(t);
      else if (t.due < today) b.overdue.push(t);
      else if (t.due === today) b.today.push(t);
      else b.upcoming.push(t);
    });
    var byDue = function (a, c) { return a.due < c.due ? -1 : a.due > c.due ? 1 : (a.time || "99") < (c.time || "99") ? -1 : 1; };
    b.overdue.sort(byDue); b.today.sort(byDue); b.upcoming.sort(byDue);
    return b;
  }

  /* ---- outbound links and text ---------------------------------------- */
  function compact(dateYmd, hhmm) { return dateYmd.replace(/-/g, "") + (hhmm ? "T" + hhmm.replace(":", "") + "00" : ""); }
  function gcalTemplateUrl(o) {
    var dates;
    if (o.allDay || !o.start) dates = compact(o.date) + "/" + compact(ymd(addDays(parseYmd(o.date), 1)));
    else dates = compact(o.date, o.start) + "/" + compact(o.date, o.end || o.start);
    var q = "action=TEMPLATE&text=" + encodeURIComponent(o.title || "") + "&dates=" + dates;
    if (o.details) q += "&details=" + encodeURIComponent(o.details.slice(0, 1500));
    if (o.tz) q += "&ctz=" + encodeURIComponent(o.tz);
    return "https://calendar.google.com/calendar/render?" + q;
  }

  function htmlToText(html) {
    return String(html || "")
      .replace(/<(br|\/p|\/div|\/li)\s*\/?>/gi, "\n")
      .replace(/<li[^>]*>/gi, "- ")
      .replace(/<[^>]+>/g, "")
      .replace(/&nbsp;/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&")
      .replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  var RT_FIELDS = ["thesis", "gap", "experiment", "risk"];
  var RT_LABEL = { thesis: "Thesis", gap: "Open question", experiment: "Plan", risk: "Risk" };

  function entryMarkdown(e) {
    var out = [];
    RT_FIELDS.forEach(function (f) { var t = htmlToText(e[f]); if (t) out.push("## " + RT_LABEL[f] + "\n\n" + t); });
    var meta = ["Type: " + byId(KINDS, e.kind).label, "Axis: " + byId(AXES, e.axis).label, "Conviction: " + (e.conviction || 3) + "/5"];
    if (e.venue) meta.push("Target venue: " + e.venue);
    if (e.deadline) meta.push("Deadline: " + e.deadline);
    if ((e.tags || []).length) meta.push("Tags: " + e.tags.join(", "));
    out.push("## Capture metadata\n\n" + meta.map(function (m) { return "- " + m; }).join("\n"));
    if (/^https?:\/\//i.test(e.sourceUrl || "")) out.push("Source: " + (e.sourceLabel ? e.sourceLabel + " " : "") + e.sourceUrl);
    else if (e.sourceLabel) out.push("Source: " + e.sourceLabel);
    return out.join("\n\n");
  }

  // Suggested values for a Notion form, keyed by column name. A suggestion is
  // used only when the column exists and, for selects, offers that option.
  function notionDefaults(e, fields) {
    var ax = byId(AXES, e.axis), s = e.status, c = e.conviction || 3;
    var guess = {
      Concept: ax.label, Novelty: htmlToText(e.gap), "Key Results": htmlToText(e.experiment),
      "Success metric": htmlToText(e.experiment), Notes: htmlToText(e.thesis), Area: ax.notionArea,
      Stage: s === "active" ? "Active" : s === "parked" ? "Parked" : (s === "scoping" || s === "shortlist") ? "Validating" : "Seed",
      Promise: c >= 4 ? "High" : c <= 2 ? "Low" : "Medium",
      Risk: c >= 4 ? "Low" : c <= 2 ? "High" : "Medium",
      Status: s === "done" ? "Done" : s === "active" ? "In progress" : s === "parked" ? "Dropped" : "Not started",
      Category: e.kind === "target" ? "Publication" : "Career move",
      Target: e.deadline || "", Deadline: e.deadline || ""
    };
    var out = {};
    (fields || []).forEach(function (f) {
      var v = guess[f.name];
      if (v == null || v === "" || f.type === "title") return;
      if ((f.type === "select" || f.type === "status") && f.options.indexOf(v) === -1) return;
      if (f.type === "date" && !isYmd(v)) return;
      out[f.name] = String(v).slice(0, 1800);
    });
    return out;
  }

  function normaliseEntry(id, d) {
    d = d || {};
    return {
      id: id, title: d.title || "", kind: d.kind || "idea", axis: d.axis || "policy", status: d.status || "inbox",
      conviction: Number(d.conviction) || 3, venue: d.venue || "", deadline: d.deadline || "",
      tags: Array.isArray(d.tags) ? d.tags : [], sourceLabel: d.sourceLabel || "", sourceUrl: d.sourceUrl || "",
      thesis: d.thesis || "", gap: d.gap || "", experiment: d.experiment || "", risk: d.risk || "",
      pinned: !!d.pinned, images: Array.isArray(d.images) ? d.images : [],
      notionUrl: d.notionUrl || "", calendarUrl: d.calendarUrl || "",
      addedAt: d.addedAt || "", updatedAt: d.updatedAt || ""
    };
  }

  var core = {
    AXES: AXES, KINDS: KINDS, STATUSES: STATUSES, SOURCE_COLORS: SOURCE_COLORS, DEFAULT_WATCH: DEFAULT_WATCH,
    RT_FIELDS: RT_FIELDS, RT_LABEL: RT_LABEL,
    byId: byId, pad2: pad2, ymd: ymd, parseYmd: parseYmd, addDays: addDays, startOfWeek: startOfWeek,
    dayDiff: dayDiff, isYmd: isYmd, countdown: countdown, urgency: urgency,
    parseTime: parseTime, parseQuick: parseQuick, conferenceDeadlines: conferenceDeadlines, collectDeadlines: collectDeadlines,
    normEvent: normEvent, eventOnDay: eventOnDay, unifyTasks: unifyTasks, bucketTasks: bucketTasks,
    gcalTemplateUrl: gcalTemplateUrl, htmlToText: htmlToText, entryMarkdown: entryMarkdown,
    notionDefaults: notionDefaults, normaliseEntry: normaliseEntry
  };
  if (typeof module !== "undefined" && module.exports) module.exports = core;
  else { root.Desk = root.Desk || {}; root.Desk.core = core; }
})(typeof window !== "undefined" ? window : this);
