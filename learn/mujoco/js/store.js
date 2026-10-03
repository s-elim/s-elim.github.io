// Progress store. Per-viewer conveniences only (completed lessons, quiz answers,
// last position), kept in localStorage. Every access is guarded: storage can be
// unavailable (private windows, blocked site data) and the course must still work.

const KEY = "mjcourse:v1";

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === "object") return { done: {}, quiz: {}, last: null, ...parsed };
  } catch (e) { /* fall through to a fresh state */ }
  return { done: {}, quiz: {}, last: null };
}

let state = read();
const listeners = new Set();

function write() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* storage unavailable */ }
  for (const fn of listeners) fn(state);
}

export const store = {
  get: () => state,
  onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); },
  isDone: (id) => Boolean(state.done[id]),
  setDone(id, done = true) {
    const next = { ...state.done };
    if (done) next[id] = new Date().toISOString(); else delete next[id];
    state = { ...state, done: next };
    write();
  },
  quizAnswer: (qid) => state.quiz[qid] || null,
  setQuizAnswer(qid, answer) {
    state = { ...state, quiz: { ...state.quiz, [qid]: answer } };
    write();
  },
  setLast(route) { state = { ...state, last: route }; write(); },
  reset() { state = { done: {}, quiz: {}, last: null }; write(); },
};

export function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try { localStorage.setItem("theme", theme); } catch (e) { /* storage unavailable */ }
}

export function currentTheme() {
  const t = document.documentElement.getAttribute("data-theme");
  if (t === "dark" || t === "light") return t;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
