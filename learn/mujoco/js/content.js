// Lesson rendering: Markdown to HTML, then directives to live widgets.
//
// INPUT   lesson Markdown (lessons/*.md, content/*.md, project READMEs)
// PROCESS protect math -> marked -> restore math as KaTeX -> build callouts,
//         code blocks with file links and copy buttons, directive placeholders
// OUTPUT  DOM inserted into a container, plus mount() for the widgets in it

import { MARKED_JS, KATEX_JS, HLJS_JS, HLJS_LANGS, loadScript } from "./vendor.js";
import { protectMath, restoreMath, parseInfo, slugify, parseCalloutHead, TIERS } from "./mdcore.js";
import { mountWidget } from "./widgets/registry.js";

const REPO = "https://github.com/s-elim/s-elim.github.io/blob/master/learn/mujoco/code/";
let markedPromise = null;

async function getMarked() {
  if (!markedPromise) {
    markedPromise = import(MARKED_JS).then(({ Marked }) => {
      const md = new Marked({ gfm: true, breaks: false });
      md.use({ renderer: { code: renderCode, heading: renderHeading } });
      return md;
    });
  }
  return markedPromise;
}

async function getKatex() {
  await loadScript(KATEX_JS);
  return window.katex;
}

async function getHljs() {
  await loadScript(HLJS_JS);
  await Promise.all(HLJS_LANGS.map((u) => loadScript(u)));
  return window.hljs;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderHeading({ tokens, depth }) {
  const text = this.parser.parseInline(tokens);
  const id = slugify(text);
  return `<h${depth} id="${id}">${text}</h${depth}>\n`;
}

function renderCode({ text, lang }) {
  const { lang: kind, attrs } = parseInfo(lang);
  if (kind === "lab" || kind === "quiz" || kind === "debug" || kind === "io") {
    const name = kind === "lab" ? Object.keys(attrs)[0] || "simlab" : kind;
    return `<div class="directive" data-directive="${esc(kind)}" data-name="${esc(name)}" data-config="${esc(text)}"></div>\n`;
  }
  const language = kind === "mjcf" ? "xml" : kind || "plaintext";
  const file = attrs.file ? `<span class="file"><a href="${REPO}${esc(attrs.file)}" target="_blank" rel="noopener">${esc(attrs.file)}</a></span>` : "";
  const title = attrs.title ? `<span class="file">${esc(attrs.title)}</span>` : "";
  const load = (language === "xml" && (attrs.load || kind === "mjcf"))
    ? `<button type="button" data-action="playground">Open in playground</button>` : "";
  return `<div class="codeblock" data-lang="${esc(language)}">
<div class="codeblock__bar"><span class="lang">${esc(kind || "text")}</span>${file}${title}<span class="spacer"></span>${load}<button type="button" data-action="copy">Copy</button></div>
<pre><code class="language-${esc(language)}">${esc(text)}</code></pre></div>\n`;
}

/** Render Markdown into `container`. Returns the list of directive placeholders. */
export async function renderInto(container, markdown) {
  const [md, katex] = await Promise.all([getMarked(), getKatex()]);
  const { text, math } = protectMath(markdown);
  let html = md.parse(text);
  html = restoreMath(html, math, (tex, display) => {
    try {
      const out = katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: "ignore" });
      return display ? `<div class="math-display">${out}</div>` : out;
    } catch (e) {
      return `<code class="math-error">${esc(tex)}</code>`;
    }
  });
  container.innerHTML = html;
  buildCallouts(container);
  wireCodeBlocks(container);
  getHljs().then((hljs) => {
    container.querySelectorAll(".codeblock pre code").forEach((el) => hljs.highlightElement(el));
  }).catch(() => { /* highlighting is optional */ });
  return Array.from(container.querySelectorAll(".directive"));
}

function buildCallouts(container) {
  for (const bq of container.querySelectorAll("blockquote")) {
    const first = bq.firstElementChild;
    if (!first || first.tagName !== "P") continue;
    const head = parseCalloutHead(first.innerHTML);
    if (!head) continue;
    const box = document.createElement("div");
    box.className = `callout callout--${head.tier}`;
    const label = document.createElement("div");
    label.className = "callout__label";
    label.textContent = head.title ? `${TIERS[head.tier]}: ${head.title}` : TIERS[head.tier];
    box.appendChild(label);
    if (head.rest.trim()) {
      const p = document.createElement("p");
      p.innerHTML = head.rest;
      box.appendChild(p);
    }
    first.remove();
    while (bq.firstChild) box.appendChild(bq.firstChild);
    bq.replaceWith(box);
  }
}

function wireCodeBlocks(container) {
  container.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const block = btn.closest(".codeblock");
    const code = block.querySelector("code").textContent;
    if (btn.dataset.action === "copy") {
      navigator.clipboard?.writeText(code).then(() => {
        btn.textContent = "Copied";
        setTimeout(() => { btn.textContent = "Copy"; }, 1200);
      }).catch(() => { btn.textContent = "Select and copy"; });
    } else if (btn.dataset.action === "playground") {
      try { sessionStorage.setItem("mjcourse:playground-xml", code); } catch (err) { /* ignore */ }
      location.hash = "#/playground?from=lesson";
    }
  });
}

/**
 * Mount every directive in `container`. Widgets mount lazily when they first
 * come near the viewport, so a long lesson does not create a WebGL context for
 * every lab at once. Returns a dispose() that tears all of them down.
 */
export function mountDirectives(placeholders, ctx = {}) {
  const handles = [];
  let disposed = false;
  const io = new IntersectionObserver((records) => {
    for (const r of records) {
      if (!r.isIntersecting) continue;
      io.unobserve(r.target);
      const el = r.target;
      let config = {};
      const raw = el.dataset.config || "";
      if (el.dataset.directive === "io" || el.dataset.directive === "debug") config = raw;
      else {
        try { config = raw.trim() ? JSON.parse(raw) : {}; }
        catch (err) {
          el.innerHTML = `<div class="widget__error">Directive JSON error: ${esc(err.message)}</div>`;
          continue;
        }
      }
      const kind = el.dataset.directive === "lab" ? el.dataset.name : el.dataset.directive;
      mountWidget(kind, el, config, ctx).then((h) => {
        if (!h) return;
        if (disposed) h.destroy?.(); // the page changed while this widget was loading
        else handles.push(h);
      });
    }
  }, { rootMargin: "300px" });
  placeholders.forEach((p) => io.observe(p));
  return () => {
    disposed = true;
    io.disconnect();
    handles.forEach((h) => { try { h.destroy?.(); } catch (e) { /* already gone */ } });
  };
}

export { esc };
