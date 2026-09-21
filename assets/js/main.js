/* ==========================================================================
   Modern Academic theme - interactions (vanilla, no dependencies)
   ========================================================================== */
(function () {
  "use strict";

  var root = document.documentElement;
  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Theme toggle -------------------------------------------------- */
  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") return attr;
    return "light"; // site defaults to light; dark is opt-in via the toggle
  }
  function initTheme() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  /* ---- Mobile navigation (focus trap + ESC) -------------------------- */
  function initMobileNav() {
    var burger = document.getElementById("nav-burger");
    var menu = document.getElementById("mobile-menu");
    var overlay = document.getElementById("nav-overlay");
    var closeBtn = document.getElementById("mobile-menu-close");
    if (!burger || !menu || !overlay) return;

    var lastFocused = null;

    function focusable() {
      return menu.querySelectorAll('a[href], button:not([disabled])');
    }
    function open() {
      lastFocused = document.activeElement;
      menu.classList.add("is-open");
      overlay.classList.add("is-open");
      overlay.hidden = false;
      menu.setAttribute("aria-hidden", "false");
      burger.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      var f = focusable();
      if (f.length) f[0].focus();
      document.addEventListener("keydown", onKey);
    }
    function close() {
      menu.classList.remove("is-open");
      overlay.classList.remove("is-open");
      menu.setAttribute("aria-hidden", "true");
      burger.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKey);
      window.setTimeout(function () { overlay.hidden = true; }, 320);
      if (lastFocused) lastFocused.focus();
    }
    function onKey(e) {
      if (e.key === "Escape") { close(); return; }
      if (e.key === "Tab") {
        var f = focusable();
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }

    burger.addEventListener("click", open);
    overlay.addEventListener("click", close);
    if (closeBtn) closeBtn.addEventListener("click", close);
    menu.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", close); });
  }

  /* ---- Scroll reveal ------------------------------------------------- */
  function initReveal() {
    var els = document.querySelectorAll(".reveal");
    if (!els.length) return;
    if (prefersReduced || !("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---- Accordions ---------------------------------------------------- */
  function initAccordions() {
    document.querySelectorAll(".accordion__header").forEach(function (header) {
      header.setAttribute("aria-expanded", "false");
      header.addEventListener("click", function () {
        var item = header.closest(".accordion__item");
        var isOpen = item.classList.toggle("is-open");
        header.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });
    });
  }

  /* ---- Inline toggles (abstract / bibtex) ---------------------------- */
  function initToggles() {
    document.querySelectorAll(".js-toggle").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var target = document.querySelector(btn.getAttribute("data-target"));
        if (target) target.classList.toggle("open");
      });
    });
  }

  /* ---- Toast Notification ------------------------------------------- */
  function showCopyToast(msg) {
    var toast = document.getElementById("copy-toast");
    var msgSpan = document.getElementById("copy-toast-msg");
    if (!toast) return;
    if (msgSpan) msgSpan.textContent = msg || "Copied to clipboard!";
    toast.classList.add("show");
    window.setTimeout(function () { toast.classList.remove("show"); }, 2400);
  }

  /* ---- Copy BibTeX --------------------------------------------------- */
  function initCopy() {
    document.querySelectorAll(".js-copy").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var target = document.querySelector(btn.getAttribute("data-copy"));
        if (!target) return;
        var text = target.innerText;
        var done = function () {
          var label = btn.querySelector(".js-copy-label");
          var original = label ? label.textContent : null;
          btn.classList.add("copied");
          if (label) label.textContent = "Copied!";
          showCopyToast("BibTeX copied to clipboard!");
          window.setTimeout(function () {
            btn.classList.remove("copied");
            if (label && original !== null) label.textContent = original;
          }, 1600);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(function () {});
        } else {
          var ta = document.createElement("textarea");
          ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); done(); } catch (err) {}
          document.body.removeChild(ta);
        }
      });
    });
  }

  /* ---- Publications filter + search ---------------------------------- */
  /* ---- Shareable filter state in the URL ------------------------------ */
  // Filters live in the query string so a filtered view can be linked, bookmarked
  // and navigated back to, e.g. /publications/?type=journal,lead&year=2026
  function readQuery() {
    var out = {};
    var qs = window.location.search.replace(/^\?/, "");
    if (!qs) return out;
    qs.split("&").forEach(function (pair) {
      if (!pair) return;
      var kv = pair.split("=");
      var k = decodeURIComponent(kv[0]);
      var v = decodeURIComponent((kv[1] || "").replace(/\+/g, " "));
      if (k) out[k] = v;
    });
    return out;
  }

  function writeQuery(params) {
    if (!window.history || !window.history.replaceState) return;
    var parts = [];
    for (var k in params) {
      var v = params[k];
      if (v !== null && v !== undefined && v !== "") {
        parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(v));
      }
    }
    var url = window.location.pathname + (parts.length ? "?" + parts.join("&") : "") +
              window.location.hash;
    window.history.replaceState(null, "", url);
  }

  function initPubFilter() {
    var list = document.getElementById("pub-list");
    if (!list) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(".pub-card"));
    var sections = Array.prototype.slice.call(list.querySelectorAll(".pub-year-section"));
    var search = document.getElementById("pub-search");
    var empty = document.getElementById("pub-empty");
    var groups = {};

    document.querySelectorAll(".filter-chips[data-group]").forEach(function (g) {
      var groupName = g.getAttribute("data-group");
      groups[groupName] = []; // Empty array means "All" (no restriction)
      
      var allChip = g.querySelector('.filter-chip[data-value="all"]');
      var otherChips = g.querySelectorAll('.filter-chip:not([data-value="all"])');

      g.querySelectorAll(".filter-chip").forEach(function (chip) {
        // Toggle buttons need aria-pressed; the is-active class alone tells a
        // screen-reader user nothing about which filters are on.
        chip.setAttribute("aria-pressed", chip.classList.contains("is-active") ? "true" : "false");
        chip.addEventListener("click", function () {
          var val = chip.getAttribute("data-value");
          
          if (val === "all") {
            otherChips.forEach(function (c) { c.classList.remove("is-active"); });
            allChip.classList.add("is-active");
            groups[groupName] = [];
          } else {
            chip.classList.toggle("is-active");
            
            var selected = [];
            otherChips.forEach(function (c) {
              if (c.classList.contains("is-active")) {
                selected.push(c.getAttribute("data-value"));
              }
            });
            
            if (selected.length === 0) {
              allChip.classList.add("is-active");
              groups[groupName] = [];
            } else {
              allChip.classList.remove("is-active");
              groups[groupName] = selected;
            }
          }
          g.querySelectorAll(".filter-chip").forEach(function (c) {
            c.setAttribute("aria-pressed", c.classList.contains("is-active") ? "true" : "false");
          });
          apply();
        });
      });
    });

    function apply() {
      var term = (search && search.value || "").trim().toLowerCase();
      var shownTotal = 0;
      cards.forEach(function (card) {
        var ok = true;
        for (var key in groups) {
          var selectedVals = groups[key];
          if (selectedVals.length > 0) {
            if (key === "type") {
              var cardType = card.getAttribute("data-type");
              var cardAuthor = card.getAttribute("data-author");
              var typeMatch = selectedVals.indexOf(cardType) !== -1;
              var leadMatch = selectedVals.indexOf("lead") !== -1 && cardAuthor === "lead";
              var q1Match = selectedVals.indexOf("q1") !== -1 && card.getAttribute("data-q1") === "true";
              var toprankMatch = selectedVals.indexOf("toprank") !== -1 && card.getAttribute("data-toprank") === "true";
              if (!typeMatch && !leadMatch && !q1Match && !toprankMatch) {
                ok = false;
                break;
              }
            } else {
              var cardVal = card.getAttribute("data-" + key);
              if (selectedVals.indexOf(cardVal) === -1) {
                ok = false;
                break;
              }
            }
          }
        }
        if (ok && term) {
          ok = (card.getAttribute("data-search") || "").indexOf(term) !== -1;
        }
        card.hidden = !ok;
        if (ok) shownTotal++;
      });
      sections.forEach(function (sec) {
        var visible = sec.querySelectorAll(".pub-card:not([hidden])").length;
        sec.hidden = visible === 0;
        var count = sec.querySelector(".pub-year__count");
        if (count) count.textContent = visible;
      });
      var shown = document.getElementById("pub-shown");
      if (shown) shown.textContent = shownTotal;
      if (empty) empty.classList.toggle("show", shownTotal === 0);
      if (syncUrl) {
        var params = { q: term };
        for (var g in groups) params[g] = groups[g].join(",");
        writeQuery(params);
      }
    }

    // Restore any state carried in the URL before the first render.
    var syncUrl = false;
    var initial = readQuery();
    if (initial.q && search) search.value = initial.q;
    Object.keys(groups).forEach(function (groupName) {
      var raw = initial[groupName];
      if (!raw) return;
      var wanted = raw.split(",").filter(Boolean);
      var container = document.querySelector('.filter-chips[data-group="' + groupName + '"]');
      if (!container || !wanted.length) return;
      var matched = [];
      container.querySelectorAll('.filter-chip:not([data-value="all"])').forEach(function (c) {
        var on = wanted.indexOf(c.getAttribute("data-value")) !== -1;
        c.classList.toggle("is-active", on);
        if (on) matched.push(c.getAttribute("data-value"));
      });
      if (matched.length) {
        groups[groupName] = matched;
        var allChip = container.querySelector('.filter-chip[data-value="all"]');
        if (allChip) allChip.classList.remove("is-active");
      }
    });

    document.querySelectorAll(".filter-chip").forEach(function (c) {
      c.setAttribute("aria-pressed", c.classList.contains("is-active") ? "true" : "false");
    });

    if (search) search.addEventListener("input", apply);
    apply();
    syncUrl = true; // only mirror to the URL once the user drives it
  }

  /* ---- Publications toolbar: order, reset, bulk BibTeX ---------------- */
  // Deliberately thin: rather than reach into initPubFilter's state, Reset
  // clicks the same "All" chips a visitor would, so there is one code path for
  // clearing a filter and it cannot drift out of sync.
  function initPubTools() {
    var list = document.getElementById("pub-list");
    if (!list) return;
    var order = document.getElementById("pub-order");
    var reset = document.getElementById("pub-reset");
    var copyAll = document.getElementById("pub-copy-all");
    var search = document.getElementById("pub-search");

    function visibleBibtex() {
      var out = [];
      list.querySelectorAll(".pub-card:not([hidden]) .bibtex-block pre").forEach(function (pre) {
        var t = (pre.innerText || "").trim();
        if (t) out.push(t);
      });
      return out;
    }

    function syncCopyLabel() {
      if (!copyAll) return;
      var n = visibleBibtex().length;
      var label = copyAll.querySelector(".js-copy-label");
      if (label) label.textContent = "Copy " + n + " BibTeX";
      copyAll.disabled = n === 0;
    }

    function anyFilterActive() {
      if (search && search.value.trim()) return true;
      return !!document.querySelector('.filter-chip.is-active:not([data-value="all"])');
    }

    function syncReset() {
      if (reset) reset.disabled = !anyFilterActive();
    }

    if (order) {
      // The button reports the order currently applied, so a click flips to the
      // other one. The page ships newest-first, matching aria-pressed="false".
      order.addEventListener("click", function () {
        var toOldest = order.getAttribute("aria-pressed") !== "true";
        var secs = Array.prototype.slice.call(list.querySelectorAll(".pub-year-section"));
        secs.sort(function (a, b) {
          var ya = parseInt(a.getAttribute("data-year"), 10) || 0;
          var yb = parseInt(b.getAttribute("data-year"), 10) || 0;
          return toOldest ? ya - yb : yb - ya;
        });
        secs.forEach(function (sec) { list.appendChild(sec); });
        order.setAttribute("aria-pressed", toOldest ? "true" : "false");
        var lbl = order.querySelector(".pub-order__label");
        if (lbl) lbl.textContent = toOldest ? "Oldest first" : "Newest first";
        var ic = order.querySelector("i");
        if (ic) {
          ic.classList.toggle("fa-sort-amount-down", !toOldest);
          ic.classList.toggle("fa-sort-amount-up", toOldest);
        }
      });
    }

    if (reset) {
      reset.addEventListener("click", function () {
        document.querySelectorAll('.filter-chip[data-value="all"]').forEach(function (c) { c.click(); });
        if (search && search.value) {
          search.value = "";
          search.dispatchEvent(new Event("input"));
        }
        search && search.focus();
      });
    }

    if (copyAll) {
      copyAll.addEventListener("click", function () {
        var entries = visibleBibtex();
        if (!entries.length) return;
        var text = entries.join("\n\n") + "\n";
        var done = function () {
          showCopyToast(entries.length + " BibTeX " +
            (entries.length === 1 ? "entry" : "entries") + " copied to clipboard!");
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(function () {});
        } else {
          var ta = document.createElement("textarea");
          ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); done(); } catch (err) {}
          document.body.removeChild(ta);
        }
      });
    }

    // The filter owns the card visibility; watch its result counter rather than
    // every card, so re-syncing costs one observed node.
    var shown = document.getElementById("pub-shown");
    if (shown && window.MutationObserver) {
      new MutationObserver(function () { syncCopyLabel(); syncReset(); })
        .observe(shown, { childList: true, characterData: true, subtree: true });
    }
    document.querySelectorAll(".filter-chips").forEach(function (g) {
      g.addEventListener("click", function () {
        window.setTimeout(function () { syncCopyLabel(); syncReset(); }, 0);
      });
    });
    if (search) search.addEventListener("input", syncReset);
    syncCopyLabel();
    syncReset();
  }

  /* ---- Activities filter (fun-time) ----------------------------------- */
  function initActivityFilter() {
    var list = document.getElementById("activity-list");
    var chipsWrap = document.getElementById("activity-filters");
    if (!list || !chipsWrap) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(".activity-card"));
    var sections = Array.prototype.slice.call(list.querySelectorAll(".activity-year"));
    var empty = document.getElementById("activity-empty");

    var allChip = chipsWrap.querySelector('.filter-chip[data-value="all"]');
    var otherChips = chipsWrap.querySelectorAll('.filter-chip:not([data-value="all"])');
    var selectedVals = [];

    function apply() {
      var anyVisible = false;
      cards.forEach(function (card) {
        var ok = selectedVals.length === 0 || selectedVals.indexOf(card.getAttribute("data-cat")) !== -1;
        card.hidden = !ok;
        if (ok) anyVisible = true;
      });
      sections.forEach(function (sec) {
        sec.hidden = sec.querySelectorAll(".activity-card:not([hidden])").length === 0;
      });
      if (empty) empty.classList.toggle("show", !anyVisible);
    }

    chipsWrap.querySelectorAll(".filter-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var val = chip.getAttribute("data-value");
        if (val === "all") {
          otherChips.forEach(function (c) { c.classList.remove("is-active"); });
          allChip.classList.add("is-active");
          selectedVals = [];
        } else {
          chip.classList.toggle("is-active");
          var selected = [];
          otherChips.forEach(function (c) {
            if (c.classList.contains("is-active")) {
              selected.push(c.getAttribute("data-value"));
            }
          });
          if (selected.length === 0) {
            allChip.classList.add("is-active");
            selectedVals = [];
          } else {
            allChip.classList.remove("is-active");
            selectedVals = selected;
          }
        }
        apply();
      });
    });
  }

  /* ---- Updates card scroll hint (homepage) ---------------------------- */
  function initUpdatesScroll() {
    var scroller = document.getElementById("updates-scroll");
    if (!scroller) return;
    var card = scroller.closest(".updates-card");
    function check() {
      var atEnd = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4;
      card.classList.toggle("is-at-end", atEnd);
    }
    scroller.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check);
    check();
  }

  /* ---- Figure lightbox (publication thumbnails) ----------------------- */
  function initLightbox() {
    var triggers = Array.prototype.slice.call(document.querySelectorAll(".js-lightbox"));
    if (!triggers.length) return;
    var box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Figure preview");
    box.innerHTML = '<img alt=""><p class="lightbox__caption"></p>';
    document.body.appendChild(box);
    var img = box.querySelector("img");
    var cap = box.querySelector(".lightbox__caption");
    var lastTrigger = null;

    function close() {
      if (!box.classList.contains("is-open")) return;
      box.classList.remove("is-open");
      document.body.style.overflow = "";
      if (lastTrigger) { lastTrigger.focus(); lastTrigger = null; }
    }
    triggers.forEach(function (t) {
      t.addEventListener("click", function () {
        lastTrigger = t;
        img.src = t.getAttribute("data-full");
        img.alt = t.getAttribute("data-caption") || "";
        cap.textContent = t.getAttribute("data-caption") || "";
        box.classList.add("is-open");
        document.body.style.overflow = "hidden";
      });
    });
    box.addEventListener("click", close);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
  }

  /* ---- Modal popups (About on the home page) -------------------------- */
  function initModals() {
    var openers = Array.prototype.slice.call(document.querySelectorAll(".js-modal-open"));
    if (!openers.length) return;

    openers.forEach(function (btn) {
      var modal = document.querySelector(btn.getAttribute("data-modal-target"));
      if (!modal) return;
      var lastFocused = null;

      function focusable() {
        return modal.querySelectorAll('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([tabindex="-1"]), select:not([disabled])');
      }
      function open() {
        lastFocused = document.activeElement;
        modal.classList.add("is-open");
        document.body.style.overflow = "hidden";
        var closeBtn = modal.querySelector(".js-modal-close");
        if (closeBtn) closeBtn.focus();
        document.addEventListener("keydown", onKey);
      }
      function close() {
        modal.classList.remove("is-open");
        document.body.style.overflow = "";
        document.removeEventListener("keydown", onKey);
        if (lastFocused) { lastFocused.focus(); lastFocused = null; }
      }
      function onKey(e) {
        if (e.key === "Escape") { close(); return; }
        if (e.key === "Tab") {
          var f = focusable();
          if (!f.length) return;
          var first = f[0], last = f[f.length - 1];
          if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
          else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
      }

      btn.addEventListener("click", open);
      modal.addEventListener("click", function (e) {
        if (e.target === modal || e.target.closest(".js-modal-close")) close();
      });
    });
  }

  /* ---- Deadline helpers ---------------------------------------------- */
  // Shared by the full tracker on /deadlines/ and the home page hero badge.
  var DL_MS_DAY = 86400000;

  function dlPad(n) { return n < 10 ? "0" + n : String(n); }

  // A stage's date and clock time are read in the timezone its data names, so
  // a deadline lands on the same instant for every viewer. Minutes east of UTC
  // for the fixed labels; PT and ET follow daylight saving through Intl. A
  // stage with no tz, or a label not listed here, is read on the viewer's own
  // clock.
  var DL_FIXED_TZ = {
    AOE: -720, UTC: 0, GMT: 0, PST: -480, PDT: -420, EST: -300, EDT: -240,
    CET: 60, CEST: 120, BST: 60, JST: 540, KST: 540
  };
  var DL_ZONE_TZ = { PT: "America/Los_Angeles", ET: "America/New_York" };

  // Minutes east of UTC for an IANA zone at the instant `ms`.
  function dlZoneOffset(zone, ms) {
    var p = {};
    new Intl.DateTimeFormat("en-US", {
      timeZone: zone, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric",
      hour: "numeric", minute: "numeric", second: "numeric"
    }).formatToParts(new Date(ms)).forEach(function (x) { p[x.type] = x.value; });
    return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - ms) / 60000;
  }

  // ("2026-11-16", "23:59", "AoE") -> epoch ms; null when the date is not
  // YYYY-MM-DD (a "tba" stage). The time defaults to 23:59.
  function dlInstant(date, time, tz) {
    var d = String(date || "").split("-");
    if (d.length !== 3) return null;
    var t = String(time || "23:59").split(":");
    var y = parseInt(d[0], 10), mo = parseInt(d[1], 10) - 1, day = parseInt(d[2], 10);
    var h = parseInt(t[0], 10) || 0, mi = parseInt(t[1], 10) || 0;
    // The wall-clock reading as if it were UTC; each zone shifts it by its offset.
    var wall = Date.UTC(y, mo, day, h, mi, 0);
    var key = String(tz || "").trim().toUpperCase();

    var num = /^(?:UTC|GMT)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$/.exec(key);
    if (num) {
      var mins = parseInt(num[2], 10) * 60 + (parseInt(num[3], 10) || 0);
      return wall - (num[1] === "-" ? -mins : mins) * 60000;
    }
    if (DL_FIXED_TZ.hasOwnProperty(key)) return wall - DL_FIXED_TZ[key] * 60000;
    if (DL_ZONE_TZ.hasOwnProperty(key) && window.Intl) {
      try {
        // Two passes so a date near a daylight-saving switch takes the offset
        // in force at the deadline itself.
        var guess = wall - dlZoneOffset(DL_ZONE_TZ[key], wall) * 60000;
        return wall - dlZoneOffset(DL_ZONE_TZ[key], guess) * 60000;
      } catch (e) { /* no zone data: fall back to the viewer's clock */ }
    }
    return new Date(y, mo, day, h, mi, 0).getTime();
  }

  // Coarse above a day, live clock below it - the same read on both pages.
  function dlHumanGap(ms) {
    var days = Math.floor(ms / DL_MS_DAY);
    if (days >= 1) return days + (days === 1 ? " day" : " days");
    return dlPad(Math.floor((ms % DL_MS_DAY) / 3600000)) + ":" +
           dlPad(Math.floor((ms % 3600000) / 60000)) + ":" +
           dlPad(Math.floor((ms % 60000) / 1000));
  }

  function dlBadgeMarkup(name, gap, urgent) {
    return '<span class="deadline-pill deadline-pill--' + (urgent ? "urgent" : "soon") +
           '" style="font-size: 0.72em; padding: 1px 7px;">' +
           name + " &middot; " + gap + "</span>";
  }

  /* ---- AI Conference Deadline Tracker -------------------------------- */
  // Cards are rendered by Jekyll from _data/conferences.yml; this drives the
  // live countdowns, urgency states, filtering, sorting and the hero badge.
  function initDeadlineTracker() {
    var grid = document.getElementById("deadlines-grid");
    if (!grid) return;

    var cards = Array.prototype.slice.call(grid.querySelectorAll(".dl-card"));
    if (!cards.length) return;

    var MS_DAY = 86400000;
    var searchInput = document.getElementById("deadline-search");
    var openOnlyBtn = document.getElementById("deadline-open-only");
    var ticker = document.getElementById("deadlines-ticker");
    var emptyMsg = document.getElementById("deadlines-empty");
    var heroBadge = document.getElementById("deadlines-next-badge");

    var state = { category: "all", rank: "all", query: "", openOnly: false, view: "grid" };

    // ---- Parse the Liquid-rendered stages once -----------------------------
    var models = cards.map(function (card) {
      var stages = Array.prototype.slice.call(card.querySelectorAll(".dl-stage")).map(function (el) {
        var at = dlInstant(el.getAttribute("data-date"), el.getAttribute("data-time"), el.getAttribute("data-tz"));
        var when = at === null ? null : new Date(at);
        return { el: el, when: when, label: el.querySelector(".dl-stage__label").textContent.trim() };
      });
      return {
        card: card,
        stages: stages,
        name: card.getAttribute("data-name") || "",
        search: [
          card.getAttribute("data-name"),
          card.getAttribute("data-location"),
          card.getAttribute("data-category")
        ].join(" ").toLowerCase(),
        category: card.getAttribute("data-category") || "",
        rank: card.getAttribute("data-rank") || "unranked",
        stageEl: card.querySelector(".dl-card__stage"),
        countEl: card.querySelector(".dl-card__count"),
        fillEl: card.querySelector(".dl-card__bar-fill"),
        // Sort key and urgency, refreshed on every tick.
        next: null,
        sortKey: Infinity
      };
    });

    var pad = dlPad;

    function bigNumber(value, unit) {
      return '<span class="dl-card__count-main">' + value + '</span>' +
             '<span class="dl-card__count-unit">' + unit + '</span>';
    }

    function clockFace(h, m, s) {
      return bigNumber(pad(h), "hrs") +
             '<span class="dl-card__count-sep">:</span>' + bigNumber(pad(m), "min") +
             '<span class="dl-card__count-sep">:</span>' + bigNumber(pad(s), "sec");
    }

    // ---- One tick: recompute every card's countdown ------------------------
    function tick() {
      var now = new Date();

      models.forEach(function (m) {
        var next = null;
        var prev = null;

        m.stages.forEach(function (st) {
          st.el.classList.remove("is-done", "is-next");
          if (!st.when) return;
          if (st.when.getTime() <= now.getTime()) {
            st.el.classList.add("is-done");
            prev = st;
          } else if (!next) {
            next = st;
          }
        });

        var hasTba = m.stages.some(function (st) { return !st.when; });
        m.card.classList.remove("dl-card--urgent", "dl-card--soon", "dl-card--closed", "dl-card--tba");
        m.next = next;

        if (next) {
          next.el.classList.add("is-next");
          var diff = next.when.getTime() - now.getTime();
          var days = Math.floor(diff / MS_DAY);
          var hrs = Math.floor((diff % MS_DAY) / 3600000);
          var mins = Math.floor((diff % 3600000) / 60000);
          var secs = Math.floor((diff % 60000) / 1000);

          m.sortKey = diff;
          m.stageEl.textContent = next.label;

          // Inside a day, show a ticking clock; otherwise days (+ hours when close).
          if (days < 1) {
            m.countEl.innerHTML = clockFace(hrs, mins, secs);
            m.card.classList.add("dl-card--urgent");
          } else if (days <= 7) {
            m.countEl.innerHTML = bigNumber(days, days === 1 ? "day" : "days") + bigNumber(pad(hrs), "hrs");
            m.card.classList.add("dl-card--urgent");
          } else if (days <= 30) {
            m.countEl.innerHTML = bigNumber(days, "days");
            m.card.classList.add("dl-card--soon");
          } else {
            m.countEl.innerHTML = bigNumber(days, "days");
          }

          // Fill the bar over the 180 days running up to the deadline.
          var pct = Math.max(0, Math.min(100, (1 - diff / (180 * MS_DAY)) * 100));
          m.fillEl.style.width = pct.toFixed(1) + "%";
        } else if (hasTba) {
          // Call not published yet: sort after everything dated, before closed.
          m.sortKey = Number.MAX_SAFE_INTEGER - 1;
          m.card.classList.add("dl-card--tba");
          m.stageEl.textContent = m.stages[m.stages.length - 1].label;
          m.countEl.innerHTML = '<span class="dl-card__count-main">Not announced</span>';
          m.fillEl.style.width = "0%";
        } else {
          m.sortKey = Number.MAX_SAFE_INTEGER;
          m.card.classList.add("dl-card--closed");
          m.stageEl.textContent = prev ? prev.label : "Closed";
          m.countEl.innerHTML = '<span class="dl-card__count-main">Closed</span>';
          m.fillEl.style.width = "100%";
        }
      });

      updateTicker();
    }

    // ---- Hero badge + "next up" strip --------------------------------------
    var humanGap = dlHumanGap;

    function updateTicker() {
      var open = models.filter(function (m) { return m.next; })
                       .sort(function (a, b) { return a.sortKey - b.sortKey; });
      if (!open.length) {
        if (ticker) ticker.hidden = true;
        return;
      }
      var soonest = open[0];
      var gap = humanGap(soonest.sortKey);
      var isClock = gap.indexOf(":") !== -1;

      if (ticker) {
        ticker.hidden = false;
        ticker.querySelector(".deadlines__ticker-body").innerHTML =
          "<strong>" + soonest.name + "</strong> &middot; " + soonest.next.label +
          " in <span class=\"dl-mono\">" + gap + "</span>" +
          (open.length > 1 ? ' <span class="text-muted">&middot; then ' + open[1].name +
            " in " + humanGap(open[1].sortKey) + "</span>" : "");
      }
      if (heroBadge) {
        heroBadge.innerHTML =
          dlBadgeMarkup(soonest.name, gap, isClock || soonest.sortKey <= 7 * MS_DAY);
      }
    }

    // ---- Filtering & sorting ------------------------------------------------
    function applyFilters() {
      var visible = 0;

      models.forEach(function (m) {
        var okCat = state.category === "all" || m.category === state.category;
        var okRank = state.rank === "all" || m.rank === state.rank;
        var okQuery = !state.query || m.search.indexOf(state.query) !== -1;
        // "Dated calls only" hides both lapsed calls and ones with no published
        // date, so the default grid is the venues you can actually count down to.
        var undated = m.card.classList.contains("dl-card--closed") ||
                      m.card.classList.contains("dl-card--tba");
        var okOpen = !state.openOnly || !undated;
        var show = okCat && okRank && okQuery && okOpen;

        m.card.classList.toggle("is-hidden", !show);
        if (show) visible++;
      });

      resort();

      if (emptyMsg) emptyMsg.hidden = visible > 0;
      updateCounts();
    }

    // Soonest deadline first, TBA next, closed last. Re-appending cards is only
    // worth it when the order actually moved, so compare against the last one.
    var lastOrder = "";
    function resort() {
      var ordered = models.slice().sort(function (a, b) {
        return a.sortKey - b.sortKey || a.name.localeCompare(b.name);
      });
      var sig = ordered.map(function (m) { return m.name; }).join("|");
      if (sig === lastOrder) return;
      lastOrder = sig;
      var frag = document.createDocumentFragment();
      ordered.forEach(function (m) { frag.appendChild(m.card); });
      grid.appendChild(frag);
    }

    function updateCounts() {
      var buckets = { all: 0, robotics: 0, vision: 0, aiml: 0, hci: 0 };
      models.forEach(function (m) {
        if (state.openOnly && (m.card.classList.contains("dl-card--closed") ||
                               m.card.classList.contains("dl-card--tba"))) return;
        buckets.all++;
        if (buckets[m.category] !== undefined) buckets[m.category]++;
      });
      document.querySelectorAll(".dl-pill[data-filter]").forEach(function (btn) {
        var key = btn.getAttribute("data-filter");
        var slot = btn.querySelector(".dl-pill__count");
        if (!slot) {
          slot = document.createElement("span");
          slot.className = "dl-pill__count";
          btn.appendChild(slot);
        }
        slot.textContent = buckets[key] === undefined ? "" : buckets[key];
      });
    }

    // ---- Controls ----------------------------------------------------------
    document.querySelectorAll(".dl-pill[data-filter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-pill[data-filter]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.category = btn.getAttribute("data-filter");
        applyFilters();
      });
    });

    document.querySelectorAll(".dl-seg[data-rank]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-rank]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.rank = btn.getAttribute("data-rank");
        applyFilters();
      });
    });

    document.querySelectorAll(".dl-seg[data-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-view]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.view = btn.getAttribute("data-view");
        grid.classList.toggle("is-list", state.view === "list");
      });
    });

    if (openOnlyBtn) {
      openOnlyBtn.addEventListener("click", function () {
        state.openOnly = !state.openOnly;
        openOnlyBtn.classList.toggle("is-active", state.openOnly);
        openOnlyBtn.setAttribute("aria-pressed", String(state.openOnly));
        applyFilters();
      });
    }

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = (searchInput.value || "").trim().toLowerCase();
        applyFilters();
      });
    }

    // Expand a card for the note, conference dates and the CFP link.
    grid.addEventListener("click", function (e) {
      var btn = e.target.closest(".js-dl-more");
      if (!btn) return;
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      panel.hidden = open;
    });

    function statusSignature() {
      return models.map(function (m) {
        return m.card.classList.contains("dl-card--closed") ? "c"
             : m.card.classList.contains("dl-card--tba") ? "t" : "o";
      }).join("");
    }

    tick();
    applyFilters();

    // A #conf-<slug> deep link (command palette, shared URL) may point at a card
    // the default filters hide, so relax them before scrolling to it.
    (function revealHashTarget() {
      var hash = window.location.hash;
      if (!hash || hash.indexOf("#conf-") !== 0) return;
      var target = document.getElementById(hash.slice(1));
      if (!target) return;
      state.category = "all";
      state.rank = "all";
      state.query = "";
      state.openOnly = false;
      if (searchInput) searchInput.value = "";
      if (openOnlyBtn) {
        openOnlyBtn.classList.remove("is-active");
        openOnlyBtn.setAttribute("aria-pressed", "false");
      }
      document.querySelectorAll(".dl-pill[data-filter]").forEach(function (b) {
        b.classList.toggle("is-active", b.getAttribute("data-filter") === "all");
      });
      document.querySelectorAll(".dl-seg[data-rank]").forEach(function (b) {
        b.classList.toggle("is-active", b.getAttribute("data-rank") === "all");
      });
      applyFilters();
      window.setTimeout(function () {
        target.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
        target.classList.add("is-linked");
      }, 120);
    })();

    var lastStatus = statusSignature();

    window.setInterval(function () {
      tick();
      var status = statusSignature();
      if (status !== lastStatus) {
        // A deadline just lapsed: visibility and counts need a full pass.
        lastStatus = status;
        applyFilters();
      } else {
        resort();
      }
    }, 1000);
  }

  /* ---- Home-page "next deadline" badge -------------------------------- */
  // The tracker itself lives on /deadlines/. The home page ships only a small
  // JSON payload (#deadlines-mini), so the hero link still counts down live
  // without carrying the whole section.
  function initDeadlineBadge() {
    var badge = document.getElementById("deadlines-next-badge");
    var payload = document.getElementById("deadlines-mini");
    if (!badge || !payload) return;

    var raw;
    try {
      raw = JSON.parse(payload.textContent || payload.innerHTML || "[]");
    } catch (e) {
      return;
    }
    if (!raw || !raw.length) return;

    // Read exactly as the tracker reads the same stages.
    var stages = [];
    raw.forEach(function (s) {
      var at = dlInstant(s.d, s.t, s.z);
      if (at !== null) stages.push({ name: s.n || "", when: at });
    });
    if (!stages.length) return;

    function render() {
      var now = Date.now();
      var next = null;
      stages.forEach(function (s) {
        if (s.when > now && (!next || s.when < next.when)) next = s;
      });
      if (!next) {
        badge.innerHTML = "";
        return;
      }
      var left = next.when - now;
      badge.innerHTML = dlBadgeMarkup(next.name, dlHumanGap(left), left <= 7 * DL_MS_DAY);
    }

    render();
    window.setInterval(render, 1000);
  }

  /* ---- Q1 Journal Explorer ------------------------------------------- */
  // Cards are rendered by Jekyll from _data/journals.yml on /journals/; this
  // drives domain filtering, search, the minimum-impact-factor slider, sorting
  // and the grid/list toggle.
  function initJournalExplorer() {
    var grid = document.getElementById("journals-grid");
    if (!grid) return;

    var cards = Array.prototype.slice.call(grid.querySelectorAll(".jr-card"));
    if (!cards.length) return;

    var searchInput = document.getElementById("journal-search");
    var jifInput = document.getElementById("journal-jif");
    var jifValue = document.getElementById("journal-jif-value");
    var emptyMsg = document.getElementById("journals-empty");
    var countEl = document.getElementById("journals-count");

    var state = { category: "all", query: "", minJif: 0, sort: "jif", view: "grid" };

    var models = cards.map(function (card) {
      return {
        card: card,
        category: card.getAttribute("data-category") || "",
        jif: parseFloat(card.getAttribute("data-jif")) || 0,
        name: card.getAttribute("data-name") || "",
        search: [
          card.getAttribute("data-name"),
          card.getAttribute("data-abbr"),
          card.getAttribute("data-issn"),
          card.getAttribute("data-publisher"),
          card.getAttribute("data-category")
        ].join(" ").toLowerCase()
      };
    });

    // Cap the slider at the highest impact factor actually present.
    var maxJif = models.reduce(function (m, x) { return Math.max(m, x.jif); }, 0);
    if (jifInput) jifInput.max = String(Math.ceil(maxJif));

    var lastOrder = "";
    function resort() {
      var ordered = models.slice().sort(function (a, b) {
        if (state.sort === "name") return a.name.localeCompare(b.name);
        return b.jif - a.jif || a.name.localeCompare(b.name);
      });
      var sig = state.sort + "|" + ordered.map(function (m) { return m.name; }).join("|");
      if (sig === lastOrder) return;
      lastOrder = sig;
      var frag = document.createDocumentFragment();
      ordered.forEach(function (m) { frag.appendChild(m.card); });
      grid.appendChild(frag);
    }

    function apply() {
      var visible = 0;
      models.forEach(function (m) {
        var show = (state.category === "all" || m.category === state.category) &&
                   (!state.query || m.search.indexOf(state.query) !== -1) &&
                   (m.jif >= state.minJif);
        m.card.classList.toggle("is-hidden", !show);
        if (show) visible++;
      });
      resort();
      if (emptyMsg) emptyMsg.hidden = visible > 0;
      if (countEl) {
        countEl.textContent = visible === models.length
          ? models.length + " journals"
          : visible + " of " + models.length + " journals";
      }
    }

    document.querySelectorAll(".dl-pill[data-jfilter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-pill[data-jfilter]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.category = btn.getAttribute("data-jfilter");
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-jsort]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-jsort]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.sort = btn.getAttribute("data-jsort");
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-jview]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-jview]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.view = btn.getAttribute("data-jview");
        grid.classList.toggle("is-list", state.view === "list");
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = (searchInput.value || "").trim().toLowerCase();
        apply();
      });
    }

    if (jifInput) {
      jifInput.addEventListener("input", function () {
        state.minJif = parseFloat(jifInput.value) || 0;
        if (jifValue) jifValue.textContent = state.minJif;
        apply();
      });
    }

    grid.addEventListener("click", function (e) {
      var btn = e.target.closest(".js-jr-more");
      if (!btn) return;
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      panel.hidden = open;
    });

    apply();
  }


  /* ---- Research Ideas board + mind map -------------------------------- */
  // Cards are rendered by Jekyll from _data/research_ideas.yml on
  // /research-ideas/. This drives theme and status filtering, search, sorting,
  // and the SVG mind map. The map is laid out deterministically (themes on a
  // ring around a root node, ideas fanned out in their theme's wedge) so the
  // same data always draws the same picture, and it is built the first time the
  // map view is opened rather than on every page load.
  var IM_NS = "http://www.w3.org/2000/svg";
  var IM_R_THEME_MIN = 210;  // smallest theme-ring radius
  var IM_R_GAP = 140;        // clearance between the theme ring and the first idea
  var IM_RING_STEP = 88;     // radial step between two ideas of the same theme
  var IM_CHAR_W = 6.2;       // idea label width per character at 11.5px
  var IM_THEME_CHAR_W = 7;   // theme label width per character at 12.5px bold
  var IM_LINE_CHARS = 20;    // wrap width of an idea label, in characters
  var IM_THEME_CHARS = 16;   // wrap width of a theme label, in characters
  var IM_NODE_H1 = 27;       // one-line idea box
  var IM_NODE_H2 = 40;       // two-line idea box

  // Label widths are estimated from character counts rather than measured with
  // getBBox: the map is often built while its panel is still hidden, where
  // getBBox reports zeros.

  function imEl(name, attrs) {
    var node = document.createElementNS(IM_NS, name);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    }
    return node;
  }

  // Greedy wrap into at most `maxLines` lines, ellipsised when it overflows.
  function imWrap(text, maxChars, maxLines) {
    var words = String(text || "").split(/\s+/);
    var lines = [];
    var line = "";
    words.forEach(function (w) {
      var candidate = line ? line + " " + w : w;
      if (candidate.length > maxChars && line) {
        lines.push(line);
        line = w;
      } else {
        line = candidate;
      }
    });
    if (line) lines.push(line);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      var last = lines[maxLines - 1];
      lines[maxLines - 1] = last.slice(0, Math.max(0, maxChars - 1)).replace(/\s+\S*$/, "") + "…";
    }
    return lines;
  }

  function initResearchIdeas() {
    var grid = document.getElementById("ideas-grid");
    if (!grid) return;

    var cards = Array.prototype.slice.call(grid.querySelectorAll(".idea-card"));
    if (!cards.length) return;

    var mapWrap = document.getElementById("idea-map");
    var svg = document.getElementById("idea-map-svg");
    var canvas = document.getElementById("idea-map-canvas");
    var panel = document.getElementById("idea-map-panel");
    var panelBody = panel ? panel.querySelector(".im-panel__body") : null;
    var searchInput = document.getElementById("idea-search");
    var emptyMsg = document.getElementById("ideas-empty");
    var countEl = document.getElementById("ideas-count");

    var graph = { themes: [], ideas: [] };
    var payload = document.getElementById("idea-graph");
    if (payload) {
      try { graph = JSON.parse(payload.textContent || payload.innerHTML); } catch (e) { graph = { themes: [], ideas: [] }; }
    }

    var themes = graph.themes || [];
    var themeById = {};
    var themeOrder = {};
    themes.forEach(function (t, i) { themeById[t.id] = t; themeOrder[t.id] = i; });

    var models = cards.map(function (card) {
      var id = card.getAttribute("data-id");
      return {
        id: id,
        card: card,
        theme: card.getAttribute("data-theme") || "",
        themes: (card.getAttribute("data-themes") || "").split(/\s+/),
        status: card.getAttribute("data-status") || "",
        priority: parseInt(card.getAttribute("data-priority"), 10) || 0,
        added: card.getAttribute("data-added") || "",
        title: card.getAttribute("data-title") || "",
        search: (card.getAttribute("data-search") || "").toLowerCase()
      };
    });
    var byId = {};
    models.forEach(function (m) { byId[m.id] = m; });

    var state = { theme: "all", status: "all", query: "", sort: "added", view: "cards" };
    var selected = null;

    /* -- filtering, sorting, counts -- */
    function matches(m) {
      return (state.theme === "all" || m.themes.indexOf(state.theme) !== -1) &&
             (state.status === "all" || m.status === state.status) &&
             (!state.query || m.search.indexOf(state.query) !== -1);
    }

    function resort() {
      var ordered = models.slice().sort(function (a, b) {
        if (state.sort === "priority") return b.priority - a.priority || b.added.localeCompare(a.added);
        if (state.sort === "theme") {
          var ta = themeOrder[a.theme], tb = themeOrder[b.theme];
          ta = (ta === undefined) ? 999 : ta;
          tb = (tb === undefined) ? 999 : tb;
          return ta - tb || b.priority - a.priority;
        }
        return b.added.localeCompare(a.added) || b.priority - a.priority;
      });
      var frag = document.createDocumentFragment();
      ordered.forEach(function (m) { frag.appendChild(m.card); });
      grid.appendChild(frag);
    }

    function apply() {
      var visible = 0;
      models.forEach(function (m) {
        var show = matches(m);
        m.visible = show;
        m.card.classList.toggle("is-hidden", !show);
        if (show) visible++;
      });
      resort();
      if (emptyMsg) emptyMsg.hidden = visible > 0 || state.view === "map";
      if (countEl) {
        countEl.textContent = visible === models.length
          ? models.length + (models.length === 1 ? " idea" : " ideas")
          : visible + " of " + models.length + " ideas";
      }
      if (state.view === "map") drawMap();
    }

    function syncThemePills() {
      document.querySelectorAll(".dl-pill[data-ifilter]").forEach(function (b) {
        b.classList.toggle("is-active", b.getAttribute("data-ifilter") === state.theme);
      });
    }

    /* -- mind map ------------------------------------------------------- */
    var view = null;      // current viewBox
    var baseView = null;  // the fitted viewBox, restored by the Fit button

    function setView(v) {
      view = v;
      svg.setAttribute("viewBox", v.x + " " + v.y + " " + v.w + " " + v.h);
    }

    function nodeGroup(cls, color, id) {
      var g = imEl("g", { "class": "im-node " + cls, tabindex: "0", role: "button" });
      if (color) g.style.setProperty("--idea-color", color);
      if (id) g.setAttribute("data-node", id);
      return g;
    }

    function drawMap() {
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      svg.classList.remove("is-focused");

      var edgeLayer = imEl("g", { "class": "im-edges" });
      var nodeLayer = imEl("g", { "class": "im-nodes" });
      svg.appendChild(edgeLayer);
      svg.appendChild(nodeLayer);

      // Every theme is drawn, including the empty ones: the taxonomy is the
      // point of the map, so a new idea has an obvious place to land.
      var ring = themes.slice();
      var known = {};
      ring.forEach(function (t) { known[t.id] = true; });
      (graph.ideas || []).forEach(function (g) {
        if (!known[g.theme]) {
          known[g.theme] = true;
          ring.push({ id: g.theme, label: g.theme, color: "#2563eb" });
        }
      });
      if (!ring.length) return;

      var visibleIdeas = (graph.ideas || []).filter(function (g) {
        var m = byId[g.id];
        return m && m.visible;
      });
      var perTheme = {};
      ring.forEach(function (t) { perTheme[t.id] = []; });
      visibleIdeas.forEach(function (g) { (perTheme[g.theme] || (perTheme[g.theme] = [])).push(g); });

      var cx = 0, cy = 0;
      var step = (Math.PI * 2) / ring.length;
      var points = {};   // node id -> {x, y}

      // Wrap every visible label first, then size the two rings so that the arc
      // between neighbouring spokes is always wider than the widest label they
      // carry. Adding themes or long titles pushes the rings out instead of
      // piling nodes on top of each other.
      var box = {};
      var maxIdeaW = 96;
      visibleIdeas.forEach(function (g) {
        var lines = imWrap(g.title, IM_LINE_CHARS, 2);
        var longest = lines.reduce(function (n, l) { return Math.max(n, l.length); }, 0);
        var w = Math.max(96, longest * IM_CHAR_W + 22);
        box[g.id] = { lines: lines, w: w, h: lines.length > 1 ? IM_NODE_H2 : IM_NODE_H1 };
        maxIdeaW = Math.max(maxIdeaW, w);
      });
      var maxThemeW = 0;
      var themeLines = {};
      ring.forEach(function (t) {
        var lines = imWrap(t.label, IM_THEME_CHARS, 2);
        themeLines[t.id] = lines;
        maxThemeW = Math.max(maxThemeW, lines.reduce(function (n, l) {
          return Math.max(n, l.length * IM_THEME_CHAR_W);
        }, 0));
      });
      // + 40 covers the label drawn below each disc: for the spokes at the top
      // of the ring that offset pulls the label inward, onto a shorter arc.
      var rTheme = Math.max(IM_R_THEME_MIN, (maxThemeW + 18) / step + 40);
      // The first idea ring clears both the disc and the widest theme label
      // beside it, so a long label never runs into the node next to it.
      var rIdea = Math.max(
        rTheme + Math.max(IM_R_GAP, maxThemeW / 2 + maxIdeaW / 2 + 20),
        (maxIdeaW + 26) / step
      );

      // Root
      var rootG = nodeGroup("im-node--root", null, "__root");
      rootG.appendChild(imEl("circle", { "class": "im-node__disc", r: 46, cx: 0, cy: 0 }));
      var rootT = imEl("text", { x: 0, y: 1, "text-anchor": "middle", "font-size": "13" });
      rootT.textContent = "Physical AI";
      rootG.appendChild(rootT);
      rootG.setAttribute("aria-label", "All themes. Activate to clear the theme filter.");
      nodeLayer.appendChild(rootG);

      var bounds = { minX: -90, maxX: 90, minY: -90, maxY: 90 };
      function grow(x, y, w, h) {
        bounds.minX = Math.min(bounds.minX, x - w);
        bounds.maxX = Math.max(bounds.maxX, x + w);
        bounds.minY = Math.min(bounds.minY, y - h);
        bounds.maxY = Math.max(bounds.maxY, y + h);
      }

      ring.forEach(function (t, i) {
        var ang = -Math.PI / 2 + i * step;
        var tx = cx + rTheme * Math.cos(ang);
        var ty = cy + rTheme * Math.sin(ang);
        points["t:" + t.id] = { x: tx, y: ty };
        var mine = perTheme[t.id] || [];

        // root -> theme
        var e0 = imEl("path", {
          "class": "im-edge im-edge--theme",
          "data-edge": "t:" + t.id,
          d: "M0,0 Q" + (tx * 0.5) + "," + (ty * 0.5) + " " + tx + "," + ty
        });
        e0.style.setProperty("--idea-color", t.color);
        edgeLayer.appendChild(e0);

        var g = nodeGroup("im-node--theme" + (mine.length ? "" : " im-node--empty"), t.color, "t:" + t.id);
        g.appendChild(imEl("circle", { "class": "im-node__disc", r: 21, cx: tx, cy: ty }));
        var cnt = imEl("text", { "class": "im-node__count", x: tx, y: ty + 1, "text-anchor": "middle" });
        cnt.textContent = String(mine.length);
        g.appendChild(cnt);
        themeLines[t.id].forEach(function (ln, k) {
          var lab = imEl("text", { x: tx, y: ty + 36 + k * 15, "text-anchor": "middle" });
          lab.textContent = ln;
          g.appendChild(lab);
        });
        g.setAttribute("aria-label", t.label + ", " + mine.length + " idea" + (mine.length === 1 ? "" : "s") + ". Activate to filter the board to this theme.");
        nodeLayer.appendChild(g);
        grow(tx, ty + 36 + (themeLines[t.id].length - 1) * 15, maxThemeW / 2 + 10, 30);

        mine.forEach(function (gi, j) {
          // Ideas stack straight out along their theme's spoke. The step is
          // projected onto the spoke direction: a branch pointing sideways has
          // to clear a node's width, one pointing up or down only its height.
          var spokeStep = Math.max(
            IM_RING_STEP,
            Math.abs(Math.cos(ang)) * (maxIdeaW + 14),
            Math.abs(Math.sin(ang)) * (IM_NODE_H2 + 14)
          );
          var rad = rIdea + j * spokeStep;
          var ix = cx + rad * Math.cos(ang);
          var iy = cy + rad * Math.sin(ang);
          points["i:" + gi.id] = { x: ix, y: iy };

          var e1 = imEl("path", {
            "class": "im-edge",
            "data-edge": "t:" + t.id,
            "data-edge2": "i:" + gi.id,
            d: "M" + tx + "," + ty + " L" + ix + "," + iy
          });
          e1.style.setProperty("--idea-color", t.color);
          edgeLayer.appendChild(e1);

          var lines = box[gi.id].lines;
          var w = box[gi.id].w;
          var h = box[gi.id].h;

          var ig = nodeGroup("im-node--idea", t.color, "i:" + gi.id);
          ig.appendChild(imEl("rect", {
            "class": "im-node__box",
            x: ix - w / 2, y: iy - h / 2, width: w, height: h
          }));
          lines.forEach(function (ln, k) {
            var y = iy + (k - (lines.length - 1) / 2) * 14;
            var tnode = imEl("text", { x: ix, y: y, "text-anchor": "middle" });
            tnode.textContent = ln;
            ig.appendChild(tnode);
          });
          ig.setAttribute("aria-label", gi.title + ". " + t.label + ", status " + gi.status + ". Activate to read the idea.");
          nodeLayer.appendChild(ig);
          grow(ix, iy, w / 2 + 12, h / 2 + 12);
        });
      });

      // Secondary themes and idea-to-idea links, drawn under everything else.
      var drawnPairs = {};
      visibleIdeas.forEach(function (gi) {
        var from = points["i:" + gi.id];
        if (!from) return;
        (gi.also || []).forEach(function (a) {
          var to = points["t:" + a];
          if (!to) return;
          var e = imEl("path", {
            "class": "im-edge im-edge--also",
            "data-edge": "i:" + gi.id,
            "data-edge2": "t:" + a,
            d: "M" + from.x + "," + from.y + " Q" + ((from.x + to.x) / 2 * 0.62) + "," + ((from.y + to.y) / 2 * 0.62) + " " + to.x + "," + to.y
          });
          var th = themeById[a];
          if (th) e.style.setProperty("--idea-color", th.color);
          edgeLayer.insertBefore(e, edgeLayer.firstChild);
        });
        (gi.related || []).forEach(function (rid) {
          var to = points["i:" + rid];
          var pair = [gi.id, rid].sort().join("|");
          if (!to || drawnPairs[pair]) return;   // one line per pair, either way round
          drawnPairs[pair] = true;
          var e = imEl("path", {
            "class": "im-edge im-edge--rel",
            "data-edge": "i:" + gi.id,
            "data-edge2": "i:" + rid,
            d: "M" + from.x + "," + from.y + " Q" + ((from.x + to.x) / 2 * 0.5) + "," + ((from.y + to.y) / 2 * 0.5) + " " + to.x + "," + to.y
          });
          edgeLayer.insertBefore(e, edgeLayer.firstChild);
        });
      });

      var pad = 40;
      var w = (bounds.maxX - bounds.minX) + pad * 2;
      var h = (bounds.maxY - bounds.minY) + pad * 2;
      baseView = { x: bounds.minX - pad, y: bounds.minY - pad, w: w, h: h };
      setView({ x: baseView.x, y: baseView.y, w: baseView.w, h: baseView.h });

      // A selected idea that a filter has just removed takes its panel with it.
      if (selected) {
        if (svg.querySelector('[data-node="' + selected + '"]')) highlight(selected, true);
        else closePanel();
      }
    }

    function fitMap() {
      if (!baseView) return;
      setView({ x: baseView.x, y: baseView.y, w: baseView.w, h: baseView.h });
    }

    /* -- highlight one branch -- */
    function clearHighlight() {
      svg.classList.remove("is-focused");
      svg.querySelectorAll(".is-lit").forEach(function (n) { n.classList.remove("is-lit"); });
      svg.querySelectorAll(".is-selected").forEach(function (n) { n.classList.remove("is-selected"); });
    }

    function highlight(nodeId, keepSelected) {
      clearHighlight();
      var node = svg.querySelector('[data-node="' + nodeId + '"]');
      if (!node) return;
      svg.classList.add("is-focused");
      node.classList.add("is-lit");
      if (keepSelected) node.classList.add("is-selected");
      svg.querySelectorAll(".im-edge").forEach(function (e) {
        var a = e.getAttribute("data-edge");
        var b = e.getAttribute("data-edge2");
        if (a === nodeId || b === nodeId) {
          e.classList.add("is-lit");
          [a, b].forEach(function (other) {
            if (!other || other === nodeId) return;
            var peer = svg.querySelector('[data-node="' + other + '"]');
            if (peer) peer.classList.add("is-lit");
          });
        }
      });
      // A theme keeps its own ideas lit; the root lights the whole ring.
      if (nodeId === "__root") {
        svg.classList.remove("is-focused");
      }
    }

    /* -- side panel ----------------------------------------------------- */
    function closePanel() {
      if (!panel) return;
      panel.hidden = true;
      if (panelBody) panelBody.innerHTML = "";
      selected = null;
      clearHighlight();
    }

    function openPanel(ideaId) {
      var m = byId[ideaId];
      if (!m || !panel || !panelBody) return;
      var th = themeById[m.theme] || { label: m.theme, color: "#2563eb" };
      panel.style.setProperty("--idea-color", th.color);
      panelBody.innerHTML = "";

      var head = document.createElement("div");
      head.className = "im-panel__head";
      var themeLine = document.createElement("span");
      themeLine.className = "im-panel__theme";
      themeLine.textContent = th.label;
      var title = document.createElement("h3");
      title.className = "im-panel__title";
      title.textContent = m.title;
      var status = document.createElement("span");
      status.className = "idea-status idea-status--" + m.status;
      status.textContent = m.status;
      head.appendChild(themeLine);
      head.appendChild(title);
      head.appendChild(status);
      panelBody.appendChild(head);

      var summary = m.card.querySelector(".idea-card__summary");
      if (summary) panelBody.appendChild(summary.cloneNode(true));

      var details = m.card.querySelector(".idea-card__details");
      if (details) {
        var copy = details.cloneNode(true);
        copy.removeAttribute("id");
        copy.hidden = false;
        panelBody.appendChild(copy);
      }

      var open = document.createElement("button");
      open.type = "button";
      open.className = "im-panel__open";
      open.innerHTML = '<i class="fas fa-arrow-right" aria-hidden="true"></i> Open the card';
      open.addEventListener("click", function () {
        setViewMode("cards");
        revealCard(ideaId);
      });
      panelBody.appendChild(open);

      panel.hidden = false;
      panel.scrollTop = 0;
      selected = "i:" + ideaId;
      highlight(selected, true);
    }

    function revealCard(ideaId) {
      var m = byId[ideaId];
      if (!m) return;
      var more = m.card.querySelector(".js-idea-more");
      var details = m.card.querySelector(".idea-card__details");
      if (more && details && details.hidden) {
        more.setAttribute("aria-expanded", "true");
        details.hidden = false;
      }
      m.card.classList.add("is-flash");
      window.setTimeout(function () { m.card.classList.remove("is-flash"); }, 2400);
      window.setTimeout(function () {
        m.card.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
      }, 60);
    }

    /* -- view switching -------------------------------------------------- */
    function setViewMode(mode) {
      state.view = mode;
      document.querySelectorAll(".dl-seg[data-iview]").forEach(function (b) {
        b.classList.toggle("is-active", b.getAttribute("data-iview") === mode);
      });
      if (mapWrap) mapWrap.hidden = mode !== "map";
      grid.hidden = mode === "map";
      if (mode === "map") {
        drawMap();
        if (emptyMsg) emptyMsg.hidden = true;
      } else {
        closePanel();
        apply();
      }
    }

    /* -- wiring ---------------------------------------------------------- */
    document.querySelectorAll(".dl-pill[data-ifilter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.theme = btn.getAttribute("data-ifilter");
        syncThemePills();
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-istatus]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-istatus]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.status = btn.getAttribute("data-istatus");
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-isort]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-isort]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.sort = btn.getAttribute("data-isort");
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-iview]").forEach(function (btn) {
      btn.addEventListener("click", function () { setViewMode(btn.getAttribute("data-iview")); });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = (searchInput.value || "").trim().toLowerCase();
        apply();
      });
    }

    grid.addEventListener("click", function (e) {
      var more = e.target.closest(".js-idea-more");
      if (more) {
        var pnl = document.getElementById(more.getAttribute("aria-controls"));
        if (!pnl) return;
        var open = more.getAttribute("aria-expanded") === "true";
        more.setAttribute("aria-expanded", String(!open));
        pnl.hidden = open;
        return;
      }
      var focus = e.target.closest(".js-idea-focus");
      if (focus) {
        var id = focus.getAttribute("data-focus");
        var m = byId[id];
        if (m && !m.visible) {          // clear filters so the node exists
          state.theme = "all";
          state.status = "all";
          state.query = "";
          if (searchInput) searchInput.value = "";
          syncThemePills();
          document.querySelectorAll(".dl-seg[data-istatus]").forEach(function (b) {
            b.classList.toggle("is-active", b.getAttribute("data-istatus") === "all");
          });
          apply();
        }
        setViewMode("map");
        openPanel(id);
      }
    });

    if (svg) {
      svg.addEventListener("click", function (e) {
        var node = e.target.closest(".im-node");
        if (!node) { closePanel(); return; }
        var id = node.getAttribute("data-node") || "";
        if (id === "__root") {
          state.theme = "all";
          syncThemePills();
          closePanel();
          apply();
        } else if (id.indexOf("t:") === 0) {
          state.theme = id.slice(2);
          syncThemePills();
          closePanel();
          apply();
        } else if (id.indexOf("i:") === 0) {
          openPanel(id.slice(2));
        }
      });

      svg.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        var node = e.target.closest(".im-node");
        if (!node) return;
        e.preventDefault();
        node.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      });

      svg.addEventListener("mouseover", function (e) {
        var node = e.target.closest(".im-node");
        if (!node || selected) return;
        highlight(node.getAttribute("data-node"), false);
      });
      svg.addEventListener("mouseleave", function () {
        if (!selected) clearHighlight();
      });
    }

    if (panel) {
      var closeBtn = panel.querySelector(".im-panel__close");
      if (closeBtn) closeBtn.addEventListener("click", closePanel);
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && panel && !panel.hidden) closePanel();
    });

    /* -- zoom and pan ----------------------------------------------------- */
    function zoomBy(factor, originX, originY) {
      if (!view) return;
      var w = Math.min(4200, Math.max(320, view.w * factor));
      var scale = w / view.w;
      var h = view.h * scale;
      setView({
        x: originX - (originX - view.x) * scale,
        y: originY - (originY - view.y) * scale,
        w: w,
        h: h
      });
    }

    function svgPoint(clientX, clientY) {
      var r = svg.getBoundingClientRect();
      if (!view || !r.width || !r.height) return { x: 0, y: 0 };
      return {
        x: view.x + ((clientX - r.left) / r.width) * view.w,
        y: view.y + ((clientY - r.top) / r.height) * view.h
      };
    }

    document.querySelectorAll(".im-btn[data-imap]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-imap");
        if (mode === "fit") { fitMap(); return; }
        if (!view) return;
        var mid = { x: view.x + view.w / 2, y: view.y + view.h / 2 };
        zoomBy(mode === "in" ? 0.8 : 1.25, mid.x, mid.y);
      });
    });

    if (canvas) {
      canvas.addEventListener("wheel", function (e) {
        if (!view) return;
        e.preventDefault();
        var p = svgPoint(e.clientX, e.clientY);
        zoomBy(e.deltaY > 0 ? 1.12 : 0.89, p.x, p.y);
      }, { passive: false });

      var drag = null;
      canvas.addEventListener("pointerdown", function (e) {
        if (e.target.closest(".im-node") || e.target.closest(".im-panel") || e.target.closest(".im-controls")) return;
        if (!view) return;
        drag = { x: e.clientX, y: e.clientY, view: { x: view.x, y: view.y, w: view.w, h: view.h } };
        canvas.classList.add("is-panning");
        canvas.setPointerCapture(e.pointerId);
      });
      canvas.addEventListener("pointermove", function (e) {
        if (!drag) return;
        var r = svg.getBoundingClientRect();
        if (!r.width || !r.height) return;
        var dx = ((e.clientX - drag.x) / r.width) * drag.view.w;
        var dy = ((e.clientY - drag.y) / r.height) * drag.view.h;
        setView({ x: drag.view.x - dx, y: drag.view.y - dy, w: drag.view.w, h: drag.view.h });
      });
      ["pointerup", "pointercancel", "pointerleave"].forEach(function (evt) {
        canvas.addEventListener(evt, function () {
          drag = null;
          canvas.classList.remove("is-panning");
        });
      });
    }

    /* -- first paint and deep links --------------------------------------- */
    apply();

    var hash = window.location.hash || "";
    if (hash.indexOf("#idea-") === 0) {
      var wanted = hash.slice(6);
      if (byId[wanted]) revealCard(wanted);
    } else if (hash === "#map") {
      setViewMode("map");
    }
  }

  /* ---- Resources Library ---------------------------------------------- */
  // The boxed directory at the top of /research-ideas/, rendered by Jekyll
  // from _data/link_library.yml. Filters by section, by kind and by text, keeps
  // the per-section counts honest, and collapses sections that go empty.
  function initLinkLibrary() {
    var wrap = document.getElementById("links-groups");
    if (!wrap) return;

    var rows = Array.prototype.slice.call(wrap.querySelectorAll(".lk"));
    if (!rows.length) return;

    var groups = Array.prototype.slice.call(wrap.querySelectorAll(".lg"));
    var searchInput = document.getElementById("link-search");
    var emptyMsg = document.getElementById("links-empty");
    var countEl = document.getElementById("links-count");
    var collapseBtn = document.getElementById("links-collapse");

    var models = rows.map(function (row) {
      var section = row.closest(".lg");
      return {
        row: row,
        group: section ? section.getAttribute("data-group") : "",
        kind: row.getAttribute("data-kind") || "",
        search: (row.getAttribute("data-search") || "").toLowerCase()
      };
    });

    var state = { group: "all", kind: "all", query: "" };

    function setOpen(section, open) {
      var head = section.querySelector(".lg__head");
      var body = section.querySelector(".lg__body");
      if (!head || !body) return;
      head.setAttribute("aria-expanded", String(open));
      body.hidden = !open;
    }

    function apply() {
      var total = 0;
      models.forEach(function (m) {
        var show = (state.group === "all" || m.group === state.group) &&
                   (state.kind === "all" || m.kind === state.kind) &&
                   (!state.query || m.search.indexOf(state.query) !== -1);
        m.row.classList.toggle("is-hidden", !show);
        if (show) total++;
      });

      groups.forEach(function (section) {
        var visible = section.querySelectorAll(".lk:not(.is-hidden)").length;
        var counter = section.querySelector("[data-lg-count]");
        if (counter) counter.textContent = visible;
        section.classList.toggle("is-hidden", visible === 0);
        // A search should surface its hits, not leave them behind a collapsed
        // header; clearing the box leaves the sections as the reader left them.
        if (state.query && visible) setOpen(section, true);
      });

      if (emptyMsg) emptyMsg.hidden = total > 0;
      if (countEl) {
        countEl.textContent = total === models.length
          ? models.length + " links"
          : total + " of " + models.length + " links";
      }
    }

    document.querySelectorAll(".dl-pill[data-lfilter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-pill[data-lfilter]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.group = btn.getAttribute("data-lfilter");
        apply();
      });
    });

    document.querySelectorAll(".dl-seg[data-lkind]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-lkind]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        state.kind = btn.getAttribute("data-lkind");
        apply();
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = (searchInput.value || "").trim().toLowerCase();
        apply();
      });
    }

    wrap.addEventListener("click", function (e) {
      var head = e.target.closest(".js-lg-toggle");
      if (!head) return;
      var section = head.closest(".lg");
      if (section) setOpen(section, head.getAttribute("aria-expanded") !== "true");
    });

    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        var collapse = collapseBtn.getAttribute("aria-pressed") !== "true";
        collapseBtn.setAttribute("aria-pressed", String(collapse));
        collapseBtn.classList.toggle("is-active", collapse);
        collapseBtn.innerHTML = collapse
          ? '<i class="fas fa-expand-alt" aria-hidden="true"></i> Expand all'
          : '<i class="fas fa-compress-alt" aria-hidden="true"></i> Collapse all';
        groups.forEach(function (section) { setOpen(section, !collapse); });
      });
    }

    apply();

    var hash = window.location.hash || "";
    if (hash.indexOf("#link-") === 0) {
      var target = document.getElementById(hash.slice(1));
      if (target) {
        var section = target.closest(".lg");
        if (section) setOpen(section, true);
        target.classList.add("is-flash");
        window.setTimeout(function () { target.classList.remove("is-flash"); }, 2400);
        window.setTimeout(function () {
          target.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
        }, 60);
      }
    }
  }

  /* ---- Research Highlights: 3D orbit map ------------------------------ */
  // Builds a rotating 3D scene on the home page from the three highlight cards
  // already in the DOM: a root, one node per topic carrying its figure, and a
  // satellite per tag. No WebGL and no library: points are rotated and
  // projected here, and the nodes stay real focusable DOM elements so the text
  // is selectable, translatable and reachable by keyboard. With JavaScript off
  // the stage never appears and the cards render as they always did.
  var RM_FOCAL = 760;        // perspective distance in scene units
  var RM_R_TOPIC = 185;      // radius of the topic shell
  var RM_R_TAG = 96;         // radius of a tag shell around its topic
  var RM_NARROW = 720;       // stage width (px) at or below which the panel docks at the bottom
  var RM_SPIN = 0.0032;      // radians per frame while idle
  var RM_COLORS = ["#ea7317", "#0891b2", "#8b5cf6"];

  // Fibonacci sphere: n points spread evenly over a unit sphere, deterministic
  // so the scene looks the same on every load.
  function rmSphere(n) {
    var pts = [];
    var golden = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < n; i++) {
      var y = n === 1 ? 0 : 1 - (2 * i + 1) / n;
      var r = Math.sqrt(Math.max(0, 1 - y * y));
      var a = golden * i;
      pts.push({ x: Math.cos(a) * r, y: y, z: Math.sin(a) * r });
    }
    return pts;
  }

  function rmRotate(p, yaw, pitch) {
    var cy = Math.cos(yaw), sy = Math.sin(yaw);
    var x1 = p.x * cy + p.z * sy;
    var z1 = p.z * cy - p.x * sy;
    var cp = Math.cos(pitch), sp = Math.sin(pitch);
    return { x: x1, y: p.y * cp - z1 * sp, z: p.y * sp + z1 * cp };
  }

  function initResearchMap() {
    var root = document.getElementById("rmap");
    var stage = document.getElementById("rmap-stage");
    var bar = document.getElementById("rmap-bar");
    var nodeLayer = document.getElementById("rmap-nodes");
    var edgeLayer = document.getElementById("rmap-edges");
    var cards = document.getElementById("rmap-cards");
    var panel = document.getElementById("rmap-panel");
    if (!root || !stage || !nodeLayer || !edgeLayer || !cards || !panel) return;

    var panelBody = panel.querySelector(".rmap__panel-body");
    var articles = Array.prototype.slice.call(cards.querySelectorAll(".highlight-card"));
    if (!articles.length) return;

    /* -- scene built from the cards -- */
    var nodes = [];   // {el, pos, kind, topic, color, tag}
    var edges = [];   // {from, to, line, color}

    function addNode(el, pos, kind, topic, color) {
      var node = { el: el, pos: pos, kind: kind, topic: topic, color: color };
      nodes.push(node);
      return node;
    }

    var rootEl = document.createElement("button");
    rootEl.type = "button";
    rootEl.className = "rm-node rm-node--root";
    rootEl.setAttribute("data-rnode", "root");
    rootEl.innerHTML = '<span class="rm-node__root-label">Physical<br>AI</span>';
    rootEl.setAttribute("aria-label", "Physical AI, the centre of the map. Activate to clear the selection.");
    nodeLayer.appendChild(rootEl);
    var rootNode = addNode(rootEl, { x: 0, y: 0, z: 0 }, "root", -1, null);

    var topicDirs = rmSphere(articles.length);
    articles.forEach(function (card, i) {
      var color = RM_COLORS[i % RM_COLORS.length];
      var title = (card.querySelector(".highlight-card__title") || {}).textContent || "Topic";
      var dir = topicDirs[i];
      var pos = { x: dir.x * RM_R_TOPIC, y: dir.y * RM_R_TOPIC, z: dir.z * RM_R_TOPIC };

      var el = document.createElement("button");
      el.type = "button";
      el.className = "rm-node rm-node--topic";
      el.style.setProperty("--rm-color", color);
      el.setAttribute("data-rnode", "topic-" + i);
      el.setAttribute("aria-label", title + ". Activate to read this highlight.");

      var thumb = card.querySelector(".highlight-card__media img");
      if (thumb) {
        var copy = thumb.cloneNode(true);
        copy.removeAttribute("loading");
        copy.className = "rm-node__thumb";
        copy.setAttribute("alt", "");
        el.appendChild(copy);
      }
      var label = document.createElement("span");
      label.className = "rm-node__label";
      label.textContent = title.trim();
      el.appendChild(label);
      nodeLayer.appendChild(el);

      var topicNode = addNode(el, pos, "topic", i, color);
      edges.push({ from: rootNode, to: topicNode, color: color, weight: 2 });

      var tags = Array.prototype.slice.call(card.querySelectorAll(".tag-list .tag"));
      var dirs = rmSphere(Math.max(tags.length, 1));
      tags.forEach(function (tag, j) {
        var d = dirs[j];
        // Push the satellites outward from the centre so they orbit their topic
        // on the far side rather than falling back through the middle.
        var tpos = {
          x: pos.x + (d.x * 0.9 + dir.x * 0.5) * RM_R_TAG,
          y: pos.y + (d.y * 0.9 + dir.y * 0.5) * RM_R_TAG,
          z: pos.z + (d.z * 0.9 + dir.z * 0.5) * RM_R_TAG
        };
        var tEl = document.createElement("button");
        tEl.type = "button";
        tEl.className = "rm-node rm-node--tag";
        tEl.style.setProperty("--rm-color", color);
        tEl.setAttribute("data-rnode", "tag-" + i + "-" + j);
        tEl.textContent = tag.textContent.trim();
        tEl.setAttribute("aria-label", tag.textContent.trim() + ", part of " + title.trim());
        nodeLayer.appendChild(tEl);
        var tagNode = addNode(tEl, tpos, "tag", i, color);
        tagNode.tag = tag.textContent.trim().toLowerCase();
        edges.push({ from: topicNode, to: tagNode, color: color, weight: 1 });
      });
    });

    edges.forEach(function (e) {
      var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("class", "rm-edge");
      line.setAttribute("stroke-width", e.weight);
      line.style.stroke = e.color;
      edgeLayer.appendChild(line);
      e.line = line;
    });

    // Worst-case projected radius: the scene's outermost point, magnified by
    // perspective when it swings to the near side. Every fit below is measured
    // against it so a node cannot leave the stage at the default zoom.
    var sceneR = nodes.reduce(function (m, n) {
      return Math.max(m, Math.sqrt(n.pos.x * n.pos.x + n.pos.y * n.pos.y + n.pos.z * n.pos.z));
    }, 1);
    var reach = sceneR * (RM_FOCAL / Math.max(120, RM_FOCAL - sceneR));

    /* -- view state -- */
    var view = { yaw: 0.6, pitch: -0.18, zoom: 1 };
    var spinning = !prefersReduced;
    var dragging = false;
    var onScreen = true;
    var selected = null;
    var frame = null;
    var size = { w: 0, h: 0 };

    function measure() {
      var rect = stage.getBoundingClientRect();
      size.w = rect.width || stage.offsetWidth || 640;
      size.h = rect.height || stage.offsetHeight || 460;
      edgeLayer.setAttribute("viewBox", "0 0 " + size.w + " " + size.h);
      // Positions shrink to fit the stage; the nodes themselves shrink only
      // part of the way, so the labels stay readable on a phone.
      size.posFit = Math.max(0.3, Math.min(1, (0.46 * Math.min(size.w, size.h)) / reach));
      size.nodeFit = Math.min(1, 0.6 + 0.4 * size.posFit);
      stage.classList.toggle("is-narrow", size.w <= RM_NARROW);
    }

    function render() {
      var cx = size.w / 2;
      var cy = size.h / 2;
      // An open panel covers part of the stage, so move the scene into what is
      // left instead of drawing behind it: left of a side panel, or above one
      // docked along the bottom of a narrow stage (.is-narrow in
      // _research-map.scss, 62% of the height).
      if (!panel.hidden) {
        if (size.w > RM_NARROW) cx = size.w * 0.34;
        else cy = size.h * 0.19;
      }
      var fit = size.posFit || 1;

      nodes.forEach(function (n) {
        var r = rmRotate(n.pos, view.yaw, view.pitch);
        var depth = RM_FOCAL + r.z * fit;
        var persp = RM_FOCAL / Math.max(120, depth);
        var scale = persp * view.zoom * fit;
        n.sx = cx + r.x * scale;
        n.sy = cy + r.y * scale;
        // Perspective drives the position; the drawn size is clamped so the
        // near node does not balloon over the rest of the scene.
        n.scale = Math.max(0.55, Math.min(1.2, persp * view.zoom)) * (size.nodeFit || 1);
        n.z = r.z * fit;
      });

      nodes.forEach(function (n) {
        var fade = Math.max(0.22, Math.min(1, 1.18 - (n.z + sceneR) / (3.1 * sceneR)));
        if (n.kind !== "tag") fade = Math.max(0.55, fade);
        if (n.dim) fade *= 0.2;
        n.el.style.transform = "translate3d(" + (n.sx).toFixed(1) + "px," + (n.sy).toFixed(1) +
                               "px,0) translate(-50%,-50%) scale(" + n.scale.toFixed(3) + ")";
        n.el.style.zIndex = String(600 - Math.round(n.z));
        n.el.style.opacity = fade.toFixed(2);
      });

      edges.forEach(function (e) {
        e.line.setAttribute("x1", e.from.sx.toFixed(1));
        e.line.setAttribute("y1", e.from.sy.toFixed(1));
        e.line.setAttribute("x2", e.to.sx.toFixed(1));
        e.line.setAttribute("y2", e.to.sy.toFixed(1));
        var far = (e.from.z + e.to.z) / 2;
        e.line.setAttribute("stroke-opacity",
          Math.max(0.08, Math.min(0.55, 0.5 - far / (5 * RM_R_TOPIC))).toFixed(2));
      });
    }

    function tick() {
      if (spinning && !dragging && onScreen && panel.hidden) view.yaw += RM_SPIN;
      render();
      frame = window.requestAnimationFrame(tick);
    }

    function start() {
      if (frame === null) frame = window.requestAnimationFrame(tick);
    }
    function stop() {
      if (frame !== null) { window.cancelAnimationFrame(frame); frame = null; }
    }

    /* -- selection and panel -- */
    function clearLit() {
      nodes.forEach(function (n) {
        n.dim = false;
        n.el.classList.remove("is-lit");
      });
      edges.forEach(function (e) { e.line.classList.remove("is-lit"); });
    }

    function litTopic(index) {
      clearLit();
      nodes.forEach(function (n) {
        var mine = n.topic === index || n.kind === "root";
        n.dim = !mine;
        n.el.classList.toggle("is-lit", mine && n.kind !== "root");
      });
      edges.forEach(function (e) {
        e.line.classList.toggle("is-lit", e.to.topic === index || e.from.topic === index);
      });
    }

    function closePanel() {
      panel.hidden = true;
      panelBody.innerHTML = "";
      selected = null;
      clearLit();
      render();
    }

    function openTopic(index) {
      var card = articles[index];
      if (!card) return;
      panelBody.innerHTML = "";

      var trigger = card.querySelector(".js-lightbox");
      var img = card.querySelector(".highlight-card__media img");
      if (img && trigger) {
        var shot = document.createElement("button");
        shot.type = "button";
        shot.className = "rmap__shot";
        shot.setAttribute("aria-label", "Open the figure full size");
        var copy = img.cloneNode(true);
        copy.removeAttribute("loading");
        shot.appendChild(copy);
        // Reuse the card's own lightbox trigger rather than binding a second one.
        shot.addEventListener("click", function () { trigger.click(); });
        panelBody.appendChild(shot);
      }

      var body = card.querySelector(".highlight-card__body");
      if (body) {
        var clone = body.cloneNode(true);
        clone.classList.add("rmap__panel-text");
        panelBody.appendChild(clone);
      }

      panel.style.setProperty("--rm-color", RM_COLORS[index % RM_COLORS.length]);
      panel.hidden = false;
      panel.scrollTop = 0;
      selected = index;
      litTopic(index);
      render();
    }

    /* -- input -- */
    nodeLayer.addEventListener("click", function (e) {
      var btn = e.target.closest(".rm-node");
      if (!btn) return;
      var id = btn.getAttribute("data-rnode") || "";
      if (id === "root") { closePanel(); return; }
      if (id.indexOf("topic-") === 0) {
        var index = parseInt(id.slice(6), 10);
        if (selected === index) closePanel(); else openTopic(index);
        return;
      }
      if (id.indexOf("tag-") === 0) openTopic(parseInt(id.split("-")[1], 10));
    });

    nodeLayer.addEventListener("mouseover", function (e) {
      var btn = e.target.closest(".rm-node");
      if (!btn || selected !== null) return;
      var id = btn.getAttribute("data-rnode") || "";
      if (id === "root") return;
      var parts = id.split("-");
      litTopic(parseInt(parts[1], 10));
      render();
    });
    nodeLayer.addEventListener("mouseleave", function () {
      if (selected !== null) return;
      clearLit();
      render();
    });

    var drag = null;
    stage.addEventListener("pointerdown", function (e) {
      if (e.target.closest(".rmap__panel")) return;
      drag = { x: e.clientX, y: e.clientY, yaw: view.yaw, pitch: view.pitch, moved: false };
      dragging = true;
      stage.classList.add("is-dragging");
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener("pointermove", function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.x;
      var dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      view.yaw = drag.yaw + dx * 0.006;
      view.pitch = Math.max(-1.1, Math.min(1.1, drag.pitch + dy * 0.005));
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (evt) {
      stage.addEventListener(evt, function () {
        drag = null;
        dragging = false;
        stage.classList.remove("is-dragging");
      });
    });

    stage.addEventListener("wheel", function (e) {
      if (e.target.closest(".rmap__panel")) return;
      e.preventDefault();
      view.zoom = Math.max(0.6, Math.min(2.2, view.zoom * (e.deltaY > 0 ? 0.92 : 1.08)));
    }, { passive: false });

    var spinBtn = root.querySelector('[data-rmap="spin"]');
    if (spinBtn) {
      spinBtn.addEventListener("click", function () {
        spinning = !spinning;
        spinBtn.setAttribute("aria-pressed", String(spinning));
        spinBtn.setAttribute("aria-label", spinning ? "Pause the rotation" : "Resume the rotation");
        spinBtn.innerHTML = spinning
          ? '<i class="fas fa-pause" aria-hidden="true"></i>'
          : '<i class="fas fa-play" aria-hidden="true"></i>';
      });
      if (prefersReduced) {
        spinBtn.setAttribute("aria-pressed", "false");
        spinBtn.innerHTML = '<i class="fas fa-play" aria-hidden="true"></i>';
      }
    }
    var resetBtn = root.querySelector('[data-rmap="reset"]');
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        view.yaw = 0.6; view.pitch = -0.18; view.zoom = 1;
        render();
      });
    }
    var closeBtn = panel.querySelector(".rmap__close");
    if (closeBtn) closeBtn.addEventListener("click", closePanel);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !panel.hidden) closePanel();
    });

    document.querySelectorAll(".dl-seg[data-rview]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dl-seg[data-rview]").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        var mode = btn.getAttribute("data-rview");
        stage.hidden = mode !== "map";
        cards.hidden = mode === "map";
        if (mode === "map") { measure(); render(); start(); } else { stop(); }
      });
    });

    /* -- go live -- */
    bar.hidden = false;
    stage.hidden = false;
    cards.hidden = true;
    measure();
    render();

    if ("ResizeObserver" in window) {
      new ResizeObserver(function () { measure(); render(); }).observe(stage);
    } else {
      window.addEventListener("resize", function () { measure(); render(); });
    }

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        onScreen = entries[0].isIntersecting;
        if (onScreen && !stage.hidden) start(); else stop();
      }, { threshold: 0.05 }).observe(stage);
    } else {
      start();
    }
  }

  /* ---- Floating Back to Top Button ----------------------------------- */
  function initBackToTop() {
    var btn = document.getElementById("back-to-top");
    if (!btn) return;
    window.addEventListener("scroll", function () {
      if (window.scrollY > 350) {
        btn.classList.add("is-visible");
      } else {
        btn.classList.remove("is-visible");
      }
    });
    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: prefersReduced ? "auto" : "smooth" });
    });
  }

  /* ---- Reading progress ---------------------------------------------- */
  function initScrollProgress() {
    var bar = document.getElementById("scroll-progress");
    if (!bar) return;
    var ticking = false;

    function sync() {
      ticking = false;
      var doc = document.documentElement;
      var max = Math.max(1, doc.scrollHeight - window.innerHeight);
      var progress = Math.max(0, Math.min(1, window.scrollY / max));
      root.style.setProperty("--scroll-progress", progress.toFixed(4));
    }

    function requestSync() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(sync);
    }

    window.addEventListener("scroll", requestSync, { passive: true });
    window.addEventListener("resize", requestSync);
    window.addEventListener("load", requestSync);
    sync();
  }

  /* ---- Interactive Skill Search -------------------------------------- */
  function initSkillSearch() {
    var input = document.getElementById("skill-search");
    var chips = document.querySelectorAll(".skill-chip");
    if (!input || !chips.length) return;

    input.addEventListener("input", function () {
      var q = (input.value || "").trim().toLowerCase();
      chips.forEach(function (chip) {
        var text = chip.textContent.toLowerCase();
        if (!q) {
          chip.style.opacity = "";
          chip.style.borderColor = "";
          chip.style.background = "";
          chip.style.color = "";
        } else if (text.indexOf(q) !== -1) {
          chip.style.opacity = "1";
          chip.style.borderColor = "var(--accent)";
          chip.style.background = "var(--accent)";
          chip.style.color = "#ffffff";
        } else {
          chip.style.opacity = "0.35";
          chip.style.borderColor = "";
          chip.style.background = "";
          chip.style.color = "";
        }
      });
    });
  }

  /* ---- Copy Email ---------------------------------------------------- */
  function initCopyEmail() {
    document.querySelectorAll(".js-copy-email").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var email = btn.getAttribute("data-email");
        if (!email) return;
        var done = function () {
          showCopyToast(email + " copied to clipboard!");
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(email).then(done).catch(function () {});
        } else {
          var ta = document.createElement("textarea");
          ta.value = email; document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); done(); } catch (err) {}
          document.body.removeChild(ta);
        }
      });
    });
  }

  /* ---- Accordion Controls (Expand All / Collapse All) ----------------- */
  function initAccordionControls() {
    var expandBtn = document.getElementById("accordion-expand-all");
    var collapseBtn = document.getElementById("accordion-collapse-all");
    if (!expandBtn && !collapseBtn) return;

    if (expandBtn) {
      expandBtn.addEventListener("click", function () {
        document.querySelectorAll(".accordion__item").forEach(function (item) {
          item.classList.add("is-open");
          var header = item.querySelector(".accordion__header");
          if (header) header.setAttribute("aria-expanded", "true");
        });
      });
    }
    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        document.querySelectorAll(".accordion__item").forEach(function (item) {
          item.classList.remove("is-open");
          var header = item.querySelector(".accordion__header");
          if (header) header.setAttribute("aria-expanded", "false");
        });
      });
    }
  }

  /* ---- World University Rankings (THE / QS tabs + search) ------------- */
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function initRankings() {
    var modal = document.getElementById("rankings-modal");
    if (!modal) return;

    var tabs = Array.prototype.slice.call(modal.querySelectorAll(".rank-tab"));
    var panels = Array.prototype.slice.call(modal.querySelectorAll(".rank-panel"));
    if (!tabs.length || !panels.length) return;

    // Deep-link support: /?rank=qs&country=Japan&q=tokyo opens the modal already
    // filtered, which is what the command palette links to.
    var urlState = readQuery();
    var deepLinked = !!(urlState.rank || urlState.country || urlState.q);
    var activeKey = urlState.rank === "qs" ? "qs" : "the";
    var syncUrl = false;

    function pushState() {
      if (!syncUrl) return;
      var panel = panels.filter(function (p) { return !p.hidden; })[0];
      if (!panel) return;
      var key = panel.getAttribute("data-rank-panel");
      var input = panel.querySelector(".rank-search");
      writeQuery({
        rank: key,
        country: panel.rankCountry || "",
        q: input ? input.value.trim() : ""
      });
    }
    modal.rankPushState = pushState;

    function selectTab(key) {
      tabs.forEach(function (t) {
        var on = t.getAttribute("data-rank-tab") === key;
        t.classList.toggle("active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
      });
      panels.forEach(function (p) {
        p.hidden = p.getAttribute("data-rank-panel") !== key;
      });
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        selectTab(tab.getAttribute("data-rank-tab"));
        pushState();
      });
    });

    panels.forEach(function (panel) {
      var key = panel.getAttribute("data-rank-panel");
      var input = panel.querySelector('[data-rank-search="' + key + '"]');
      var counter = panel.querySelector('[data-rank-count="' + key + '"]');
      var table = panel.querySelector('[data-rank-table="' + key + '"]');
      var chipBox = panel.querySelector('[data-rank-countries="' + key + '"]');
      var moreBtn = panel.querySelector('[data-rank-more="' + key + '"]');
      if (!table) return;

      var empty = table.querySelector(".rank-empty");
      var loading = table.querySelector(".rank-loading");
      var body = table.querySelector("tbody");
      var scroll = panel.querySelector(".rank-scroll");
      var rows = [], haystack = [], countries = [], total = 0;
      var country = "";
      panel.rankCountry = "";

      function apply() {
        var q = input ? (input.value || "").trim().toLowerCase() : "";
        var shown = 0;
        for (var i = 0; i < rows.length; i++) {
          var hit = (!country || countries[i] === country) &&
                    (!q || haystack[i].indexOf(q) !== -1);
          rows[i].style.display = hit ? "" : "none";
          if (hit) shown++;
        }
        if (empty) empty.hidden = shown !== 0;
        if (counter) counter.innerHTML = "Showing <b>" + shown + "</b> / " + total;
        if (scroll) scroll.scrollTop = 0;
      }
      panel.rankApply = apply;

      // Seed this panel from the URL before any rows exist; apply() runs after render.
      if (deepLinked && key === activeKey) {
        if (urlState.q && input) input.value = urlState.q;
        if (urlState.country) {
          country = panel.rankCountry = urlState.country;
        }
      }

      // Build the 400 rows from the JSON payload. One innerHTML write beats
      // appending 400 nodes one at a time.
      panel.rankRender = function (entries) {
        var html = "", medals = { "1": " rank-pos--gold", "2": " rank-pos--silver", "3": " rank-pos--bronze" };
        var otherName = panel.getAttribute("data-rank-other") || "";
        var otherTitle = panel.getAttribute("data-rank-other-title") || "";
        for (var i = 0; i < entries.length; i++) {
          var rank = entries[i][0], name = entries[i][1], loc = entries[i][2], cross = entries[i][3];
          var medal = medals[rank.replace("=", "")] || "";
          // Blank cross means no confident match between the two tables, which is
          // not the same as "absent from the other ranking" - so say nothing.
          var crossHtml = cross
            ? ' <span class="rank-cross" title="' + esc(otherTitle) + '">' +
              esc(otherName) + " " + esc(cross) + "</span>"
            : "";
          html += '<tr data-c="' + esc(loc) + '"><td class="rank-pos' + medal + '"><span>' +
                  esc(rank) + '</span></td><td class="rank-uni">' + esc(name) + crossHtml +
                  '</td><td class="rank-loc">' + esc(loc) + "</td></tr>";
        }
        if (loading) loading.remove();
        body.insertAdjacentHTML("beforeend", html);
        rows = Array.prototype.slice.call(body.querySelectorAll("tr:not(.rank-empty)"));
        haystack = rows.map(function (r) { return r.textContent.toLowerCase(); });
        countries = rows.map(function (r) { return r.getAttribute("data-c") || ""; });
        total = rows.length;
        apply();
      };

      panel.rankFail = function () {
        if (loading) {
          loading.querySelector("td").textContent =
            "Could not load the rankings. Please refresh the page.";
        }
      };

      if (input) {
        input.addEventListener("input", function () { apply(); pushState(); });
      }

      if (chipBox) {
        var chips = Array.prototype.slice.call(chipBox.querySelectorAll(".rank-chip"));
        var syncChips = function () {
          chips.forEach(function (c) {
            c.classList.toggle("active", (c.getAttribute("data-country") || "") === country);
          });
        };
        if (country) syncChips();
        chipBox.addEventListener("click", function (e) {
          var chip = e.target.closest(".rank-chip");
          if (!chip) return;
          // Clicking the active country again clears it, so the chips double as a toggle.
          var next = chip.getAttribute("data-country");
          country = (next && next === country) ? "" : next;
          panel.rankCountry = country;
          syncChips();
          apply();
          pushState();
        });
      }

      if (moreBtn && chipBox) {
        moreBtn.addEventListener("click", function () {
          var open = chipBox.classList.toggle("is-expanded");
          moreBtn.setAttribute("aria-expanded", open ? "true" : "false");
          moreBtn.textContent = open
            ? "Show fewer countries"
            : moreBtn.getAttribute("data-label");
        });
        moreBtn.setAttribute("data-label", moreBtn.textContent);
      }
    });

    // Fetch the row data the first time the modal is opened, so the homepage
    // never pays for it on load.
    var loaded = false;
    function loadRows() {
      if (loaded) return;
      loaded = true;
      var url = modal.getAttribute("data-rank-src");
      fetch(url, { credentials: "same-origin" })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          panels.forEach(function (p) {
            var rows = data[p.getAttribute("data-rank-panel")];
            if (rows && p.rankRender) p.rankRender(rows);
          });
        })
        .catch(function (e) {
          if (window.console) console.error("rankings load failed", e);
          panels.forEach(function (p) { if (p.rankFail) p.rankFail(); });
        });
    }

    var trigger = document.querySelector('[data-modal-target="#rankings-modal"]');
    Array.prototype.slice.call(
      document.querySelectorAll('[data-modal-target="#rankings-modal"]')
    ).forEach(function (btn) {
      // Warm the data on hover/focus so the table is usually ready by the click.
      btn.addEventListener("mouseenter", loadRows);
      btn.addEventListener("focus", loadRows);
      btn.addEventListener("click", loadRows);
    });

    // Open a shared/deep link straight into the right tab and filters.
    modal.rankOpen = function (opts) {
      opts = opts || {};
      var key = opts.rank === "qs" ? "qs" : "the";
      selectTab(key);
      var panel = modal.querySelector('[data-rank-panel="' + key + '"]');
      if (panel) {
        var input = panel.querySelector(".rank-search");
        if (input && typeof opts.q === "string") input.value = opts.q;
        if (panel.rankApply) panel.rankApply();
      }
      loadRows();
      if (trigger) trigger.click();
      pushState();
    };

    if (deepLinked) {
      selectTab(activeKey);
      loadRows();
      if (trigger) trigger.click();
    }
    syncUrl = true;
  }

  /* ---- Command palette (Cmd/Ctrl-K) ----------------------------------- */
  function initPalette() {
    var box = document.getElementById("palette");
    var input = document.getElementById("palette-input");
    var results = document.getElementById("palette-results");
    if (!box || !input || !results) return;

    var openBtn = document.getElementById("palette-open");
    var closeBtn = document.getElementById("palette-close");
    var home = box.getAttribute("data-home") || "/";
    var items = null, loading = false, active = 0, shown = [], lastFocus = null;

    function load() {
      if (items || loading) return;
      loading = true;
      fetch(box.getAttribute("data-palette-src"), { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (data) { items = data; render(); })
        .catch(function () { items = []; render(); });
    }

    // Subsequence match, so "vla" finds "Vision-Language-Action" and typos in the
    // middle of a long title do not kill the result.
    function score(item, q) {
      var hay = (item.t + " " + (item.s || "") + " " + (item.k || "")).toLowerCase();
      var idx = hay.indexOf(q);
      if (idx !== -1) return idx === 0 ? 0 : 1 + idx / 200;
      var ti = 0;
      for (var i = 0; i < q.length; i++) {
        ti = hay.indexOf(q[i], ti);
        if (ti === -1) return -1;
        ti++;
      }
      return 50;
    }

    function render() {
      var q = input.value.trim().toLowerCase();
      var list = [];
      if (items && q) {
        list = items
          .map(function (it) { return { it: it, sc: score(it, q) }; })
          .filter(function (r) { return r.sc >= 0; })
          .sort(function (a, b) { return a.sc - b.sc; })
          .slice(0, 12)
          .map(function (r) { return r.it; });
      } else if (items) {
        list = items.filter(function (it) { return it.k === "Page"; }).slice(0, 5);
      }
      // Always offer the rankings lookup: 800 universities stay out of this index.
      if (q) {
        list = list.concat([{
          t: "Search “" + input.value.trim() + "” in the university rankings",
          k: "Rankings",
          u: home + "?q=" + encodeURIComponent(input.value.trim())
        }]);
      }
      shown = list;
      active = 0;
      if (!items && loading) {
        results.innerHTML = '<li class="palette__empty">Loading&hellip;</li>';
        return;
      }
      if (!list.length) {
        results.innerHTML = '<li class="palette__empty">No matches</li>';
        return;
      }
      results.innerHTML = list.map(function (it, i) {
        return '<li class="palette__item' + (i === 0 ? " is-active" : "") +
          '" role="option" aria-selected="' + (i === 0) + '" data-i="' + i + '">' +
          '<span class="palette__kind">' + esc(it.k) + "</span>" +
          '<span class="palette__title">' + esc(it.t) + "</span>" +
          (it.m ? '<span class="palette__meta">' + esc(it.m) + "</span>" : "") +
          "</li>";
      }).join("");
    }

    function move(step) {
      if (!shown.length) return;
      active = (active + step + shown.length) % shown.length;
      Array.prototype.slice.call(results.children).forEach(function (li, i) {
        li.classList.toggle("is-active", i === active);
        li.setAttribute("aria-selected", i === active);
      });
      var el = results.children[active];
      if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
    }

    function go(i) {
      var it = shown[i];
      if (!it) return;
      close();
      window.location.href = it.u;
    }

    function open() {
      lastFocus = document.activeElement;
      box.hidden = false;
      document.body.style.overflow = "hidden";
      load();
      render();
      input.focus();
      input.select();
    }
    function close() {
      box.hidden = true;
      document.body.style.overflow = "";
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    if (openBtn) openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    input.addEventListener("input", render);
    if (openBtn) {
      openBtn.addEventListener("mouseenter", load);
      openBtn.addEventListener("focus", load);
    }

    results.addEventListener("click", function (e) {
      var li = e.target.closest(".palette__item");
      if (li) go(parseInt(li.getAttribute("data-i"), 10));
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Enter") { e.preventDefault(); go(active); }
      else if (e.key === "Escape") { e.preventDefault(); close(); }
    });

    document.addEventListener("keydown", function (e) {
      var k = (e.key || "").toLowerCase();
      if ((e.metaKey || e.ctrlKey) && k === "k") {
        e.preventDefault();
        box.hidden ? open() : close();
        return;
      }
      // "/" opens search the way it does on GitHub, unless the user is typing.
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (k === "/" && box.hidden && tag !== "INPUT" && tag !== "TEXTAREA") {
        e.preventDefault();
        open();
      }
    });
  }

  /* ---- Deep links: open an accordion / prefill skill search ----------- */
  function initDeepLinks() {
    var hash = window.location.hash;
    if (hash && hash.indexOf("#p-") === 0) {
      var item = document.getElementById(hash.slice(1));
      if (item && item.classList.contains("accordion__item")) {
        item.classList.add("is-open");
        var head = item.querySelector(".accordion__header");
        if (head) head.setAttribute("aria-expanded", "true");
        window.setTimeout(function () {
          item.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
        }, 120);
      }
    }
    var skill = readQuery().skill;
    var skillInput = document.getElementById("skill-search");
    if (skill && skillInput) {
      skillInput.value = skill;
      skillInput.dispatchEvent(new Event("input"));
      skillInput.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
    }
  }

  /* ---- Carousels (awards / activities / teaching / highlights) -------- */
  // One controller for every [data-carousel]. Replaces the inline onclick
  // handlers that scrolled a hardcoded 330-370px: the step is now derived from
  // the real card size, the arrows disable at the ends instead of looking
  // broken, and the track takes keyboard and drag input.
  //
  // The axis follows the stylesheet: a track laid out as a flex column (the
  // home page's side-by-side highlights and awards) scrolls vertically, any
  // other track sideways. It is re-read on every call, so a track that swaps
  // layout at a breakpoint swaps axis with it.
  function initCarousels() {
    document.querySelectorAll("[data-carousel]").forEach(function (box) {
      var track = box.querySelector("[data-carousel-track]");
      if (!track) return;
      var prev = box.querySelector("[data-carousel-prev]");
      var next = box.querySelector("[data-carousel-next]");
      var bar = box.querySelector("[data-carousel-progress]");

      function vertical() {
        return getComputedStyle(track).flexDirection.indexOf("column") === 0;
      }

      function position() {
        return vertical() ? track.scrollTop : track.scrollLeft;
      }

      // Cards in a column differ in height, so a vertical step pages by most
      // of the visible track and lets scroll-snap settle on a card edge.
      function step() {
        if (vertical()) return Math.round(track.clientHeight * 0.8);
        var card = track.querySelector(".carousel-card");
        if (!card) return Math.round(track.clientWidth * 0.8);
        var gap = parseFloat(getComputedStyle(track).columnGap || "0") || 0;
        return Math.round(card.getBoundingClientRect().width + gap);
      }

      function maxScroll() {
        return vertical()
          ? Math.max(0, track.scrollHeight - track.clientHeight)
          : Math.max(0, track.scrollWidth - track.clientWidth);
      }

      // The track carries padding so hover shadows are not clipped, and
      // scroll-snap parks the first card against the content box, not the
      // scrollport. So a track sitting at its start reads a scroll offset equal
      // to its leading padding, not 0. Derive the end tolerances from that
      // padding rather than guessing a pixel constant.
      function edgeSlack() {
        var cs = getComputedStyle(track);
        var v = vertical();
        return {
          start: Math.max(2, (parseFloat(v ? cs.paddingTop : cs.paddingLeft) || 0) + 1),
          end: Math.max(2, (parseFloat(v ? cs.paddingBottom : cs.paddingRight) || 0) + 1)
        };
      }

      function jumpTo(offset) {
        var opts = { behavior: prefersReduced ? "auto" : "smooth" };
        opts[vertical() ? "top" : "left"] = offset;
        track.scrollTo(opts);
      }

      function scrollBy(dir) {
        var opts = { behavior: prefersReduced ? "auto" : "smooth" };
        opts[vertical() ? "top" : "left"] = dir * step();
        track.scrollBy(opts);
      }

      function sync() {
        var v = vertical();
        var max = maxScroll();
        var at = position();
        var slack = edgeSlack();
        var atStart = at <= slack.start;
        var atEnd = at >= max - slack.end;
        box.classList.toggle("is-scrollable", max > 1);
        box.classList.toggle("at-start", atStart);
        box.classList.toggle("at-end", atEnd);
        if (prev) prev.disabled = atStart;
        if (next) next.disabled = atEnd;
        if (bar) {
          var filled = (max > 1 ? (at / max) * 100 : 100) + "%";
          bar.style.width = v ? "" : filled;
          bar.style.height = v ? filled : "";
        }
      }

      if (prev) prev.addEventListener("click", function () { scrollBy(-1); });
      if (next) next.addEventListener("click", function () { scrollBy(1); });

      track.addEventListener("keydown", function (e) {
        var v = vertical();
        if (e.key === (v ? "ArrowDown" : "ArrowRight")) { e.preventDefault(); scrollBy(1); }
        else if (e.key === (v ? "ArrowUp" : "ArrowLeft")) { e.preventDefault(); scrollBy(-1); }
        else if (e.key === "Home") { e.preventDefault(); jumpTo(0); }
        else if (e.key === "End") { e.preventDefault(); jumpTo(maxScroll()); }
      });

      // Click-drag on pointer devices. Touch keeps the browser's native
      // momentum scrolling, so it is deliberately left alone.
      var dragging = false, dragV = false, startAt = 0, startScroll = 0, moved = 0;
      track.addEventListener("pointerdown", function (e) {
        if (e.pointerType === "touch" || e.button !== 0) return;
        if (e.target.closest("a, button")) return;
        dragging = true; moved = 0;
        dragV = vertical();
        startAt = dragV ? e.clientY : e.clientX;
        startScroll = position();
        track.classList.add("is-dragging");
      });
      track.addEventListener("pointermove", function (e) {
        if (!dragging) return;
        var d = (dragV ? e.clientY : e.clientX) - startAt;
        moved = Math.max(moved, Math.abs(d));
        if (moved > 3 && track.setPointerCapture && e.pointerId != null) {
          try { track.setPointerCapture(e.pointerId); } catch (err) {}
        }
        if (dragV) track.scrollTop = startScroll - d;
        else track.scrollLeft = startScroll - d;
      });
      function endDrag() {
        if (!dragging) return;
        dragging = false;
        track.classList.remove("is-dragging");
      }
      track.addEventListener("pointerup", endDrag);
      track.addEventListener("pointercancel", endDrag);
      track.addEventListener("pointerleave", endDrag);
      // Swallow the click that ends a drag so it never opens a card link.
      track.addEventListener("click", function (e) {
        if (moved > 4) { e.preventDefault(); e.stopPropagation(); moved = 0; }
      }, true);

      var ticking = false;
      track.addEventListener("scroll", function () {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(function () { ticking = false; sync(); });
      }, { passive: true });

      if (window.ResizeObserver) {
        new ResizeObserver(sync).observe(track);
      } else {
        window.addEventListener("resize", sync);
      }
      // Cards hold lazy images, so the scroll width settles after first paint.
      window.addEventListener("load", sync);
      sync();
    });
  }

  /* ---- Ambient floating bubbles -------------------------------------- */
  function initAmbientBubbles() {
    var canvas = document.getElementById("ambient-bubbles");
    if (!canvas || !canvas.getContext) return;
    if (prefersReduced) return;

    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var width = 0;
    var height = 0;
    var dpr = window.devicePixelRatio || 1;
    var particles = [];
    var animId = null;
    var mouse = { x: -1000, y: -1000, active: false };
    var mouseTimer = null;

    // Pastel palette sampled from the reference snapshot
    var PALETTE = [
      { r: 159, g: 191, b: 174 }, // sage
      { r: 184, g: 222, b: 203 }, // mint
      { r: 246, g: 207, b: 197 }, // peach
      { r: 173, g: 197, b: 230 }, // periwinkle
      { r: 250, g: 216, b: 212 }, // blush
      { r: 228, g: 169, b: 155 }, // terracotta
      { r: 247, g: 222, b: 215 }  // apricot
    ];

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function createParticle(initial) {
      var col = PALETTE[Math.floor(Math.random() * PALETTE.length)];
      var rBase = Math.random();
      var radius = rBase < 0.65 ? (2.6 + Math.random() * 2.8) : (5.6 + Math.random() * 3.8);
      var speed = 0.12 + Math.random() * 0.22;
      var angle = Math.random() * Math.PI * 2;
      return {
        x: initial ? Math.random() * width : (Math.random() < 0.5 ? -radius : width + radius),
        y: initial ? Math.random() * height : Math.random() * height,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: radius,
        color: col,
        alpha: 0.42 + Math.random() * 0.26,
        phase: Math.random() * Math.PI * 2,
        wobbleSpeed: 0.006 + Math.random() * 0.010
      };
    }

    function initParticles() {
      particles = [];
      var targetCount = Math.max(20, Math.min(45, Math.floor((width * height) / 32000)));
      for (var i = 0; i < targetCount; i++) {
        particles.push(createParticle(true));
      }
    }

    function update() {
      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        p.phase += p.wobbleSpeed;

        var curVx = p.vx + Math.cos(p.phase) * 0.08;
        var curVy = p.vy + Math.sin(p.phase) * 0.08;

        if (mouse.active) {
          var dx = p.x - mouse.x;
          var dy = p.y - mouse.y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          var repulseDist = 80;
          if (dist < repulseDist && dist > 1) {
            var push = (1 - dist / repulseDist) * 0.35;
            curVx += (dx / dist) * push;
            curVy += (dy / dist) * push;
          }
        }

        p.x += curVx;
        p.y += curVy;

        var pad = p.radius + 15;
        if (p.x < -pad) p.x = width + pad;
        else if (p.x > width + pad) p.x = -pad;
        if (p.y < -pad) p.y = height + pad;
        else if (p.y > height + pad) p.y = -pad;
      }
    }

    function render() {
      ctx.clearRect(0, 0, width, height);
      var isDark = root.getAttribute("data-theme") === "dark";

      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        var c = p.color;
        var a = isDark ? Math.min(0.75, p.alpha * 1.15) : p.alpha;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(" + c.r + "," + c.g + "," + c.b + "," + a.toFixed(3) + ")";
        ctx.fill();
      }
    }

    function tick() {
      update();
      render();
      animId = window.requestAnimationFrame(tick);
    }

    function onMouseMove(e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
      if (mouseTimer) window.clearTimeout(mouseTimer);
      mouseTimer = window.setTimeout(function () {
        mouse.active = false;
      }, 1200);
    }

    function onVisibilityChange() {
      if (document.hidden) {
        if (animId) {
          window.cancelAnimationFrame(animId);
          animId = null;
        }
      } else {
        if (!animId) {
          animId = window.requestAnimationFrame(tick);
        }
      }
    }

    var resizeTimer = null;
    function onResize() {
      if (resizeTimer) window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(function () {
        var oldW = width || 1;
        var oldH = height || 1;
        resize();
        for (var i = 0; i < particles.length; i++) {
          particles[i].x = (particles[i].x / oldW) * width;
          particles[i].y = (particles[i].y / oldH) * height;
        }
      }, 150);
    }

    resize();
    initParticles();
    animId = window.requestAnimationFrame(tick);

    window.addEventListener("resize", onResize, { passive: true });
    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mouseout", function (e) {
      if (!e.relatedTarget) mouse.active = false;
    });
    document.addEventListener("visibilitychange", onVisibilityChange);
  }

  /* ---- Anonymous message form (footer) ------------------------------- */
  // Posts to the Cloudflare Worker in workers/contact. Turnstile loads only when
  // the dialog opens, so pages that never open it make no third-party request.
  function initMessageForm() {
    var form = document.getElementById("message-form");
    var opener = document.querySelector('[data-modal-target="#message-modal"]');
    if (!form || !opener) return;
    var endpoint = form.getAttribute("data-endpoint");
    var sitekey = form.getAttribute("data-sitekey");
    var text = document.getElementById("message-text");
    var contact = document.getElementById("message-contact");
    var honeypot = document.getElementById("message-website");
    var count = document.getElementById("message-count");
    var send = document.getElementById("message-send");
    var status = document.getElementById("message-status");
    var sent = document.getElementById("message-sent");
    var again = document.getElementById("message-again");
    var box = document.getElementById("message-turnstile");
    var MIN = 10, MAX = 2000;
    var token = "", widget = null, loading = false, busy = false;

    function say(msg, isError) {
      status.textContent = msg;
      status.classList.toggle("is-error", !!isError);
    }
    function refresh() {
      var n = text.value.trim().length;
      count.textContent = text.value.length + " / " + MAX;
      send.disabled = busy || !token || n < MIN;
    }
    function render() {
      if (widget !== null || !window.turnstile) return;
      widget = window.turnstile.render(box, {
        sitekey: sitekey,
        theme: root.getAttribute("data-theme") === "dark" ? "dark" : "light",
        callback: function (t) { token = t; say(""); refresh(); },
        "expired-callback": function () { token = ""; say("The spam check expired. It will renew in a moment."); refresh(); },
        "error-callback": function () { token = ""; say("The spam check could not load. Check your connection or disable a blocker, then reopen this form.", true); refresh(); }
      });
    }
    function loadTurnstile() {
      if (window.turnstile) { render(); return; }
      if (loading) return;
      loading = true;
      window.onMessageTurnstile = render;
      var s = document.createElement("script");
      s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onMessageTurnstile";
      s.async = true;
      s.onerror = function () { loading = false; say("The spam check could not load. Check your connection or disable a blocker, then reopen this form.", true); };
      document.head.appendChild(s);
    }
    function resetCheck() {
      token = "";
      if (widget !== null && window.turnstile) window.turnstile.reset(widget);
      refresh();
    }

    opener.addEventListener("click", function () {
      loadTurnstile();
      window.setTimeout(function () { if (!sent.hidden) again.focus(); else text.focus(); }, 60);
    });
    text.addEventListener("input", refresh);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var msg = text.value.trim();
      if (msg.length < MIN) { say("Write at least " + MIN + " characters.", true); text.focus(); return; }
      if (!token) { say("The spam check has not finished. Wait a moment and send again.", true); return; }
      busy = true; refresh();
      say("Sending…");
      var ctrl = window.AbortController ? new AbortController() : null;
      var timer = ctrl ? window.setTimeout(function () { ctrl.abort(); }, 15000) : null;
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, contact: contact.value.trim(), website: honeypot.value, token: token, page: window.location.pathname }),
        signal: ctrl ? ctrl.signal : undefined
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok && j.ok, error: j.error }; });
      }).then(function (res) {
        if (res.ok) {
          form.reset();
          form.hidden = true;
          sent.hidden = false;
          say("");
          again.focus();
        } else {
          say(res.error || "The message could not be sent. Please try again.", true);
        }
      }).catch(function () {
        say("The message could not be sent. Check your connection and try again.", true);
      }).then(function () {
        if (timer) window.clearTimeout(timer);
        busy = false;
        resetCheck();
      });
    });

    again.addEventListener("click", function () {
      sent.hidden = true;
      form.hidden = false;
      refresh();
      if (!token) say("Running a quick spam check…");
      text.focus();
    });
    refresh();
  }

  /* ---- Boot ---------------------------------------------------------- */
  function safe(fn) { try { fn(); } catch (e) { if (window.console) console.error(e); } }
  function boot() {
    // Reveal first so a later failure never leaves content invisible.
    safe(initReveal);
    safe(initTheme);
    safe(initAmbientBubbles);
    safe(initMobileNav);
    safe(initAccordions);
    safe(initToggles);
    safe(initCopy);
    safe(initCopyEmail);
    safe(initAccordionControls);
    safe(initPubFilter);
    safe(initPubTools);
    safe(initActivityFilter);
    safe(initUpdatesScroll);
    safe(initLightbox);
    safe(initModals);
    safe(initMessageForm);
    safe(initDeadlineTracker);
    safe(initDeadlineBadge);
    safe(initJournalExplorer);
    safe(initResearchIdeas);
    safe(initLinkLibrary);
    safe(initResearchMap);
    safe(initRankings);
    safe(initPalette);
    safe(initScrollProgress);
    safe(initBackToTop);
    safe(initSkillSearch);
    safe(initCarousels);
    // Last: it fires input events at widgets above, so they must be listening.
    safe(initDeepLinks);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
