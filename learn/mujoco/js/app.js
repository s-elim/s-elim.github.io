// Course application: routing, navigation, pages, search, shortcuts, progress.
//
// Routes (hash-based, so the course works from any static host):
//   #/                      course map
//   #/lesson/<id>           a lesson, e.g. #/lesson/1.3
//   #/playground            full-page MJCF playground
//   #/page/<id>             a content page (debugging clinic, reading list, ...)
//   #/project/<slug>        a project README from code/projects/<slug>/README.md
//   #/capstone/<slug>       a capstone README from code/capstones/<slug>/README.md

import { store, setTheme, currentTheme } from "./store.js";
import { renderInto, mountDirectives, esc } from "./content.js";
import { activeLab } from "./loop.js";
import { mountWidget } from "./widgets/registry.js";

const state = { course: null, lessons: [], byId: new Map(), cleanup: null, search: null };
const $ = (sel) => document.querySelector(sel);

async function boot() {
  const res = await fetch(new URL("../course.json", import.meta.url));
  state.course = await res.json();
  for (const level of state.course.levels) {
    for (const l of level.lessons) {
      const lesson = { ...l, level: level.id, levelTitle: level.title };
      state.lessons.push(lesson);
      state.byId.set(l.id, lesson);
    }
  }
  buildNav();
  wireChrome();
  updateProgress();
  store.onChange(() => { updateProgress(); refreshNavDone(); });
  window.addEventListener("hashchange", route);
  route();
}

// ------------------------------------------------------------------ chrome

function wireChrome() {
  $("#theme-toggle").onclick = toggleTheme;
  $("#search-open").onclick = openSearch;
  $("#shortcuts-open").onclick = () => $("#shortcuts").showModal();
  const nav = $("#sidenav"), scrim = $("#scrim"), toggle = $("#nav-toggle");
  const setNav = (open) => {
    nav.classList.toggle("is-open", open);
    scrim.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  };
  toggle.onclick = () => setNav(!nav.classList.contains("is-open"));
  scrim.onclick = () => setNav(false);
  nav.addEventListener("click", (e) => { if (e.target.closest("a")) setNav(false); });
  document.addEventListener("keydown", onKey);
}

function toggleTheme() {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
  // Viewers read their background colour from CSS at build time; rebuild the page.
  route();
}

let pendingG = false;
function onKey(e) {
  const tag = (e.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable || e.target.closest?.(".CodeMirror")) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.querySelector("dialog[open]")) return;
  const k = e.key;
  if (pendingG) {
    pendingG = false;
    if (k === "h") { location.hash = "#/"; e.preventDefault(); return; }
    if (k === "p") { location.hash = "#/playground"; e.preventDefault(); return; }
  }
  if (k === "g") { pendingG = true; setTimeout(() => { pendingG = false; }, 900); return; }
  if (k === "/") { e.preventDefault(); openSearch(); return; }
  if (k === "?") { $("#shortcuts").showModal(); return; }
  if (k === "t") { toggleTheme(); return; }
  const lesson = currentLesson();
  if (k === "j" && lesson) { goRelative(lesson, 1); return; }
  if (k === "k" && lesson) { goRelative(lesson, -1); return; }
  if (k === "m" && lesson) { store.setDone(lesson.id, !store.isDone(lesson.id)); syncDoneButton(lesson); return; }
  const lab = activeLab();
  if (!lab) return;
  if (k === " ") { e.preventDefault(); lab.toggle?.(); }
  else if (k === ".") lab.step?.();
  else if (k === "r") lab.reset?.();
}

