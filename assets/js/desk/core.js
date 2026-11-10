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
  // Text colours and highlights, shared by the entry editor (tc-N / hl-N spans)
  // and the title styles on events and tasks. The swatch is only the button's
  // fill; the colours on the page come from _desk.scss, per theme.
  var TEXT_COLORS = [
    { n: 1, name: "Red", swatch: "hsl(2 62% 42%)" }, { n: 2, name: "Orange", swatch: "hsl(28 68% 42%)" },
    { n: 3, name: "Yellow", swatch: "hsl(46 72% 36%)" }, { n: 4, name: "Green", swatch: "hsl(150 50% 32%)" },
    { n: 5, name: "Blue", swatch: "hsl(206 60% 40%)" }, { n: 6, name: "Purple", swatch: "hsl(276 48% 44%)" }
  ];
  var HIGHLIGHTS = [
    { n: 1, name: "Yellow", swatch: "hsl(48 86% 72%)" }, { n: 2, name: "Green", swatch: "hsl(150 56% 72%)" },
    { n: 3, name: "Blue", swatch: "hsl(204 76% 76%)" }, { n: 4, name: "Pink", swatch: "hsl(318 66% 78%)" },
    { n: 5, name: "Red", swatch: "hsl(2 72% 78%)" }
  ];
  var WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  // Whole weekday names and their usual short forms only, so "monthly",
  // "wedding" or "sunset" are not read as days.
  var WEEKDAY_WORD = /^(sun(days?)?|mon(days?)?|tue(s(days?)?)?|wed(s|nesdays?)?|thu(r(s(days?)?)?)?|fri(days?)?|sat(urdays?)?)$/;
  // "mondays", "tuesdays"...: a plural weekday on an event means every week.
  var PLURAL_DAY = /^(sun|mon|tues|wednes|thurs|fri|satur)days$/;
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

  /* ---- clock arithmetic ("HH:MM" within one day) ------------------------ */
  function minutesOf(hhmm) { var p = String(hhmm || "").split(":"); return (+p[0] || 0) * 60 + (+p[1] || 0); }
  function hm(d) { return pad2(d.getHours()) + ":" + pad2(d.getMinutes()); }
  // An event never runs past midnight here, matching the backend's eventTimes().
  function addMinutes(hhmm, mins) {
    var t = Math.max(0, minutesOf(hhmm) + mins);
    if (t >= 24 * 60) return "23:59";
    return pad2(Math.floor(t / 60)) + ":" + pad2(t % 60);
  }
  function fmtDuration(mins) {
    if (mins < 60) return mins + " min";
    var h = Math.floor(mins / 60), r = mins % 60;
    return h + " h" + (r ? " " + pad2(r) : "");
  }
  function atMinutes(dayYmd, mins) { var d = parseYmd(dayYmd); d.setMinutes(mins); return d; }
  function roundUp(d, step) {
    var x = new Date(d.getTime());
    if (x.getSeconds() || x.getMilliseconds()) { x.setSeconds(0, 0); x.setMinutes(x.getMinutes() + 1); }
    var r = x.getMinutes() % step;
    if (r) x.setMinutes(x.getMinutes() + step - r);
    return x;
  }

  /* ---- quick add -------------------------------------------------------
     "Draft rebuttal fri 14:00-15:30 #icra" -> title, date, start, end, tags.
     Unrecognised words stay in the title, so nothing typed is ever lost. */
  // "45m", "90min", "1h", "1h30", "1h30m" -> minutes; anything else -> 0.
  function parseDuration(tok) {
    var m = /^(\d{1,2})h(?:(\d{1,2})m?)?$/i.exec(tok);
    if (m) return +m[1] * 60 + (+m[2] || 0);
    m = /^(\d{1,3})(?:m|min|mins)$/i.exec(tok);
    return m ? +m[1] : 0;
  }
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
  /* ---- repeating events --------------------------------------------------
     A repeat is { freq: DAILY|WEEKLY|MONTHLY, interval: 1-4, byday: [MO..] };
     the backend rebuilds the RRULE from these fields, never from free text. */
  var RRULE_DAYS = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];
  function normRepeat(r) {
    if (!r || ["DAILY", "WEEKLY", "MONTHLY"].indexOf(String(r.freq || "").toUpperCase()) === -1) return null;
    var out = { freq: String(r.freq).toUpperCase(), interval: Math.max(1, Math.min(4, parseInt(r.interval, 10) || 1)), byday: [] };
    if (out.freq === "WEEKLY") out.byday = (r.byday || []).map(String).filter(function (d) { return RRULE_DAYS.indexOf(d) !== -1; });
    return out;
  }
  function rrule(r, dateYmd) {
    r = normRepeat(r);
    if (!r) return "";
    var rule = "RRULE:FREQ=" + r.freq + (r.interval > 1 ? ";INTERVAL=" + r.interval : "");
    if (r.freq === "WEEKLY") rule += ";BYDAY=" + (r.byday.length ? r.byday : [RRULE_DAYS[parseYmd(dateYmd).getDay()]]).join(",");
    return rule;
  }
  // A weekly repeat's first occurrence has to fall on one of its days, or
  // Google adds a stray one on the start date: move the date forward to the
  // first listed weekday on or after it.
  function alignToDays(dateYmd, byday) {
    if (!isYmd(dateYmd) || !byday || !byday.length) return dateYmd;
    var d = parseYmd(dateYmd);
    for (var n = 0; n < 7 && byday.indexOf(RRULE_DAYS[d.getDay()]) === -1; n++) d = addDays(d, 1);
    return ymd(d);
  }
  function repeatLabel(r, dateYmd) {
    r = normRepeat(r);
    if (!r) return "";
    var names = { SU: "Sun", MO: "Mon", TU: "Tue", WE: "Wed", TH: "Thu", FR: "Fri", SA: "Sat" };
    if (r.freq === "DAILY") return r.interval > 1 ? "every " + r.interval + " days" : "daily";
    if (r.freq === "MONTHLY") return r.interval > 1 ? "every " + r.interval + " months" : "monthly";
    var days = r.byday.length ? r.byday : (isYmd(dateYmd) ? [RRULE_DAYS[parseYmd(dateYmd).getDay()]] : []);
    if (days.join() === "MO,TU,WE,TH,FR") return "weekdays";
    return (r.interval > 1 ? "every " + r.interval + " weeks" : "weekly") + (days.length ? " on " + days.map(function (d) { return names[d]; }).join(", ") : "");
  }

  /* ---- reminders -----------------------------------------------------------
     Timed events (normEvent objects) starting within `leadMin` minutes that
     have not been announced yet; `sent` maps "eventId|startISO" to a time. */
  function reminderKey(e) { return e.id + "|" + e.start.toISOString(); }
  function dueReminders(events, now, leadMin, sent) {
    var t = now.getTime(), lead = Math.max(1, leadMin || 10) * 60e3;
    return (events || []).filter(function (e) {
      if (!e || e.allDay || e.declined) return false;
      var dt = e.start.getTime() - t;
      return dt > -60e3 && dt <= lead && !(sent && sent[reminderKey(e)]);
    }).map(function (e) { return { event: e, key: reminderKey(e), minutes: Math.max(0, Math.round((e.start.getTime() - t) / 60e3)) }; });
  }

  // A time range such as "9-10pm", "9:30-10:30pm", "11-1pm", "9pm-10pm" or
  // "21:00-22:00". A meridiem written only on the end also applies to the
  // start, flipped if that would put the start after the end ("11-1pm" is
  // 11:00-13:00). An end before the start means the range runs past midnight
  // ("11pm-1am"), which the backend books into the next day.
  function parseTimeRange(tok) {
    var m = /^(\d{1,2}(?::\d{2})?)(am|pm)?-(\d{1,2}(?::\d{2})?)(am|pm)?$/i.exec(tok);
    if (!m) return null;
    var sAp = (m[2] || "").toLowerCase(), eAp = (m[4] || "").toLowerCase();
    var end = parseTime(m[3] + (eAp || (m[3].indexOf(":") === -1 ? sAp : "")));
    if (!end) return null;
    var start;
    if (sAp) start = parseTime(m[1] + sAp);
    else if (eAp) {
      start = parseTime(m[1] + eAp);
      if (start && start > end) start = parseTime(m[1] + (eAp === "pm" ? "am" : "pm"));
    } else start = parseTime(m[1]);
    return start ? { start: start, end: end } : null;
  }
  // Joins what people type with spaces back into single tokens before the
  // word scan: "9 pm" -> "9pm", "9pm - 10pm" / "9 to 10pm" / "9–10pm" -> "9pm-10pm".
  function tidyTimes(text) {
    return String(text || "")
      .replace(/\b(\d{1,2}(?::\d{2})?)\s+(am|pm)\b/gi, "$1$2")
      .replace(/\b(\d{1,2}(?::\d{2})?(?:am|pm)?)\s*(?:-|–|—|to)\s*(\d{1,2}(?::\d{2})?(?:am|pm)?)(?=\s|$)/gi, function (all, a, b) {
        return /[:apm]/i.test(a + b) ? a + "-" + b : all; // "3 to 5" alone stays words
      });
  }
  // opts.repeats: false leaves "daily", "every mon" etc. as words (tasks and
  // ideas cannot repeat, so their titles keep them).
  function parseQuick(text, now, opts) {
    now = now || new Date();
    var wantRepeat = !(opts && opts.repeats === false);
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var words = tidyTimes(text).trim().split(/\s+/).filter(Boolean);
    var out = { title: "", date: "", start: "", end: "", tags: [] };
    var keep = [], dur = null;
    for (var i = 0; i < words.length; i++) {
      var w = words[i], lw = w.toLowerCase(), m;
      if (/^#[\w-]{1,40}$/.test(w)) { out.tags.push(w.slice(1).toLowerCase()); continue; }
      if (wantRepeat && !out.repeat && PLURAL_DAY.test(lw)) {
        out.repeat = normRepeat({ freq: "WEEKLY", byday: [RRULE_DAYS[WEEKDAYS.indexOf(lw.slice(0, 3))]] });
        continue;
      }
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
        if (wd !== -1 && WEEKDAY_WORD.test(lw)) {
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
      if (wantRepeat && !out.repeat) {
        // "daily", "weekdays", "weekly", "biweekly", "monthly", "every day",
        // "every week", "every 2 weeks", "every other week", "every mon".
        var nextW = (words[i + 1] || "").toLowerCase(), afterW = (words[i + 2] || "").toLowerCase();
        var simple = { daily: { freq: "DAILY" }, weekdays: { freq: "WEEKLY", byday: ["MO", "TU", "WE", "TH", "FR"] },
          weekly: { freq: "WEEKLY" }, biweekly: { freq: "WEEKLY", interval: 2 }, fortnightly: { freq: "WEEKLY", interval: 2 }, monthly: { freq: "MONTHLY" } };
        if (Object.prototype.hasOwnProperty.call(simple, lw)) { out.repeat = normRepeat(simple[lw]); continue; }
        if (lw === "every") {
          var dayIdx = WEEKDAYS.indexOf(nextW.slice(0, 3));
          if (nextW === "day") { out.repeat = normRepeat({ freq: "DAILY" }); i++; continue; }
          if (nextW === "weekday") { out.repeat = normRepeat(simple.weekdays); i++; continue; }
          if (nextW === "week") { out.repeat = normRepeat({ freq: "WEEKLY" }); i++; continue; }
          if (nextW === "month") { out.repeat = normRepeat({ freq: "MONTHLY" }); i++; continue; }
          if ((nextW === "other" && afterW === "week") || (/^[2-4]$/.test(nextW) && /^weeks?$/.test(afterW))) {
            out.repeat = normRepeat({ freq: "WEEKLY", interval: nextW === "other" ? 2 : +nextW }); i += 2; continue;
          }
          if (dayIdx !== -1 && WEEKDAY_WORD.test(nextW)) {
            out.repeat = normRepeat({ freq: "WEEKLY", byday: [RRULE_DAYS[dayIdx]] });
            i++; continue;
          }
        }
      }
      if (!out.start) {
        var range = parseTimeRange(w);
        if (range) { out.start = range.start; out.end = range.end; continue; }
        var t = parseTime(w);
        if (t) { out.start = t; continue; }
      }
      if (!dur) {
        var withFor = lw === "for" && parseDuration(words[i + 1] || "");
        var mins = withFor || parseDuration(w);
        if (mins) {
          dur = { mins: mins, at: keep.length, words: withFor ? [w, words[i + 1]] : [w] };
          if (withFor) i++;
          continue;
        }
      }
      keep.push(w);
    }
    // A duration only means something after a start time; otherwise its words
    // go back into the title where they were typed.
    if (dur && out.start && !out.end) out.end = addMinutes(out.start, dur.mins);
    else if (dur) keep.splice.apply(keep, [dur.at, 0].concat(dur.words));
    out.title = keep.join(" ");
    // A repeat on set weekdays starts on the first of them from the typed date,
    // or from today ("every mon" typed on a Monday starts today).
    if (out.repeat && out.repeat.byday.length) out.date = alignToDays(out.date || ymd(today), out.repeat.byday);
    return out;
  }

  /* ---- free time ---------------------------------------------------------
     events are normEvent() objects; the planning window is local "HH:MM". */
  function freeSlots(events, dayYmd, opts) {
    opts = opts || {};
    var min = opts.min == null ? 30 : opts.min;
    var winStart = atMinutes(dayYmd, minutesOf(opts.start || "08:00"));
    var winEnd = atMinutes(dayYmd, minutesOf(opts.end || "22:00"));
    var from = opts.from && opts.from > winStart ? roundUp(opts.from, opts.step || 5) : winStart;
    var busy = (events || []).filter(function (e) { return e && !e.allDay && e.end > from && e.start < winEnd; })
      .map(function (e) { return [e.start < from ? from : e.start, e.end > winEnd ? winEnd : e.end]; })
      .sort(function (a, b) { return a[0] - b[0]; });
    var out = [], cursor = from;
    var push = function (s, e) {
      var mins = Math.round((e - s) / 6e4);
      if (mins >= min && mins > 0) out.push({ start: s, end: e, mins: mins });
    };
    busy.forEach(function (b) {
      if (b[0] > cursor) push(cursor, b[0]);
      if (b[1] > cursor) cursor = b[1];
    });
    if (winEnd > cursor) push(cursor, winEnd);
    return out;
  }

  // The timed event running at `now` that ends first, and the next to start.
  function nowNext(events, now) {
    var timed = (events || []).filter(function (e) { return e && !e.allDay; });
    var current = timed.filter(function (e) { return e.start <= now && e.end > now; }).sort(function (a, b) { return a.end - b.end; })[0] || null;
    var next = timed.filter(function (e) { return e.start > now; }).sort(function (a, b) { return a.start - b.start; })[0] || null;
    return { current: current, next: next };
  }

  // The first free block from `now` on, up to opts.length minutes long and at
  // least opts.min, starting on a quarter hour. Looks a week ahead at most.
  function planSlot(events, now, opts) {
    opts = opts || {};
    var length = opts.length || 60, min = opts.min || 30, step = opts.step || 15;
    for (var i = 0; i < (opts.days || 7); i++) {
      var day = ymd(addDays(now, i));
      var slots = freeSlots(events, day, { from: now, start: opts.start, end: opts.end, min: min });
      for (var j = 0; j < slots.length; j++) {
        var st = roundUp(slots[j].start, step), avail = Math.round((slots[j].end - st) / 6e4);
        if (avail >= min) return { date: day, start: hm(st), end: hm(new Date(st.getTime() + Math.min(length, avail) * 6e4)) };
      }
    }
    return null;
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
      location: ev.location || "", description: ev.description || "", attendees: ev.attendees || 0,
      eventId: ev.id, calendarId: ev.calendarId || "", editable: !!ev.editable, recurring: !!ev.recurring,
      series: ev.series || "", declined: !!ev.declined, taskKey: ev.taskKey || ""
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

  // The time blocks a task still has ahead of it, soonest first. A linked event
  // matches by key. One with no link (made before links existed) matches by
  // title, but only a one-off on a calendar you can write to: Block time could
  // have made that, and not somebody's weekly "Lab meeting".
  function taskBlocks(task, events, now) {
    var norm = function (s) { return String(s || "").trim().toLowerCase(); }, want = norm(task.title);
    return events.filter(function (e) {
      if (e.allDay || e.end <= now) return false;
      return e.taskKey ? e.taskKey === task.key : e.editable && !e.recurring && norm(e.title) === want;
    }).sort(function (a, b) { return a.start - b.start; });
  }

  /* ---- the agenda, day by day ------------------------------------------ */
  function agendaDay(date, opts) {
    return {
      date: date,
      events: (opts.events || []).filter(function (e) { return eventOnDay(e, date); }),
      tasks: (opts.tasks || []).filter(function (t) { return !t.done && t.due === date; }),
      deadlines: (opts.deadlines || []).filter(function (d) { return !d.done && d.date === date; })
    };
  }
  // One entry per day from opts.today on, for opts.days days.
  function agendaDays(opts) {
    var first = parseYmd(opts.today), out = [];
    for (var i = 0; i < opts.days; i++) out.push(agendaDay(ymd(addDays(first, i)), opts));
    return out;
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
    if (o.repeat && rrule(o.repeat, o.date)) q += "&recur=" + encodeURIComponent(rrule(o.repeat, o.date));
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
      pinned: !!d.pinned,
      // Older images carry a public Drive link; newer ones are private and are
      // fetched through the backend by id (editor.js, imageData).
      images: (Array.isArray(d.images) ? d.images : []).filter(function (im) {
        return im && typeof im === "object" && (/^https:\/\//.test(im.url || "") || (im.private === true && /^[\w-]{10,120}$/.test(String(im.id || ""))));
      }),
      notionUrl: d.notionUrl || "", calendarUrl: d.calendarUrl || "",
      addedAt: d.addedAt || "", updatedAt: d.updatedAt || ""
    };
  }

  /* ---- title styles on events and tasks ---------------------------------
     Google keeps titles as plain text, so colour, bold, italic, highlight and
     the star live on the desk: one map in the settings/marks document, keyed
     by markKey. A mark is { c: 1-6, h: 1-5, b, i, s, at: "YYYY-MM-DD" }. */
  var MARK_KEY_RE = /^(ev|g|d):/;
  // A repeating event's occurrences share one style: Google names an
  // occurrence "<series id>_<start>", and newer backends send the series id.
  function eventMarkKey(e) {
    var id = String(e.eventId || "");
    var series = e.series || (e.recurring ? id.replace(/_\d{8}(T\d{6}Z?)?$/, "") : "");
    return "ev:" + (series || id) + "@" + (e.calendarId || "");
  }
  function taskMarkKey(t) { return String(t.key || ""); }
  function isMarkKey(k) { return typeof k === "string" && k.length <= 400 && MARK_KEY_RE.test(k); }

  // A clean copy holding only known fields in range, or null when it styles nothing.
  function normMark(m) {
    if (!m || typeof m !== "object") return null;
    var out = {}, c = Number(m.c), h = Number(m.h);
    if (c >= 1 && c <= TEXT_COLORS.length && c % 1 === 0) out.c = c;
    if (h >= 1 && h <= HIGHLIGHTS.length && h % 1 === 0) out.h = h;
    if (m.b === true) out.b = true;
    if (m.i === true) out.i = true;
    if (m.s === true) out.s = true;
    if (!Object.keys(out).length) return null;
    if (isYmd(m.at)) out.at = m.at;
    return out;
  }
  function normMarks(items) {
    var out = {};
    if (!items || typeof items !== "object") return out;
    Object.keys(items).forEach(function (k) {
      var m = isMarkKey(k) && normMark(items[k]);
      if (m) out[k] = m;
    });
    return out;
  }
  // Classes for the span around a title. opts.text leaves out the highlight,
  // for a form field whose whole box would otherwise turn that colour.
  function markClass(m, opts) {
    m = normMark(m);
    if (!m) return "";
    var out = ["dk-mk"];
    if (m.b) out.push("is-b");
    if (m.i) out.push("is-i");
    if (m.s) out.push("is-star");
    if (m.c) out.push("tc-" + m.c);
    if (m.h && !(opts && opts.text)) out.push("hl-" + m.h);
    return out.join(" ");
  }
  // "at" is when the item was last seen: items in liveKeys get today, and a
  // style whose item has not been seen for keepDays (default 120) is dropped.
  // One with no date is kept. Pass liveKeys only from a complete sync.
  function pruneMarks(items, liveKeys, todayYmd, keepDays) {
    var live = {}, cutoff = ymd(addDays(parseYmd(todayYmd), -(keepDays == null ? 120 : keepDays)));
    (liveKeys || []).forEach(function (k) { live[k] = true; });
    var out = {};
    Object.keys(items || {}).forEach(function (k) {
      var m = items[k];
      if (live[k]) out[k] = Object.assign({}, m, { at: todayYmd });
      else if (!m.at || m.at >= cutoff) out[k] = m;
    });
    return out;
  }
  // Starred items first, otherwise in the order given.
  function starFirst(list, isStarred) {
    var top = [], rest = [];
    (list || []).forEach(function (x) { (isStarred(x) ? top : rest).push(x); });
    return top.concat(rest);
  }

  /* ---- command palette ----------------------------------------------------
     Subsequence match with bonuses for word starts and runs, so "mv tmr" finds
     "Move to tomorrow" and "gauss" finds "Review GaussVLA". 0 means no match. */
  function paletteScore(query, text) {
    var q = String(query || "").toLowerCase().replace(/\s+/g, " ").trim(), t = String(text || "").toLowerCase();
    if (!q) return 1;
    if (t.indexOf(q) !== -1) return 100 + (t.indexOf(q) === 0 ? 20 : 0) - Math.min(20, t.length / 10);
    var score = 0, ti = 0, run = 0;
    for (var qi = 0; qi < q.length; qi++) {
      var ch = q[qi];
      if (ch === " ") { run = 0; continue; }
      var at = t.indexOf(ch, ti);
      if (at === -1) return 0;
      var wordStart = at === 0 || /[\s\-_:(/]/.test(t[at - 1]);
      score += 2 + (wordStart ? 4 : 0) + (at === ti ? 1 + run : 0);
      run = at === ti ? run + 1 : 0;
      ti = at + 1;
    }
    return score;
  }
  // items: [{ label, keywords?, ... }]. Returns the best `limit` with a score.
  function paletteFilter(items, query, limit) {
    var out = [];
    (items || []).forEach(function (it, i) {
      var s = paletteScore(query, it.label + " " + (it.keywords || ""));
      if (s > 0) out.push({ item: it, score: s + (it.boost || 0), i: i });
    });
    out.sort(function (a, b) { return b.score - a.score || a.i - b.i; });
    return out.slice(0, limit || 12).map(function (x) { return x.item; });
  }

  /* ---- deadline work-back -------------------------------------------------
     A template is [{ title, before }] with `before` in days. Dates that would
     already have passed land on today, so nothing is created in the past. */
  var WORKBACK_DEFAULT = [
    { title: "Outline and related work", before: 28 },
    { title: "Freeze experiments", before: 14 },
    { title: "Full draft", before: 7 },
    { title: "Figures and tables final", before: 5 },
    { title: "Internal review", before: 3 },
    { title: "Polish and submit", before: 1 }
  ];
  function normTemplate(tpl) {
    return (Array.isArray(tpl) ? tpl : []).map(function (r) {
      return { title: String((r && r.title) || "").trim().slice(0, 200), before: Math.max(0, Math.min(365, Math.round(Number(r && r.before)) || 0)) };
    }).filter(function (r) { return r.title; });
  }
  function workBack(deadlineYmd, template, todayYmd) {
    if (!isYmd(deadlineYmd)) return [];
    var d = parseYmd(deadlineYmd);
    return normTemplate(template).map(function (r) {
      var due = ymd(addDays(d, -r.before)), late = isYmd(todayYmd) && due < todayYmd;
      return { title: r.title, before: r.before, due: late ? todayYmd : due, clamped: late };
    }).sort(function (a, b) { return a.due < b.due ? -1 : a.due > b.due ? 1 : b.before - a.before; });
  }

  /* ---- the week in review ---------------------------------------------- */
  function weekBounds(anchorYmd) {
    var s = startOfWeek(parseYmd(anchorYmd));
    return { from: ymd(s), to: ymd(addDays(s, 6)), start: s, end: addDays(s, 7) };
  }
  function minutesBetween(a, b) { return Math.max(0, Math.round((b - a) / 6e4)); }
  // opts: { week: "YYYY-MM-DD" (any day in it), today, events (normEvent), tasks (unified),
  // entries, deadlines (collectDeadlines), workday: { start, end } }
  function weekReview(opts) {
    var w = weekBounds(opts.week || opts.today), today = opts.today || w.from;
    var inWeek = function (ymdStr) { return ymdStr >= w.from && ymdStr <= w.to; };
    var events = (opts.events || []).filter(function (e) { return e && !e.allDay && e.start < w.end && e.end > w.start; });
    var byCal = {}, meetingMin = 0, blockMin = 0;
    events.forEach(function (e) {
      var s = e.start < w.start ? w.start : e.start, x = e.end > w.end ? w.end : e.end, m = minutesBetween(s, x);
      var cal = e.calendar || "Calendar";
      byCal[cal] = (byCal[cal] || 0) + m;
      if (e.taskKey) blockMin += m; else meetingMin += m;
    });
    var wd = opts.workday || { start: "08:00", end: "22:00" };
    var dayMin = Math.max(0, minutesOf(wd.end) - minutesOf(wd.start));
    var days = [];
    for (var i = 0; i < 7; i++) {
      var dayYmd = ymd(addDays(w.start, i));
      var dayEv = events.filter(function (e) { return eventOnDay(e, dayYmd); });
      var busy = dayEv.reduce(function (n, e) {
        var d0 = atMinutes(dayYmd, minutesOf(wd.start)), d1 = atMinutes(dayYmd, minutesOf(wd.end));
        var s = e.start < d0 ? d0 : e.start, x = e.end > d1 ? d1 : e.end;
        return n + (x > s ? minutesBetween(s, x) : 0);
      }, 0);
      days.push({ date: dayYmd, busy: busy, free: Math.max(0, dayMin - busy), events: dayEv.length, past: dayYmd < today, today: dayYmd === today });
    }
    var tasks = opts.tasks || [];
    var done = tasks.filter(function (t) { return t.done && inWeek(String(t.completed || "").slice(0, 10)); });
    var open = tasks.filter(function (t) { return !t.done && t.due && inWeek(t.due); });
    var slipped = tasks.filter(function (t) { return !t.done && t.due && t.due >= w.from && t.due < today; });
    var entries = opts.entries || [];
    var added = entries.filter(function (e) { return inWeek(String(e.addedAt || "").slice(0, 10)); });
    var changed = entries.filter(function (e) { return inWeek(String(e.updatedAt || "").slice(0, 10)) && !inWeek(String(e.addedAt || "").slice(0, 10)); });
    var deadlines = (opts.deadlines || []).filter(function (d) { return inWeek(d.date); });
    var nextWeek = weekBounds(ymd(addDays(w.start, 7)));
    var ahead = (opts.deadlines || []).filter(function (d) { return !d.done && d.date >= nextWeek.from && d.date <= nextWeek.to; });
    return {
      from: w.from, to: w.to, days: days,
      meetingMinutes: meetingMin, blockMinutes: blockMin, byCalendar: byCal,
      freeMinutes: days.reduce(function (n, d) { return n + d.free; }, 0),
      tasksDone: done, tasksOpen: open, tasksSlipped: slipped,
      entriesAdded: added, entriesChanged: changed,
      deadlines: deadlines, deadlinesAhead: ahead
    };
  }

  /* ---- [[title]] links between entries ---------------------------------
     Typed as [[Some title]] in a rich-text field; on save the text becomes a
     <span class="dk-ref" data-ref="id">title</span>, so a later rename of the
     target cannot break the link. Unknown titles stay as typed. */
  var REF_RE = /\[\[([^\[\]<>]{1,200})\]\]/g;
  function titleIndex(entries) {
    var idx = {};
    (entries || []).forEach(function (e) { var t = String(e.title || "").trim().toLowerCase(); if (t && !idx[t]) idx[t] = e.id; });
    return idx;
  }
  function escText(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  // Runs only over text between tags, never inside one.
  function linkRefs(html, entries, selfId) {
    var idx = titleIndex(entries);
    return String(html || "").split(/(<[^>]+>)/).map(function (part) {
      if (part.charAt(0) === "<") return part;
      return part.replace(REF_RE, function (all, raw) {
        var title = raw.trim(), id = idx[title.toLowerCase()];
        if (!id || id === selfId) return all;
        return '<span class="dk-ref" data-ref="' + escText(id) + '">' + escText(title) + '</span>';
      });
    }).join("");
  }
  function refsIn(html) {
    var out = [], re = /<span class="dk-ref" data-ref="([^"]+)">/g, m;
    while ((m = re.exec(String(html || "")))) if (out.indexOf(m[1]) === -1) out.push(m[1]);
    return out;
  }
  // Entries whose rich-text fields point at `id`.
  function backlinks(id, entries) {
    return (entries || []).filter(function (e) {
      if (e.id === id) return false;
      return RT_FIELDS.some(function (f) { return refsIn(e[f]).indexOf(id) !== -1; });
    });
  }
  // Shows each link with the target's current title; a missing target is marked.
  function refreshRefs(html, entries) {
    var byId = {};
    (entries || []).forEach(function (e) { byId[e.id] = e.title || "Untitled"; });
    return String(html || "").replace(/<span class="dk-ref" data-ref="([^"]+)">([\s\S]*?)<\/span>/g, function (all, id, text) {
      if (!byId[id]) return '<span class="dk-ref is-missing" data-ref="' + id + '">' + text + '</span>';
      return '<span class="dk-ref" data-ref="' + id + '">' + escText(byId[id]) + '</span>';
    });
  }

  /* ---- offline write queue ----------------------------------------------
     Items are { action, payload, at }. Puts to the same document fold into
     one, keeping the first baseVersion (what the device last saw from the
     server) and the latest data; a delete after puts replaces them. */
  function queueKey(it) {
    var p = it.payload || {};
    if (it.action === "put" || it.action === "delete") return it.action === "delete" ? "doc:" + p.collection + ":" + p.id : "doc:" + p.collection + ":" + p.id;
    if (it.action === "setTask") return "task:" + p.listId + ":" + p.id;
    if (it.action === "updateEvent") return "event:" + p.calendarId + ":" + p.id;
    return "";
  }
  function queueAdd(queue, item) {
    var list = (queue || []).slice(), key = queueKey(item);
    if (!key) return list.concat([item]);
    var i = -1;
    for (var j = 0; j < list.length; j++) if (queueKey(list[j]) === key) { i = j; }
    if (i === -1) return list.concat([item]);
    var prev = list[i], next = item;
    if (item.action === "put" && prev.action === "put") {
      next = { action: "put", at: item.at, payload: Object.assign({}, item.payload, { baseVersion: prev.payload.baseVersion }) };
    } else if (item.action === "setTask" && prev.action === "setTask") {
      next = { action: "setTask", at: item.at, payload: Object.assign({}, prev.payload, item.payload) };
    } else if (item.action === "updateEvent" && prev.action === "updateEvent") {
      next = { action: "updateEvent", at: item.at, payload: Object.assign({}, prev.payload, item.payload) };
    } else if (item.action === "delete" && prev.action === "put") {
      next = { action: "delete", at: item.at, payload: Object.assign({}, item.payload, { base: prev.payload.baseVersion }) };
    }
    list.splice(i, 1);
    return list.concat([next]);
  }

  // Plain text for the board search, built once per entry (plainFn turns
  // stored HTML into text).
  function entryHaystack(e, plainFn) {
    return [e.title, e.venue, e.sourceLabel, (e.tags || []).join(" ")].concat(RT_FIELDS.map(function (f) { return plainFn(e[f]); })).join(" ").toLowerCase();
  }

  var core = {
    AXES: AXES, KINDS: KINDS, STATUSES: STATUSES, SOURCE_COLORS: SOURCE_COLORS, DEFAULT_WATCH: DEFAULT_WATCH,
    paletteScore: paletteScore, paletteFilter: paletteFilter,
    WORKBACK_DEFAULT: WORKBACK_DEFAULT, normTemplate: normTemplate, workBack: workBack,
    weekBounds: weekBounds, weekReview: weekReview,
    linkRefs: linkRefs, refsIn: refsIn, backlinks: backlinks, refreshRefs: refreshRefs,
    queueKey: queueKey, queueAdd: queueAdd, entryHaystack: entryHaystack,
    RT_FIELDS: RT_FIELDS, RT_LABEL: RT_LABEL, TEXT_COLORS: TEXT_COLORS, HIGHLIGHTS: HIGHLIGHTS,
    eventMarkKey: eventMarkKey, taskMarkKey: taskMarkKey, isMarkKey: isMarkKey, normMark: normMark, normMarks: normMarks,
    markClass: markClass, pruneMarks: pruneMarks, starFirst: starFirst,
    byId: byId, pad2: pad2, ymd: ymd, parseYmd: parseYmd, addDays: addDays, startOfWeek: startOfWeek,
    dayDiff: dayDiff, isYmd: isYmd, countdown: countdown, urgency: urgency,
    minutesOf: minutesOf, addMinutes: addMinutes, fmtDuration: fmtDuration,
    parseTime: parseTime, parseTimeRange: parseTimeRange, parseDuration: parseDuration, parseQuick: parseQuick,
    normRepeat: normRepeat, rrule: rrule, repeatLabel: repeatLabel, alignToDays: alignToDays, reminderKey: reminderKey, dueReminders: dueReminders,
    freeSlots: freeSlots, nowNext: nowNext, planSlot: planSlot,
    conferenceDeadlines: conferenceDeadlines, collectDeadlines: collectDeadlines,
    normEvent: normEvent, eventOnDay: eventOnDay, unifyTasks: unifyTasks, bucketTasks: bucketTasks,
    taskBlocks: taskBlocks, agendaDays: agendaDays,
    gcalTemplateUrl: gcalTemplateUrl, htmlToText: htmlToText, entryMarkdown: entryMarkdown,
    notionDefaults: notionDefaults, normaliseEntry: normaliseEntry
  };
  if (typeof module !== "undefined" && module.exports) module.exports = core;
  else { root.Desk = root.Desk || {}; root.Desk.core = core; }
})(typeof window !== "undefined" ? window : this);
