"""Decide what, if anything, changes for one venue. Pure: no network, no files.

The rules keep the promise in the header of conferences.yml, that nothing on
the page asserts a date that has not been published:

  fill      the entry waits for its call (every stage "tba") and a list now
            carries dates for that edition -> take them.
  roll      every stage of the entry is in the past and a list carries the next
            edition with dates -> move to it.
  roll-tba  every stage is past and nothing newer is published -> the next
            edition, with a "tba" stage and a note on the cycle that closed.
  change    the edition is still running and a list gives a later paper
            deadline (an extension) -> applied only once the official site
            confirms it; the pipeline decides that. The entry's time zone is
            kept. A date that moved earlier, a different zone, or a venue with
            several rounds is only reported ("review"), never written.

Hand-written fields (category, rank) are never touched. Location, flag and
conference dates are kept when the edition stays the same.
"""
import copy
import datetime
import re
from dataclasses import dataclass
from typing import Optional

from .sources import ISO_DATE, Edition

COMMUNITY_NOTE = "Dates come from the {source} community list and are not yet confirmed on the official site."
_COMMUNITY_RE = re.compile(r"\s*Dates come from the [\w-]+ community list and are not yet confirmed on the official site\.")
# Notes that only say the call is pending stop being true once dates arrive.
_PENDING_RE = re.compile(r"not (yet )?(out|released|announced|posted|published)|\bTBD\b|to be announced", re.I)


@dataclass(frozen=True)
class Plan:
    kind: str                  # fill | roll | roll-tba | change | review (report only)
    entry: dict                # the venue as it should be written
    summary: str
    edition: Optional[Edition] = None   # where the dates came from
    agree: bool = False        # the other list gives the same paper deadline
    check: str = ""            # date to look for on the official site


# ---- places and flags --------------------------------------------------------
_COUNTRY_CODES = {
    "usa": "US", "united states": "US", "us": "US", "united states of america": "US", "canada": "CA", "mexico": "MX",
    "brazil": "BR", "chile": "CL", "argentina": "AR", "colombia": "CO", "peru": "PE", "uruguay": "UY",
    "uk": "GB", "united kingdom": "GB", "england": "GB", "scotland": "GB", "ireland": "IE", "france": "FR",
    "germany": "DE", "italy": "IT", "spain": "ES", "portugal": "PT", "netherlands": "NL", "the netherlands": "NL",
    "belgium": "BE", "switzerland": "CH", "austria": "AT", "sweden": "SE", "norway": "NO", "denmark": "DK",
    "finland": "FI", "iceland": "IS", "poland": "PL", "czech republic": "CZ", "czechia": "CZ", "hungary": "HU",
    "greece": "GR", "croatia": "HR", "slovenia": "SI", "romania": "RO", "bulgaria": "BG", "serbia": "RS",
    "estonia": "EE", "latvia": "LV", "lithuania": "LT", "luxembourg": "LU", "malta": "MT", "cyprus": "CY",
    "turkey": "TR", "türkiye": "TR", "israel": "IL", "uae": "AE", "united arab emirates": "AE", "qatar": "QA",
    "saudi arabia": "SA", "egypt": "EG", "morocco": "MA", "south africa": "ZA", "kenya": "KE", "rwanda": "RW",
    "nigeria": "NG", "india": "IN", "china": "CN", "hong kong": "HK", "taiwan": "TW", "japan": "JP",
    "south korea": "KR", "korea": "KR", "republic of korea": "KR", "singapore": "SG", "malaysia": "MY",
    "thailand": "TH", "vietnam": "VN", "indonesia": "ID", "philippines": "PH", "australia": "AU",
    "new zealand": "NZ",
}
_SHORT_COUNTRY = {"united states": "USA", "united states of america": "USA", "united kingdom": "UK"}
_US_STATE = re.compile(r"^[A-Z]{2}$")


def clean_place(place: str) -> str:
    """'Seattle, WA, United States (Hybrid)' -> 'Seattle, WA, USA'."""
    text = re.sub(r"\s*\([^)]*\)", "", str(place or "")).strip(" ,")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if parts:
        parts[-1] = _SHORT_COUNTRY.get(parts[-1].lower(), parts[-1])
    return ", ".join(parts)


def flag_for(place: str) -> str:
    parts = [p.strip() for p in str(place or "").split(",") if p.strip()]
    if not parts:
        return ""
    code = _COUNTRY_CODES.get(parts[-1].lower())
    if not code and _US_STATE.match(parts[-1]):
        code = "US"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code) if code else ""


# ---- helpers ------------------------------------------------------------------
def _dates(timeline) -> list:
    return [str(s.get("date")) for s in timeline or [] if ISO_DATE.match(str(s.get("date")))]


def _paper_index(timeline) -> int:
    for i, s in enumerate(timeline or []):
        if str(s.get("label", "")).endswith("Paper Submission") and ISO_DATE.match(str(s.get("date"))):
            return i
    return -1


def _stage_dict(stage) -> dict:
    out = {"label": stage.label, "date": stage.date}
    if stage.time:
        out["time"] = stage.time
    if stage.tz:
        out["tz"] = stage.tz
    return out