function currentLesson() {
  const m = location.hash.match(/^#\/lesson\/([\d.]+)/);
  return m ? state.byId.get(m[1]) : null;
}

function goRelative(lesson, delta) {
  const i = state.lessons.indexOf(lesson);
  const next = state.lessons[i + delta];
  if (next) location.hash = `#/lesson/${next.id}`;
}

function updateProgress() {
  const total = state.lessons.length;
  const done = state.lessons.filter((l) => store.isDone(l.id)).length;
  const pct = total ? Math.round((100 * done) / total) : 0;
  $("#progress-text").textContent = `${pct}%`;
  $("#progress-ring").style.strokeDashoffset = String(94.25 * (1 - done / Math.max(total, 1)));
  $("#progress-pill").title = `${done} of ${total} lessons marked complete in this browser`;
}

// ---------------------------------------------------------------- navigation

function buildNav() {
  const tree = $("#nav-tree");
  const pages = state.course.pages;
  const link = (href, text, extra = "") => `<a class="nav-link" href="${href}">${extra}${esc(text)}</a>`;
  let html = `<div class="nav-section"><div class="nav-section__title">Start</div>
    ${link("#/", "Course map")}
    ${link("#/page/about", "How this course works")}
    ${link("#/playground", "Playground")}
    ${link("#/page/showcase", "Showcase")}
  </div><div class="nav-section"><div class="nav-section__title">Levels</div>`;
  for (const level of state.course.levels) {
    html += `<details class="nav-level" data-level="${level.id}"><summary><span class="nav-level__num">L${level.id}</span>${esc(level.title)}<span class="nav-level__done" data-level-done="${level.id}"></span></summary><div class="nav-level__lessons">`;
    for (const l of level.lessons) {
      html += `<a class="nav-link" href="#/lesson/${l.id}" data-lesson="${l.id}"><span class="nav-dot ${l.status === "planned" ? "is-planned" : ""}" data-dot="${l.id}"></span>${l.id} ${esc(l.title)}</a>`;
    }
    html += `</div></details>`;
  }
  html += `</div><div class="nav-section"><div class="nav-section__title">Labs and practice</div>`;
  for (const p of pages) if (!["about", "playground", "showcase"].includes(p.id)) html += link(`#/page/${p.id}`, p.title);
  html += `</div>`;
  tree.innerHTML = html;
  refreshNavDone();
}

function refreshNavDone() {
  for (const l of state.lessons) {
    const dot = document.querySelector(`[data-dot="${CSS.escape(l.id)}"]`);
    if (dot) dot.classList.toggle("is-done", store.isDone(l.id));
  }
  for (const level of state.course.levels) {
    const n = level.lessons.filter((l) => store.isDone(l.id)).length;
    const el = document.querySelector(`[data-level-done="${level.id}"]`);
    if (el) el.textContent = n ? `${n}/${level.lessons.length}` : "";
  }
}

function highlightNav() {
  const hash = location.hash || "#/";
  document.querySelectorAll(".nav-link").forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === hash.split("?")[0]));
  const lesson = currentLesson();
  if (lesson) {
    const det = document.querySelector(`.nav-level[data-level="${lesson.level}"]`);
    if (det) det.open = true;
    document.querySelector(`[data-lesson="${CSS.escape(lesson.id)}"]`)?.scrollIntoView({ block: "nearest" });
  }
}

// -------------------------------------------------------------------- routing

async function route() {
  if (state.cleanup) { try { state.cleanup(); } catch (e) { console.error(e); } state.cleanup = null; }
  const hash = location.hash || "#/";
  const main = $("#main");
  main.innerHTML = "";
  highlightNav();
  window.scrollTo(0, 0);
  const [path] = hash.slice(1).split("?");
  const parts = path.split("/").filter(Boolean);
  try {
    if (parts.length === 0) await renderHome(main);
    else if (parts[0] === "lesson") await renderLesson(main, parts[1]);
    else if (parts[0] === "playground") await renderPlayground(main);
    else if (parts[0] === "page") await renderPage(main, parts[1]);
    else if (parts[0] === "project" || parts[0] === "capstone") await renderReadme(main, parts[0], parts[1]);
    else main.innerHTML = `<div class="home"><h1>Not found</h1><p><a href="#/">Back to the course map</a></p></div>`;
    store.setLast(hash);
  } catch (err) {
    console.error(err);
    main.innerHTML = `<div class="home"><div class="widget__error">${esc(err.message)}</div><p><a href="#/">Back to the course map</a></p></div>`;
  }
  main.focus({ preventScroll: true });
}

