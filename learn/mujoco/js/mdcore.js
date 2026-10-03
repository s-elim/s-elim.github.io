// Pure text utilities for lesson Markdown. No DOM access, so Node tests import it.
//
// Lessons are Markdown with three extensions:
//   * math: $inline$ and $$display$$ (KaTeX), protected from the Markdown parser;
//   * fenced directives: ```lab <name>, ```quiz, ```io, ```debug with a JSON body;
//   * callouts: a blockquote whose first line is [!tier] Optional title.

const MATH_TOKEN = (kind, i) => `MJCMATH${kind}${i}X`;

/**
 * Replace math with opaque tokens, skipping fenced code and inline code.
 * Returns { text, math } where math[i] = { tex, display }.
 */
export function protectMath(src) {
  const math = [];
  let out = "";
  let i = 0;
  const n = src.length;
  let lineStart = true;
  while (i < n) {
    // Fenced code block: copy verbatim to the closing fence.
    if (lineStart && /^ {0,3}(```|~~~)/.test(src.slice(i, i + 6))) {
      const fence = src.slice(i).match(/^ {0,3}(```+|~~~+)/)[1];
      const close = src.indexOf("\n" + fence, i + fence.length);
      const end = close === -1 ? n : src.indexOf("\n", close + 1 + fence.length);
      const stop = end === -1 ? n : end;
      out += src.slice(i, stop);
      i = stop;
      lineStart = false;
      continue;
    }
    const ch = src[i];
    if (ch === "`") {
      const run = src.slice(i).match(/^`+/)[0];
      const close = src.indexOf(run, i + run.length);
      if (close !== -1) {
        out += src.slice(i, close + run.length);
        i = close + run.length;
        lineStart = false;
        continue;
      }
    }
    if (ch === "\\" && src[i + 1] === "$") { out += "$"; i += 2; lineStart = false; continue; }
    if (ch === "$" && src[i + 1] === "$") {
      const close = src.indexOf("$$", i + 2);
      if (close !== -1) {
        math.push({ tex: src.slice(i + 2, close).trim(), display: true });
        out += MATH_TOKEN("D", math.length - 1);
        i = close + 2;
        lineStart = false;
        continue;
      }
    }
    if (ch === "$" && src[i + 1] && !/\s/.test(src[i + 1])) {
      // Inline math: closing $ on the same line, preceded by non-space.
      let j = i + 1;
      while (j < n && src[j] !== "\n") {
        if (src[j] === "\\") { j += 2; continue; }
        if (src[j] === "$" && !/\s/.test(src[j - 1])) break;
        j++;
      }
      if (j < n && src[j] === "$") {
        math.push({ tex: src.slice(i + 1, j), display: false });
        out += MATH_TOKEN("I", math.length - 1);
        i = j + 1;
        lineStart = false;
        continue;
      }
    }
    out += ch;
    lineStart = ch === "\n";
    i++;
  }
  return { text: out, math };
}

/** Put rendered math back; `render(tex, display)` returns HTML. */
export function restoreMath(html, math, render) {
  return html
    .replace(/<p>\s*MJCMATHD(\d+)X\s*<\/p>/g, (_, k) => render(math[+k].tex, true))
    .replace(/MJCMATH([DI])(\d+)X/g, (_, kind, k) => render(math[+k].tex, kind === "D"));
}

/**
 * Parse a fence info string such as
 *   python file=src/mjcourse/control.py title="PD control"
 * into { lang, attrs }.
 */
export function parseInfo(info) {
  const s = (info || "").trim();
  const m = s.match(/^(\S*)\s*(.*)$/);
  const lang = m ? m[1] : "";
  const attrs = {};
  const re = /(\w[\w-]*)(?:=(?:"([^"]*)"|(\S+)))?/g;
  let a;
  while ((a = re.exec(m ? m[2] : ""))) attrs[a[1]] = a[2] ?? a[3] ?? true;
  return { lang, attrs };
}

/** Lower-case, hyphenated id for a heading. */
export function slugify(text) {
  return String(text).toLowerCase().replace(/<[^>]+>/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
}

export const TIERS = {
  established: "Established MuJoCo behavior",
  derivation: "Mathematical derivation",
  implementation: "Implementation detail",
  recommendation: "Engineering recommendation",
  research: "Research-level interpretation",
  unverified: "Unverified",
  version: "Version note",
  warning: "Pitfall",
  try: "Try it",
  note: "Note",
};

/** Detect "[!tier] title" at the start of a callout; returns { tier, title, rest } or null. */
export function parseCalloutHead(text) {
  const m = String(text).match(/^\s*\[!(\w+)\]\s*([^\n]*)\n?([\s\S]*)$/);
  if (!m || !(m[1].toLowerCase() in TIERS)) return null;
  return { tier: m[1].toLowerCase(), title: m[2].trim(), rest: m[3] };
}
