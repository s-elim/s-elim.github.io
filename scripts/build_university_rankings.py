#!/usr/bin/env python3
"""Regenerate _data/university_rankings.yml from the official THE and QS feeds.

Both rankings are pulled from the JSON that the publishers' own ranking tables
load, so the rows match what a visitor sees on their sites.

    THE : https://www.timeshighereducation.com/json/ranking_tables/world_university_rankings/<year>
    QS  : the qs-rankings-data/*.txt file referenced by the QS rankings page
          (www.topuniversities.com is Cloudflare-gated; QS's own .cn domain
          serves the identical data file without a challenge)

Usage:
    python3 scripts/build_university_rankings.py                  # fetch live
    python3 scripts/build_university_rankings.py --the a.json --qs b.json

When a new edition is published, bump THE_YEAR / QS_YEAR and the EDITIONS
metadata below, then re-run and commit the regenerated YAML.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

TOP_N = 400
THE_YEAR = "2026"
QS_YEAR = "2027"

THE_JSON = (
    "https://www.timeshighereducation.com/json/ranking_tables/"
    f"world_university_rankings/{THE_YEAR}"
)
QS_PAGE = (
    "https://www.qs-topuniversities.cn/en/university-rankings/"
    f"world-university-rankings/{QS_YEAR}"
)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

OUT = Path(__file__).resolve().parent.parent / "_data" / "university_rankings.yml"

EDITIONS = {
    "the": {
        "name": "Times Higher Education World University Rankings",
        "short": "THE",
        "edition": THE_YEAR,
        "published": "October 2025",
        "total_ranked": "2,191 institutions from 115 countries and territories",
        "url": "https://www.timeshighereducation.com/world-university-rankings/"
               f"{THE_YEAR}/world-ranking",
        "note": "THE publishes individual positions to 200, then equal bands "
                "(201-250, 251-300, 301-350, 351-400).",
    },
    "qs": {
        "name": "QS World University Rankings",
        "short": "QS",
        "edition": QS_YEAR,
        "published": "18 June 2026",
        "total_ranked": "1,504 universities from 106 countries and territories",
        "url": "https://www.topuniversities.com/world-university-rankings",
        "note": 'QS publishes individual positions to 700; "=" marks a shared rank.',
    },
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def clean(name):
    """QS ships names wrapped in anchor markup; THE ships them plain."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", name))).strip()


def low(rank):
    """Numeric part of a rank string ('=73' -> 73, '351-400' -> 351)."""
    return int(re.match(r"^=?(\d+)", rank).group(1))


def mark_ties(rows):
    """Both feeds drop the '=' marker on one member of some tie groups (THE lists
    City University of Hong Kong as '73' between two '=73' entries). Recompute the
    marker from the data so every shared position is flagged consistently."""
    counts = Counter(low(r["rank"]) for r in rows if "-" not in r["rank"])
    for r in rows:
        if "-" in r["rank"]:
            continue
        n = low(r["rank"])
        r["rank"] = ("=" if counts[n] > 1 else "") + str(n)


def load_the(raw):
    rows = []
    for r in json.loads(raw)["data"]:
        # The feed is already in rank order; stop at the first band past 400.
        if r["rank"].startswith("401"):
            break
        rows.append({
            "rank": r["rank"].replace("–", "-"),
            "name": clean(r["name"]),
            "country": r["location"].strip(),
        })
    mark_ties(rows)
    return rows


def load_qs(raw):
    entries = json.loads(raw)["data"]
    # QS's feed does not store tie groups in display order (it lists Stanford
    # before Imperial at =2, the site shows the reverse), so order ties
    # alphabetically to match the published table.
    entries.sort(key=lambda r: (low(r["rank_display"]), clean(r["title"]).lower()))
    rows = [{
        "rank": r["rank_display"].strip(),
        "name": clean(r["title"]),
        "country": (r.get("country") or "").strip(),
    } for r in entries[:TOP_N]]
    mark_ties(rows)
    return rows


def match_key(name):
    """Normalise a university name enough to pair THE and QS spellings.

    THE says "Massachusetts Institute of Technology", QS says the same plus
    "(MIT)"; dropping parentheticals, stop words and punctuation lines them up.
    """
    n = re.sub(r"\([^)]*\)", " ", name.lower())
    n = re.sub(r"\b(the|university|universities|univ|of|and|for|at)\b", " ", n)
    return re.sub(r"[^a-z0-9]", "", n)