// ------------------------------------------------------------------- home

async function renderHome(main) {
  const c = state.course;
  const nLessons = state.lessons.length;
  const minutes = state.lessons.reduce((a, l) => a + l.minutes, 0);
  const last = store.get().last;
  const resume = last && last.startsWith("#/lesson/") ? `<a class="btn" href="${last}">Resume where you left off</a>` : "";
  const wrap = document.createElement("div");
  wrap.className = "home";
  wrap.innerHTML = `
  <section class="hero">
    <div>
      <div class="kicker">Interactive course, MuJoCo ${esc(c.mujoco)}</div>
      <h1>MuJoCo, from zero to research</h1>
      <p>A course that starts with what a physics simulator computes and ends with experiments a reviewer would accept: MJCF, the Python and JavaScript APIs, kinematics, dynamics, control, contact, manipulation, cameras, Gymnasium, reinforcement and imitation learning, vision and language conditioning, domain randomization, system identification, sim-to-real, the engine's internals, and research methodology.</p>
      <p>The labs on these pages run the real MuJoCo engine, compiled to WebAssembly, in your browser. Every lab has a Python counterpart in the companion package, and every code block in a lesson marked complete was executed against MuJoCo ${esc(c.mujoco)}.</p>
      <div class="hero__cta">
        <a class="btn btn--primary" href="#/lesson/0.1">Start at Level 0</a>
        ${resume}
        <a class="btn" href="#/page/showcase">See the showcase</a>
        <a class="btn" href="#/playground">Open the playground</a>
        <a class="btn" href="#/page/about">How the course works</a>
      </div>
    </div>
    <div class="hero__lab" id="hero-lab"></div>
  </section>
  <div class="facts">
    <div class="fact"><b>${c.levels.length}</b><span>levels, 0 to ${c.levels.length - 1}</span></div>
    <div class="fact"><b>${nLessons}</b><span>lessons</span></div>
    <div class="fact"><b>${Math.round(minutes / 60)} h</b><span>estimated study time, labs excluded</span></div>
    <div class="fact"><b>20 + 8</b><span>projects and capstones</span></div>
  </div>
  <h2 class="section-title">The levels</h2>
  <p class="section-sub">Each level ends with an expert checkpoint that asks you to build something without a template. Lessons marked <span class="status status--planned">planned</span> have a fixed syllabus but no text yet; nothing on this site pretends otherwise.</p>
  <div class="levelgrid">${c.levels.map((lv) => {
    const done = lv.lessons.filter((l) => store.isDone(l.id)).length;
    const written = lv.lessons.filter((l) => l.status !== "planned").length;
    const mins = lv.lessons.reduce((a, l) => a + l.minutes, 0);
    return `<a class="levelcard" href="#/lesson/${lv.lessons[0].id}">
      <span class="levelcard__num">Level ${lv.id} <span class="track">${esc(lv.track)}</span></span>
      <span class="levelcard__title">${esc(lv.title)}</span>
      <span class="levelcard__sum">${esc(lv.summary)}</span>
      <span class="levelcard__bar"><i style="width:${(100 * done) / lv.lessons.length}%"></i></span>
      <span class="levelcard__meta"><span>${lv.lessons.length} lessons, ${written} written</span><span>${mins} min</span></span>
    </a>`;
  }).join("")}</div>
  <h2 class="section-title">Labs, practice and reference</h2>
  <div class="toolgrid">${c.pages.map((p) => `<a class="toolcard" href="${p.id === "playground" ? "#/playground" : `#/page/${p.id}`}"><b>${esc(p.title)}</b><span>${esc(p.summary)}</span></a>`).join("")}</div>
  <h2 class="section-title">Where to start</h2>
  <div class="pathways">
    <div class="pathway"><b>New to simulation</b>Levels 0 to 3 in order, then 4 and 5. Do every prediction question before running the lab.</div>
    <div class="pathway"><b>Python programmer</b>Skim Level 0, do Levels 1 to 3 properly (views versus copies will bite you otherwise), then follow your interest.</div>
    <div class="pathway"><b>Robotics student</b>Levels 1 to 3 for the API, then 6 to 10. Levels 4 and 7 check your mechanics against the engine.</div>
    <div class="pathway"><b>ML or RL researcher</b>Levels 1 to 3, 9 (contact will decide your results), then 12 to 14, 17 and 21.</div>
    <div class="pathway"><b>VLA and embodied-AI researcher</b>Levels 1 to 3, 10, 11, 15, 16, then 21. Read 9.2 and 9.3 before trusting a grasp success rate.</div>
    <div class="pathway"><b>Experienced roboticist</b>Level 0.3 (boundaries), 9.2, 20 (internals) and 21. Take the final exam first and read only what it exposes.</div>
  </div>`;
  main.appendChild(wrap);
  const heroLab = wrap.querySelector("#hero-lab");
  const h = await mountWidget("simlab", heroLab, {
    kind: "Live", title: "A double pendulum, simulated by MuJoCo in this page", model: "double_pendulum", key: 0, height: 260, autoplay: true,
    camera: { azimuth: -90, elevation: 5, distance: 1.9, target: [0, 0, 0.7] }, trail: "tip",
    readouts: [{ label: "time (s)", expr: "data.time" }, { label: "energy (J)", expr: "lib.energy().total", digits: 4 }],
  });
  state.cleanup = () => h?.destroy();
}

// ------------------------------------------------------------------ lessons

function difficulty(n) {
  return `<span class="difficulty" title="Difficulty ${n} of 5" aria-label="Difficulty ${n} of 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</span>`;
}

