// quiz: knowledge checks with prediction before reveal.
//
// Config: {"id": "1.3-a", "title": "Knowledge check", "questions": [ ... ]}
// Question kinds
//   mcq      {"kind": "mcq", "q": "...", "options": ["..."], "answer": 1, "explain": "..."}
//   predict  same as mcq, plus "sim": a simlab config mounted after the learner
//            commits to an answer, so the prediction is checked against MuJoCo
//   numeric  {"kind": "numeric", "q": "...", "answer": 0.44, "tol": 0.01, "unit": "s", "explain": "..."}
//   open     {"kind": "open", "q": "...", "reference": "model answer (Markdown-free HTML allowed)"}
// The answer key is in the page source; the point is to commit to an answer
// first, not to keep it secret.

import { h } from "./ui.js";
import { store } from "../store.js";

const KIND_LABEL = { mcq: "Concept", predict: "Predict, then simulate", numeric: "Compute", open: "Explain or design", debug: "Debugging", code: "Coding" };

export async function mount(el, config) {
  const qs = config.questions || [];
  const quizId = config.id || `quiz-${location.hash}`;
  const scoreEl = h("span", { class: "score" });
  const box = h("div", { class: "quiz" },
    h("div", { class: "quiz__head" }, config.title || "Knowledge check", scoreEl));
  el.innerHTML = "";
  el.appendChild(box);
  const results = new Array(qs.length).fill(null);
  const subs = [];

  const updateScore = () => {
    const graded = results.filter((r) => r !== null && r !== "open");
    const right = graded.filter(Boolean).length;
    scoreEl.textContent = graded.length ? `${right} / ${graded.length} correct` : "";
  };

  qs.forEach((q, i) => {
    const qid = `${quizId}#${i}`;
    const kind = q.kind || "mcq";
    const node = h("div", { class: "q" },
      h("div", { class: "q__kind" }, q.label || KIND_LABEL[kind] || kind),
      h("div", { class: "q__text", html: q.q }));
    const explain = h("div", { class: "q__explain", hidden: true });
    const saved = store.quizAnswer(qid);

    const reveal = (correct, extra = "") => {
      explain.hidden = false;
      const verdict = correct === null ? "" : `<span class="verdict ${correct ? "ok" : "no"}">${correct ? "Correct" : "Not quite"}</span>`;
      explain.innerHTML = verdict + (q.explain || "") + extra;
    };

    if (kind === "mcq" || kind === "predict" || kind === "debug") {
      const opts = h("div", { class: "q__options" });
      const buttons = q.options.map((text, k) => {
        const b = h("button", { type: "button", class: "q__opt", html: text });
        b.onclick = () => choose(k, true);
        opts.appendChild(b);
        return b;
      });
      const choose = async (k, fresh) => {
        buttons.forEach((b, j) => {
          b.disabled = true;
          b.classList.toggle("is-right", j === q.answer);
          b.classList.toggle("is-wrong", j === k && k !== q.answer);
        });
        results[i] = k === q.answer;
        if (fresh) store.setQuizAnswer(qid, { choice: k, correct: results[i] });
        reveal(results[i]);
        updateScore();
        if (kind === "predict" && q.sim && !node.querySelector(".q__sim")) {
          const holder = h("div", { class: "q__sim" });
          node.appendChild(holder);
          const { mount: mountSim } = await import("./simlab.js");
          subs.push(await mountSim(holder, { autoplay: true, kind: "Check", title: "MuJoCo's answer", ...q.sim }));
        }
      };
      node.appendChild(opts);
      node.appendChild(explain);
      if (saved && typeof saved.choice === "number") choose(saved.choice, false);
    } else if (kind === "numeric") {
      const input = h("input", { type: "number", step: "any", placeholder: q.unit ? `answer in ${q.unit}` : "answer" });
      const go = h("button", { type: "button", class: "btn" }, "Check");
      const check = (fresh) => {
        const v = parseFloat(input.value);
        if (!Number.isFinite(v)) return;
        const tol = q.tol ?? Math.abs(q.answer) * 0.02;
        results[i] = Math.abs(v - q.answer) <= tol;
        if (fresh) store.setQuizAnswer(qid, { value: v, correct: results[i] });
        reveal(results[i], `<p>Reference: <b>${q.answer}${q.unit ? " " + q.unit : ""}</b> (tolerance ${tol}).</p>`);
        updateScore();
      };
      go.onclick = () => check(true);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") check(true); });
      node.append(h("div", { class: "q__row" }, input, go), explain);
      if (saved && typeof saved.value === "number") { input.value = saved.value; check(false); }
    } else {
      const ta = h("textarea", { placeholder: "Write your answer before revealing the reference." });
      const go = h("button", { type: "button", class: "btn" }, "Reveal reference answer");
      go.onclick = () => {
        results[i] = "open";
        store.setQuizAnswer(qid, { text: ta.value, revealed: true });
        explain.hidden = false;
        explain.innerHTML = `<span class="verdict ok">Reference answer</span>${q.reference || q.explain || ""}`;
        updateScore();
      };
      if (saved && saved.text) ta.value = saved.text;
      node.append(ta, h("div", { class: "q__row" }, go), explain);
    }
    box.appendChild(node);
  });
  updateScore();
  return { destroy() { subs.forEach((s) => s?.destroy?.()); } };
}
