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
  function initPubFilter() {
    var list = document.getElementById("pub-list");
    if (!list) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(".pub-card"));
    var sections = Array.prototype.slice.call(list.querySelectorAll(".pub-year-section"));
    var search = document.getElementById("pub-search");
    var empty = document.getElementById("pub-empty");
    var groups = {};
    document.querySelectorAll(".filter-chips[data-group]").forEach(function (g) {
      groups[g.getAttribute("data-group")] = "all";
      g.querySelectorAll(".filter-chip").forEach(function (chip) {
        chip.addEventListener("click", function () {
          g.querySelectorAll(".filter-chip").forEach(function (c) { c.classList.remove("is-active"); });
          chip.classList.add("is-active");
          groups[g.getAttribute("data-group")] = chip.getAttribute("data-value");
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
          if (groups[key] !== "all" && card.getAttribute("data-" + key) !== groups[key]) { ok = false; break; }
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
    }

    if (search) search.addEventListener("input", apply);
    apply();
  }

  /* ---- Activities filter (fun-time) ----------------------------------- */
  function initActivityFilter() {
    var list = document.getElementById("activity-list");
    var chipsWrap = document.getElementById("activity-filters");
    if (!list || !chipsWrap) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(".activity-card"));
    var sections = Array.prototype.slice.call(list.querySelectorAll(".activity-year"));
    var empty = document.getElementById("activity-empty");

    function apply(value) {
      var anyVisible = false;
      cards.forEach(function (card) {
        var ok = value === "all" || card.getAttribute("data-cat") === value;
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
        chipsWrap.querySelectorAll(".filter-chip").forEach(function (c) { c.classList.remove("is-active"); });
        chip.classList.add("is-active");
        apply(chip.getAttribute("data-value"));
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
    safe(initPubFilter);
    safe(initActivityFilter);
    safe(initUpdatesScroll);
    safe(initLightbox);
    safe(initModals);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