async function renderLesson(main, id) {
  const lesson = state.byId.get(id);
  if (!lesson) { main.innerHTML = `<div class="home"><p>No lesson ${esc(id)}. <a href="#/">Course map</a></p></div>`; return; }
  const level = state.course.levels.find((lv) => lv.id === lesson.level);
  const idx = state.lessons.indexOf(lesson);
  const prev = state.lessons[idx - 1], next = state.lessons[idx + 1];
  const isLastInLevel = level.lessons[level.lessons.length - 1].id === lesson.id;

  const wrap = document.createElement("div");
  wrap.className = `lesson ${lesson.lab ? "" : "lesson--nolab"}`;
  const prereqs = lesson.prereqs.length
    ? `<ul>${lesson.prereqs.map((p) => { const l = state.byId.get(p); return `<li><a href="#/lesson/${p}">${p} ${esc(l ? l.title : "")}</a></li>`; }).join("")}</ul>`
    : `<p class="none">None. This is a starting point.</p>`;
  wrap.innerHTML = `
    <article class="lesson__body">
      <div class="crumbs"><a href="#/">Course map</a><span>/</span><span>Level ${level.id}: ${esc(level.title)}</span></div>
      <h1>${esc(lesson.id)} ${esc(lesson.title)}</h1>
      <div class="meta-row">
        <span class="status status--${lesson.status}">${lesson.status}</span>
        <span class="chip">${lesson.minutes} min</span>
        <span class="chip">difficulty ${difficulty(lesson.difficulty)}</span>
        <span class="chip">${esc(level.track)}</span>
      </div>
      <div class="overview">
        <div class="overview__box"><h2>Prerequisites</h2>${prereqs}</div>
        <div class="overview__box"><h2>Learning objectives</h2><ul>${lesson.objectives.map((o) => `<li>${esc(o)}</li>`).join("")}</ul></div>
      </div>
      <div class="prose" id="lesson-prose"><p class="widget__note">Loading lesson&hellip;</p></div>
      ${isLastInLevel && level.checkpoint ? `<section class="checkpoint"><h2>${esc(level.checkpoint.title)}</h2><p>${esc(level.checkpoint.task)}</p><ul>${level.checkpoint.accept.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></section>` : ""}
      <div class="lesson-foot">
        <button type="button" class="btn" id="done-btn"></button>
        <span class="widget__note">Progress is stored only in this browser.</span>
      </div>
      <nav class="pager" aria-label="Lesson navigation">
        ${prev ? `<a class="prev" href="#/lesson/${prev.id}"><small>Previous</small>${esc(prev.id)} ${esc(prev.title)}</a>` : "<span></span>"}
        ${next ? `<a class="next" href="#/lesson/${next.id}"><small>Next lesson</small>${esc(next.id)} ${esc(next.title)}</a>` : ""}
      </nav>
    </article>
    ${lesson.lab ? `<aside class="labdock" aria-label="Lesson lab"><div class="labdock__title">Lab for this lesson</div><div id="lab-slot"></div></aside>` : ""}`;
  main.appendChild(wrap);
  syncDoneButton(lesson);
  wrap.querySelector("#done-btn").onclick = () => { store.setDone(lesson.id, !store.isDone(lesson.id)); syncDoneButton(lesson); };

  const prose = wrap.querySelector("#lesson-prose");
  const disposers = [];
  if (lesson.status === "planned") {
    prose.innerHTML = plannedNotice(lesson);
  } else {
    const res = await fetch(new URL(`../lessons/${lesson.id}-${lesson.slug}.md`, import.meta.url));
    if (!res.ok) throw new Error(`Lesson file missing (HTTP ${res.status}).`);
    const md = await res.text();
    const placeholders = await renderInto(prose, md);
    // The first lab directive marked "dock" moves into the side panel.
    const slot = wrap.querySelector("#lab-slot");
    const dockable = placeholders.find((p) => p.dataset.directive === "lab" && /"dock"\s*:\s*true/.test(p.dataset.config));
    if (slot && dockable) slot.appendChild(dockable);
    else if (slot && !dockable) wrap.querySelector(".labdock")?.remove(), wrap.classList.add("lesson--nolab");
    disposers.push(mountDirectives(placeholders, { lesson }));
  }
  if (lesson.status === "planned" && lesson.lab) {
    wrap.querySelector(".labdock")?.remove();
    wrap.classList.add("lesson--nolab");
  }
  state.cleanup = () => disposers.forEach((d) => d());
}

function plannedNotice(lesson) {
  const written = state.lessons.filter((l) => l.status !== "planned" && l.level <= lesson.level).slice(-3);
  return `<div class="callout callout--note"><div class="callout__label">Planned lesson</div>
    <p>The syllabus above is fixed, but the text of this lesson is not written yet. It will be published here once its code has been executed against MuJoCo 3.14.0 and its lab tested; until then this page shows only what the lesson will cover.</p>
    ${written.length ? `<p>Closest written material: ${written.map((l) => `<a href="#/lesson/${l.id}">${l.id} ${esc(l.title)}</a>`).join(", ")}.</p>` : ""}
    <p>The <a href="#/playground">playground</a> runs every model in the course library today.</p></div>`;
}

function syncDoneButton(lesson) {
  const btn = document.querySelector("#done-btn");
  if (!btn) return;
  const done = store.isDone(lesson.id);
  btn.textContent = done ? "Completed (click to undo)" : "Mark lesson complete (m)";
  btn.classList.toggle("btn--primary", !done);
}

// ----------------------------------------------------------- other pages

async function renderPlayground(main) {
  const holder = document.createElement("div");
  main.appendChild(holder);
  const h = await mountWidget("playground", holder, { full: true });
  state.cleanup = () => h?.destroy();
}

async function renderPage(main, id) {
  const page = state.course.pages.find((p) => p.id === id);
  if (!page || !page.file) { main.innerHTML = `<div class="home"><p>No page ${esc(id)}. <a href="#/">Course map</a></p></div>`; return; }
  await renderMarkdownPage(main, new URL(`../${page.file}`, import.meta.url), page.title);
}

async function renderReadme(main, kind, slug) {
  const dir = kind === "project" ? "projects" : "capstones";
  if (!/^[\w-]+$/.test(slug || "")) throw new Error("Bad project name.");
  await renderMarkdownPage(main, new URL(`../code/${dir}/${slug}/README.md`, import.meta.url), null, `code/${dir}/${slug}/`);
}

async function renderMarkdownPage(main, url, title, repoPath = null) {
  const wrap = document.createElement("div");
  wrap.className = "lesson lesson--nolab";
  wrap.innerHTML = `<article class="lesson__body"><div class="crumbs"><a href="#/">Course map</a>${repoPath ? `<span>/</span><a href="https://github.com/s-elim/s-elim.github.io/tree/master/learn/mujoco/${repoPath}" target="_blank" rel="noopener">${esc(repoPath)}</a>` : ""}</div>${title ? `<h1>${esc(title)}</h1>` : ""}<div class="prose" id="page-prose"></div></article>`;
  main.appendChild(wrap);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Page not found (HTTP ${res.status}).`);
  const placeholders = await renderInto(wrap.querySelector("#page-prose"), await res.text());
  const dispose = mountDirectives(placeholders, {});
  state.cleanup = dispose;
}

// ------------------------------------------------------------------ search

async function loadSearchIndex() {
  if (state.search) return state.search;
  const items = [];
  for (const l of state.lessons) {
    items.push({ kind: "lesson", href: `#/lesson/${l.id}`, title: `${l.id} ${l.title}`, text: `${l.objectives.join(" ")} ${l.levelTitle}`, status: l.status });
  }
  for (const p of state.course.pages) items.push({ kind: "page", href: p.id === "playground" ? "#/playground" : `#/page/${p.id}`, title: p.title, text: p.summary });
  try {
    const res = await fetch(new URL("../search-index.json", import.meta.url));
    if (res.ok) {
      const extra = await res.json();
      for (const e of extra) {
        const base = items.find((it) => it.href === e.href);
        if (base) base.text += " " + e.text; else items.push(e);
      }
    }
  } catch (e) { /* the built index is optional */ }
  state.search = items;
  return items;
}

