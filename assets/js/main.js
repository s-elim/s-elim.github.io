/* ==========================================================================
   Modern Academic theme — interactions (vanilla, no dependencies)
   ========================================================================== */
(function () {
  "use strict";

  var root = document.documentElement;
  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Theme toggle -------------------------------------------------- */
  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") return attr;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
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
      var anyVisible = false;
      cards.forEach(function (card) {
        var ok = true;
        for (var key in groups) {
          if (groups[key] !== "all" && card.getAttribute("data-" + key) !== groups[key]) { ok = false; break; }
        }
        if (ok && term) {
          ok = (card.getAttribute("data-search") || "").indexOf(term) !== -1;
        }
        card.hidden = !ok;
        if (ok) anyVisible = true;
      });
      sections.forEach(function (sec) {
        var visible = sec.querySelectorAll(".pub-card:not([hidden])").length;
        sec.hidden = visible === 0;
      });
      if (empty) empty.classList.toggle("show", !anyVisible);
    }

    if (search) search.addEventListener("input", apply);
    apply();
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
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
