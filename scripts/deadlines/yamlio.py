"""Rewrite single venues in conferences.yml and leave every other byte alone.

The file is hand-written: a long header, section comments between venues, and
a consistent layout. A YAML round trip would lose all of that, so the file is
cut into one block per venue and only the blocks that changed are re-emitted.
"""
import json
import re

import yaml

_ORDER = ("name", "edition", "category", "rank", "location", "flag", "dates", "website", "note")
_ALWAYS_QUOTED = {"rank", "flag"}
_STAMP = re.compile(r"^#  Last automated update:.*$", re.M)


def _scalar(value, quote=False) -> str:
    if isinstance(value, bool) or value is None:
        raise ValueError("unexpected value %r" % (value,))
    if isinstance(value, int):
        return str(value)
    s = str(value)
    if not quote:
        try:
            if s == s.strip() and s and yaml.safe_load("k: " + s) == {"k": s}:
                return s
        except yaml.YAMLError:
            pass
    return json.dumps(s, ensure_ascii=False)


def render_entry(entry: dict) -> str:
    lines = ["- name: " + _scalar(entry["name"])]
    for key in _ORDER[1:]:
        if key in entry and entry[key] not in (None, ""):
            lines.append("  %s: %s" % (key, _scalar(entry[key], key in _ALWAYS_QUOTED)))
    lines.append("  timeline:")
    for stage in entry.get("timeline") or []:
        lines.append("    - label: " + _scalar(stage["label"]))
        lines.append("      date: " + str(stage["date"]))
        if stage.get("time"):
            lines.append("      time: " + _scalar(stage["time"], True))
        if stage.get("tz"):
            lines.append("      tz: " + _scalar(stage["tz"]))
    return "\n".join(lines) + "\n"


def _blocks(text: str):
    """(header, [[name, body, trailer], ...]): a venue's body runs from its
    `- name:` line to its last field; blank and comment lines after it, such
    as a section heading, are its trailer."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("- name:")]
    if not starts:
        return text, []
    header = "".join(lines[:starts[0]])
    blocks = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        cut = end
        while cut > start + 1 and (not lines[cut - 1].strip() or lines[cut - 1].lstrip().startswith("#")):
            cut -= 1
        name = yaml.safe_load(lines[start][2:])["name"]
        blocks.append([str(name), "".join(lines[start:cut]), "".join(lines[cut:end])])
    return header, blocks


def replace_entries(text: str, changed: dict) -> str:
    header, blocks = _blocks(text)
    out = [header]
    for name, body, trailer in blocks:
        out.append(render_entry(changed[name]) if name in changed else body)
        out.append(trailer)
    return "".join(out)


def stamp_header(text: str, today: str, count: int) -> str:
    line = "#  Last automated update: %s (%d venue%s changed)" % (today, count, "" if count == 1 else "s")
    return _STAMP.sub(line, text, count=1)