function openSearch() {
  const dlg = $("#palette"), input = $("#palette-input"), list = $("#palette-results");
  let sel = 0, results = [];
  const render = async () => {
    const items = await loadSearchIndex();
    const q = input.value.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    results = (terms.length ? items.map((it) => {
      const hay = `${it.title} ${it.text}`.toLowerCase();
      if (!terms.every((t) => hay.includes(t))) return null;
      const score = terms.reduce((a, t) => a + (it.title.toLowerCase().includes(t) ? 5 : 1), 0);
      return { it, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score).map((r) => r.it) : items.slice(0, 12)).slice(0, 30);
    sel = Math.min(sel, Math.max(results.length - 1, 0));
    const mark = (s) => { let out = esc(s); for (const t of terms) out = out.replace(new RegExp(`(${t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"), "<mark>$1</mark>"); return out; };
    list.innerHTML = results.map((r, i) => {
      const snippet = snippetFor(r.text, terms);
      return `<li class="${i === sel ? "is-sel" : ""}"><a href="${r.href}"><span class="kind">${r.kind}${r.status === "planned" ? " (planned)" : ""}</span>${mark(r.title)}<small>${mark(snippet)}</small></a></li>`;
    }).join("") || `<li><a><small>No match. Try an API name such as mj_jacSite or a concept such as friction cone.</small></a></li>`;
  };
  input.oninput = () => { sel = 0; render(); };
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, results.length - 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); }
    else if (e.key === "Enter" && results[sel]) { location.hash = results[sel].href; dlg.close(); }
  };
  list.onclick = (e) => { if (e.target.closest("a[href]")) dlg.close(); };
  input.value = "";
  dlg.showModal();
  input.focus();
  render();
}

function snippetFor(text, terms) {
  if (!text) return "";
  if (!terms.length) return text.slice(0, 110);
  const lower = text.toLowerCase();
  const i = lower.indexOf(terms[0]);
  const start = Math.max(0, i - 50);
  return (start ? "…" : "") + text.slice(start, start + 140) + (start + 140 < text.length ? "…" : "");
}

boot().catch((err) => {
  console.error(err);
  $("#main").innerHTML = `<div class="home"><div class="widget__error">The course could not start: ${esc(err.message)}</div></div>`;
});
