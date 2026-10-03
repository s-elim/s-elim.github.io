// io: the INPUT / PROCESS / OUTPUT summary that precedes substantial code.
// Body is plain text, one "LABEL: text" per line; inline `code` is honoured.

import { h } from "./ui.js";
import { esc } from "../content.js";

export async function mount(el, text) {
  const dl = h("dl", { class: "io" });
  for (const line of String(text).split("\n")) {
    const m = line.match(/^\s*([A-Z ]+):\s*(.*)$/);
    if (!m) continue;
    const html = esc(m[2]).replace(/`([^`]+)`/g, "<code>$1</code>");
    dl.append(h("dt", {}, m[1].trim()), h("dd", { html }));
  }
  el.innerHTML = "";
  el.appendChild(h("div", { class: "codeblock" }, dl));
  return { destroy() {} };
}