def _human(ymd: str) -> str:
    d = datetime.date.fromisoformat(ymd)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year)


def _best(editions, year):
    """The edition with dates for `year`, ccf-deadlines first; and whether the
    other list gives the same paper deadline."""
    found = [e for e in editions if e.year == year and e.paper]
    if not found:
        return None, False
    best = found[0]  # ccf-deadlines comes first in `editions`
    agree = any(e is not best and e.paper and best.paper and e.paper.date == best.paper.date for e in found)
    return best, agree


def _from_edition(entry, ed, same_edition) -> dict:
    new = copy.deepcopy(entry)
    new["edition"] = ed.year
    place = clean_place(ed.place)
    if not same_edition or str(entry.get("location", "TBA")).upper() == "TBA":
        new.pop("flag", None)
        new["location"] = place or "TBA"
        if flag_for(place):
            new["flag"] = flag_for(place)
    if (not same_edition or not entry.get("dates")) and ed.dates:
        new["dates"] = ed.dates
    elif not same_edition:
        new.pop("dates", None)
    # A waiting entry often still links last year's site (".../KR2026/"); the
    # list's link is for the edition itself.
    website = str(entry.get("website") or "")
    stale = any(y != str(ed.year) for y in re.findall(r"20\d\d", website))
    if ed.link and (not same_edition or not website or stale):
        new["website"] = ed.link
    note = str(entry.get("note") or "")
    if not same_edition or _PENDING_RE.search(note):
        new.pop("note", None)
    new["timeline"] = [_stage_dict(s) for s in ed.stages]
    return new


# ---- the decision -----------------------------------------------------------------
def plan_venue(entry: dict, editions: list, today: str, step: int = 1) -> Optional[Plan]:
    name, year = entry["name"], int(entry["edition"])
    timeline = entry.get("timeline") or []
    dates = _dates(timeline)

    if not dates:  # waiting for the call
        ed, agree = _best(editions, year)
        if not ed:
            return None
        return Plan("fill", _from_edition(entry, ed, True), "%s %d dates published" % (name, year), ed, agree,
                    ed.paper.date)

    if max(dates) < today:  # every stage is behind us
        later = sorted({e.year for e in editions if e.year > year and e.paper})
        if later:
            ed, agree = _best(editions, later[0])
            return Plan("roll", _from_edition(entry, ed, False), "%s moved on to %d" % (name, ed.year), ed, agree,
                        ed.paper.date)
        listed = sorted((e for e in editions if e.year > year), key=lambda e: e.year)
        target = listed[0].year if listed else year + step
        link = listed[0].link if listed and listed[0].link else entry.get("website", "")
        closed = timeline[_paper_index(timeline)]["date"] if _paper_index(timeline) >= 0 else min(dates)
        new = {k: copy.deepcopy(v) for k, v in entry.items() if k in ("name", "category", "rank")}
        new.update({"edition": target, "location": "TBA"})
        if link:
            new["website"] = link
        new["note"] = "%s %d closed %s. The %d call is not out yet." % (name, year, _human(str(closed)), target)
        new["timeline"] = [{"label": "Paper Submission", "date": "tba"}]
        return Plan("roll-tba", new, "%s %d closed; %d not announced" % (name, year, target))

    # The edition is still running: look for a moved paper deadline.
    ed, agree = _best(editions, year)
    i = _paper_index(timeline)
    if not ed or i < 0 or ed.paper.date == str(timeline[i]["date"]) or ed.paper.date < today:
        return None
    ours = timeline[i]
    summary = "%s %d paper deadline %s -> %s" % (name, year, ours["date"], ed.paper.date)
    rounds = sum(1 for s in ed.stages if s.label.endswith("Paper Submission"))
    rounds = max(rounds, sum(1 for s in timeline if str(s.get("label", "")).endswith("Paper Submission")))
    if rounds > 1:
        return Plan("review", entry, summary + "; several rounds, so not matched automatically", ed, agree)
    if ed.paper.date < str(ours["date"]):
        return Plan("review", entry, summary + "; earlier than the entry, which is more likely a stale list", ed, agree)
    if ed.paper.tz and ours.get("tz") and ed.paper.tz != ours.get("tz"):
        return Plan("review", entry, summary + "; zone %s vs %s" % (ed.paper.tz, ours.get("tz")), ed, agree)
    new = copy.deepcopy(entry)
    new["timeline"][i] = dict(ours, date=ed.paper.date)  # label, time and zone stay as written
    return Plan("change", new, summary, ed, agree, ed.paper.date)


def unconfirmed(entry: dict, source: str, mark: bool) -> dict:
    """Add or remove the note saying the dates are not yet on the official site."""
    new = copy.deepcopy(entry)
    note = _COMMUNITY_RE.sub("", str(new.get("note") or "")).strip()
    if mark:
        note = (note + " " if note else "") + COMMUNITY_NOTE.format(source=source)
    if note:
        new["note"] = note
    else:
        new.pop("note", None)
    return new


def is_unconfirmed(entry: dict) -> bool:
    return bool(_COMMUNITY_RE.search(" " + str(entry.get("note") or "")))