# The two publishers spell some countries differently; these are the same place.
COUNTRY_ALIASES = [
    {"China", "China (Mainland)"},
    {"Hong Kong", "Hong Kong SAR"},
    {"Macao", "Macau SAR", "Macau"},
    {"Russia", "Russian Federation"},
    {"Turkey", "Türkiye"},
    {"Iran", "Iran, Islamic Republic of"},
    {"Brunei", "Brunei Darussalam"},
    {"Ireland", "Republic of Ireland"},
]


def same_country(a, b):
    if a == b:
        return True
    return any(a in group and b in group for group in COUNTRY_ALIASES)


def add_cross_ranks(the_rows, qs_rows):
    """Annotate each row with the other table's position for the same institution.

    Two gates keep this honest. A normalised name must be unique within both
    tables, and the countries must agree: without the country check THE's
    "University of Newcastle" (Australia) pairs with QS's "Newcastle University"
    (United Kingdom), which are different institutions. A blank means "no
    confident match", never "absent from the other ranking".
    """
    def unique_index(rows):
        idx = {}
        for r in rows:
            idx.setdefault(match_key(r["name"]), []).append(r)
        return {k: v[0] for k, v in idx.items() if len(v) == 1}

    the_idx, qs_idx = unique_index(the_rows), unique_index(qs_rows)
    matched = 0
    for rows, own, other in ((the_rows, the_idx, qs_idx), (qs_rows, qs_idx, the_idx)):
        for r in rows:
            k = match_key(r["name"])
            # The name must be unambiguous on both sides, otherwise the pair is
            # only resolvable in one direction and the two tables disagree.
            hit = other.get(k) if k in own else None
            if hit and not same_country(r["country"], hit["country"]):
                hit = None
            r["cross"] = hit["rank"] if hit else ""
            if hit:
                matched += 1
    return matched // 2


def qs_data_url():
    page = get(QS_PAGE)
    urls = [u.replace("\\/", "/")
            for u in re.findall(r"[^\"' ]*qs-rankings-data[^\"' ]*?\.txt", page)]
    # The page also references an "_indicators" table; we want the rankings one.
    main = [u for u in urls if "_indicators" not in u]
    if not main:
        raise SystemExit("Could not find the QS data file URL on " + QS_PAGE)
    return main[0]


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--the", help="local THE JSON instead of fetching")
    ap.add_argument("--qs", help="local QS JSON instead of fetching")
    args = ap.parse_args()

    the_rows = load_the(
        Path(args.the).read_text("utf-8") if args.the else get(THE_JSON))
    qs_rows = load_qs(
        Path(args.qs).read_text("utf-8") if args.qs else get(qs_data_url()))

    pairs = add_cross_ranks(the_rows, qs_rows)
    print("cross-linked %d institutions across both tables" % pairs)

    for label, rows in (("THE", the_rows), ("QS", qs_rows)):
        if len(rows) != TOP_N:
            raise SystemExit("%s: expected %d rows, got %d" % (label, TOP_N, len(rows)))
        ranks = [low(r["rank"]) for r in rows]
        if ranks != sorted(ranks):
            raise SystemExit(label + ": rows are not in rank order")

    lines = [
        "# Top 400 world university rankings, rendered by the Rankings modal on the homepage.",
        "# Generated by scripts/build_university_rankings.py - do not hand-edit rows.",
        "#",
        "#   THE %s : %s" % (THE_YEAR, EDITIONS["the"]["url"]),
        "#   QS  %s : %s" % (QS_YEAR, EDITIONS["qs"]["url"]),
        "",
    ]
    for key, rows in (("the", the_rows), ("qs", qs_rows)):
        lines.append("%s:" % key)
        for mk, mv in EDITIONS[key].items():
            lines.append("  %s: %s" % (mk, yq(mv)))
        lines.append("  count: %d" % len(rows))
        lines.append("  entries:")
        lines += [
            "    - { rank: %s, name: %s, country: %s, cross: %s }"
            % (yq(r["rank"]), yq(r["name"]), yq(r["country"]), yq(r.get("cross", "")))
            for r in rows
        ]
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote %s" % OUT)
    print("  THE %s: %d rows, %s -> %s"
          % (THE_YEAR, len(the_rows), the_rows[0]["name"], the_rows[-1]["rank"]))
    print("  QS  %s: %d rows, %s -> %s"
          % (QS_YEAR, len(qs_rows), qs_rows[0]["name"], qs_rows[-1]["rank"]))


if __name__ == "__main__":
    main()
