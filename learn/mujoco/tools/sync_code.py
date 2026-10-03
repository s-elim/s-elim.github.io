"""Rewrite every fenced code block that names a file (```python file=PATH) with
that file's current content, so lessons always embed the code that the test
suite runs.

INPUT   lessons/*.md, content/*.md and project/capstone READMEs; code/PATH files
PROCESS replace the body of each ```<lang> file=PATH block with code/PATH
OUTPUT  the Markdown files, rewritten in place; a list of the blocks updated

Usage:  python tools/sync_code.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
FENCE = re.compile(r"^```([^\n]*\bfile=(\"[^\"]+\"|\S+)[^\n]*)\n(.*?)^```\s*$", re.M | re.S)


def sync(path: Path) -> int:
    text = path.read_text()
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        target = CODE / m.group(2).strip('"')
        if not target.exists():
            return m.group(0)
        body = target.read_text().rstrip("\n") + "\n"
        if body != m.group(3):
            changed += 1
        return f"```{m.group(1)}\n{body}```"

    new = FENCE.sub(repl, text)
    if new != text:
        path.write_text(new)
    return changed


def main() -> None:
    files = sorted((ROOT / "lessons").glob("*.md")) + sorted((ROOT / "content").glob("*.md"))
    files += sorted((CODE / "projects").glob("*/README.md")) + sorted((CODE / "capstones").glob("*/README.md"))
    for f in files:
        n = sync(f)
        if n:
            print(f"{f.relative_to(ROOT)}: {n} block(s) updated")


if __name__ == "__main__":
    main()
