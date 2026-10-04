"""Static checks for the course content. Run before every publish.

INPUT   course.json, lessons/*.md, content/*.md, code/projects/*/README.md,
        code/capstones/*/README.md
PROCESS for every Markdown file:
          * every ```lab / ```quiz / ```debug block parses as JSON (lab, quiz, debug)
          * every lab names a registered widget and every "model" exists
          * every code block with file=PATH is identical to code/PATH
          * no em dash (U+2014) and none of the banned filler words in prose
        for course.json: lesson files exist for every non-planned lesson, ids and
        prerequisites resolve, and no lesson file exists for a planned lesson
OUTPUT  a list of problems; exit status 1 if there are any

Usage:  python tools/check_content.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
MODELS = CODE / "src" / "mjcourse" / "models"
WIDGETS = set(re.findall(r"^\s+(\w+): \(\) => import", (ROOT / "js/widgets/registry.js").read_text(), re.M))

# Words the author's style guide bans from all prose (proper nouns excepted).
BANNED = ["delve", "leverage", "crucial", "pivotal", "seamless", "showcase", "unlock",
          "foster", "myriad", "it is important to note", "in today's rapidly evolving",
          "at its core", "plays a vital role", "serves as a testament"]
LINK_TARGET = re.compile(r"\]\([^)\s]*\)")
BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\w*\b", re.I)
HARNESS_VERB = re.compile(r"\bharness(es|ed|ing)?\b(?! and graph)", re.I)
FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```\s*$", re.M | re.S)


def model_exists(name: str) -> bool:
    filename = name if name.endswith(".xml") else f"{name}.xml"
    return (MODELS / filename).exists()


def check_markdown(path: Path, problems: list[str]) -> None:
    text = path.read_text()
    rel = path.relative_to(ROOT)
    if text.startswith("---"):
        problems.append(f"{rel}: starts with '---'; Jekyll would treat it as front matter and not publish the .md")
    if "—" in text:
        for i, line in enumerate(text.splitlines(), 1):
            if "—" in line:
                problems.append(f"{rel}:{i}: em dash")
    prose = LINK_TARGET.sub("]()", FENCE.sub("", text))         # link targets are URLs, not prose
    for i, line in enumerate(prose.splitlines(), 1):
        for m in BANNED_RE.finditer(line):
            problems.append(f"{rel}: banned word '{m.group(0)}' in: {line.strip()[:90]}")
        if HARNESS_VERB.search(line):
            problems.append(f"{rel}: 'harness' used as a verb or noun in prose: {line.strip()[:90]}")

    for m in FENCE.finditer(text):
        info, body = m.group(1).strip(), m.group(2)
        line = text[: m.start()].count("\n") + 1
        kind = info.split()[0] if info else ""
        if kind in ("lab", "quiz", "debug"):
            try:
                cfg = json.loads(body) if body.strip() else {}
            except json.JSONDecodeError as e:
                problems.append(f"{rel}:{line}: {kind} block is not valid JSON: {e}")
                continue
            if kind == "lab":
                name = info.split()[1] if len(info.split()) > 1 else "simlab"
                if name not in WIDGETS:
                    problems.append(f"{rel}:{line}: unknown lab widget '{name}'")
                for model in _models_in(cfg):
                    if not model_exists(model):
                        problems.append(f"{rel}:{line}: lab model '{model}' not found")
            if kind == "quiz":
                for q in cfg.get("questions", []):
                    if q.get("kind", "mcq") in ("mcq", "predict", "debug"):
                        if not 0 <= q.get("answer", -1) < len(q.get("options", [])):
                            problems.append(f"{rel}:{line}: quiz answer index out of range: {q.get('q', '')[:60]}")
                    for model in _models_in(q.get("sim", {})):
                        if not model_exists(model):
                            problems.append(f"{rel}:{line}: quiz sim model '{model}' not found")
            if kind == "debug" and "model" in cfg and not model_exists(cfg["model"]):
                problems.append(f"{rel}:{line}: debug model '{cfg['model']}' not found")
        file_attr = re.search(r'\bfile=("[^"]+"|\S+)', info)
        if file_attr:
            target = CODE / file_attr.group(1).strip('"')
            if not target.exists():
                problems.append(f"{rel}:{line}: code block file '{target.relative_to(ROOT)}' does not exist")
            elif target.read_text().rstrip("\n") != body.rstrip("\n"):
                problems.append(f"{rel}:{line}: code block differs from {target.relative_to(ROOT)} (embed the file verbatim)")


def _models_in(cfg) -> list[str]:
    out = []
    if isinstance(cfg, dict):
        if isinstance(cfg.get("model"), str):
            out.append(cfg["model"])
        for v in cfg.values():
            if isinstance(v, (dict, list)):
                out.extend(_models_in(v))
    elif isinstance(cfg, list):
        for v in cfg:
            out.extend(_models_in(v))
    return out


def check_course(problems: list[str]) -> None:
    course = json.loads((ROOT / "course.json").read_text())
    ids = {}
    for level in course["levels"]:
        for lesson in level["lessons"]:
            if lesson["id"] in ids:
                problems.append(f"course.json: duplicate lesson id {lesson['id']}")
            ids[lesson["id"]] = lesson
    for lid, lesson in ids.items():
        f = ROOT / "lessons" / f"{lid}-{lesson['slug']}.md"
        if lesson["status"] != "planned" and not f.exists():
            problems.append(f"course.json: lesson {lid} is '{lesson['status']}' but {f.name} is missing")
        if lesson["status"] == "planned" and f.exists():
            problems.append(f"course.json: lesson {lid} is 'planned' but {f.name} exists (update its status)")
        for p in lesson["prereqs"]:
            if p not in ids:
                problems.append(f"course.json: lesson {lid} has unknown prerequisite {p}")
        if lesson.get("lab") and lesson["lab"] not in WIDGETS:
            problems.append(f"course.json: lesson {lid} names unknown lab {lesson['lab']}")
    for page in course["pages"]:
        if page.get("file") and not (ROOT / page["file"]).exists():
            problems.append(f"course.json: page {page['id']} file {page['file']} is missing")
    for f in (ROOT / "lessons").glob("*.md"):
        lid = f.name.split("-")[0]
        if lid not in ids:
            problems.append(f"lessons/{f.name}: no lesson {lid} in course.json")


def main() -> int:
    problems: list[str] = []
    check_course(problems)
    files = sorted((ROOT / "lessons").glob("*.md")) + sorted((ROOT / "content").glob("*.md"))
    files += sorted((CODE / "projects").glob("*/README.md")) + sorted((CODE / "capstones").glob("*/README.md"))
    for f in files:
        check_markdown(f, problems)
    for p in problems:
        print(p)
    print(f"checked {len(files)} Markdown files: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
