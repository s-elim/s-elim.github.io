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

    if (search) search.addEventListener("input", apply);
    apply();
    syncUrl = true; // only mirror to the URL once the user drives it
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
        return modal.querySelectorAll('a[href], button:not([disabled])');
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
           '" style="font-size: 0.72rem; padding: 1px 7px;">' +
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
        var raw = el.getAttribute("data-date");
        var when = null;
        if (raw && raw !== "tba") {
          var p = raw.split("-");
          if (p.length === 3) {
            var t = (el.getAttribute("data-time") || "23:59").split(":");
            when = new Date(
              parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10),
              parseInt(t[0], 10) || 23, parseInt(t[1], 10) || 59, 0
            );
          }
        }
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

    // Local time, matching how the tracker reads the same dates.
    var stages = [];
    raw.forEach(function (s) {
      var d = String(s.d || "").split("-");
      if (d.length !== 3) return;
      var t = String(s.t || "23:59").split(":");
      stages.push({
        name: s.n || "",
        when: new Date(
          parseInt(d[0], 10), parseInt(d[1], 10) - 1, parseInt(d[2], 10),
          parseInt(t[0], 10) || 0, parseInt(t[1], 10) || 0, 0
        ).getTime()
      });
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
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
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

  /* ---- Personal Quote Banner ------------------------------------------ */
  function initQuoteBanner() {
    var banner = document.getElementById("quote-banner");
    if (!banner) return;
  }

  /* ---- Boot ---------------------------------------------------------- */
  function safe(fn) { try { fn(); } catch (e) { if (window.console) console.error(e); } }
  function boot() {
    // Reveal first so a later failure never leaves content invisible.
    safe(initReveal);
    safe(initTheme);
    safe(initMobileNav);
    safe(initAccordions);
    safe(initToggles);
    safe(initCopy);
    safe(initCopyEmail);
    safe(initAccordionControls);
    safe(initPubFilter);
    safe(initActivityFilter);
    safe(initUpdatesScroll);
    safe(initLightbox);
    safe(initModals);
    safe(initDeadlineTracker);
    safe(initDeadlineBadge);
    safe(initJournalExplorer);
    safe(initRankings);
    safe(initPalette);
    safe(initBackToTop);
    safe(initSkillSearch);
    safe(initQuoteBanner);
    // Last: it fires input events at widgets above, so they must be listening.
    safe(initDeepLinks);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
