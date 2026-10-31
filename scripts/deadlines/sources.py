"""Read the two community deadline lists into one shape: Edition and Stage."""
import re
from dataclasses import dataclass
from typing import Optional

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2}))?")

# The lists are third-party text, and /deadlines/ prints these fields as they
# are, some inside HTML attributes. So text keeps no markup, quote, brace or
# control characters, and a link must be a plain http(s) URL.
_UNSAFE = re.compile(r"[<>\"`{}\\\x00-\x1f\x7f]")
_TAG = re.compile(r"<[^>]*>")
_URL = re.compile(r"^https?://[^\s<>\"'`{}\\]+$", re.I)


def clean_text(value, limit: int = 120) -> str:
    s = _UNSAFE.sub(" ", _TAG.sub(" ", str(value or "")))
    return re.sub(r"\s+", " ", s).strip()[:limit].rstrip()


def clean_url(value) -> str:
    s = str(value or "").strip()
    return s if len(s) <= 300 and _URL.match(s) else ""


@dataclass(frozen=True)
class Stage:
    label: str
    date: str          # YYYY-MM-DD
    time: str = ""     # "HH:MM"; empty means the page default, 23:59
    tz: str = ""       # a zone /deadlines/ understands, or empty


@dataclass(frozen=True)
class Edition:
    source: str        # "ccf-deadlines" or "ai-deadlines"
    year: int
    link: str
    dates: str         # when the conference itself runs, free text
    place: str
    stages: tuple

    @property
    def paper(self) -> Optional[Stage]:
        """The main paper deadline: the first stage named Paper Submission."""
        for s in self.stages:
            if s.label.endswith("Paper Submission"):
                return s
        return None


# Zones the countdown on /deadlines/ reads (see the header of conferences.yml).
_TZ_ALIASES = {"aoe": "AoE", "utc-12": "AoE", "utc": "UTC", "utc+0": "UTC", "utc-0": "UTC", "gmt": "UTC",
               "pacific/honolulu": "UTC-10"}
_TZ_NAMED = {"PST", "PDT", "PT", "EST", "EDT", "ET", "CET", "CEST", "BST", "JST", "KST"}
_TZ_OFFSET = re.compile(r"^(?:utc|gmt)\s*([+-])0?(\d{1,2})(?::?(\d{2}))?$", re.I)


def norm_tz(raw) -> str:
    """Map a dataset's zone spelling onto the page's vocabulary; unknown -> ""."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.lower() in _TZ_ALIASES:
        return _TZ_ALIASES[s.lower()]
    if s.upper() in _TZ_NAMED:
        return s.upper()
    m = _TZ_OFFSET.match(s)
    if m:
        hours = int(m.group(2))
        if m.group(1) == "-" and hours == 12 and not m.group(3):
            return "AoE"
        if hours == 0 and not m.group(3):
            return "UTC"
        return "UTC%s%d%s" % (m.group(1), hours, ":" + m.group(3) if m.group(3) and m.group(3) != "00" else "")
    return ""


def split_dt(value):
    """'2026-11-16 23:59:59' -> ('2026-11-16', ''); '... 12:00:00' -> (..., '12:00'); TBD -> None."""
    m = _DATETIME.match(str(value or "").strip())
    if not m:
        return None
    hhmm = "%s:%s" % (m.group(2), m.group(3)) if m.group(2) else ""
    return m.group(1), "" if hhmm in ("", "23:59") else hhmm


def _sorted(stages) -> tuple:
    return tuple(sorted(stages, key=lambda s: (s.date, s.time or "23:59")))


# ---- ccf-deadlines (github.com/ccfddl/ccf-deadlines) ---------------------------
_CCF_KEYS = (("abstract_deadline", "Abstract Submission"), ("deadline", "Paper Submission"),
             ("rebuttal_deadline", "Rebuttal Ends"), ("decision_deadline", "Notification"))


def parse_ccf(doc) -> list:
    out = []
    for venue in doc or []:
        for conf in venue.get("confs") or []:
            tz = norm_tz(conf.get("timezone"))
            cycles = conf.get("timeline") or []
            stages = []
            for i, cycle in enumerate(cycles):
                prefix = ""
                if len(cycles) > 1:
                    comment = clean_text(cycle.get("comment"), 60)
                    prefix = (comment if comment and len(comment) <= 30 else "Round %d" % (i + 1)) + ": "
                for key, label in _CCF_KEYS:
                    dt = split_dt(cycle.get(key))
                    if dt:
                        stages.append(Stage(prefix + label, dt[0], dt[1], tz))
            out.append(Edition("ccf-deadlines", int(conf["year"]), clean_url(conf.get("link")),
                               clean_text(conf.get("date")), clean_text(conf.get("place")), _sorted(stages)))
    return out


# ---- ai-deadlines (github.com/huggingface/ai-deadlines) ------------------------
_HF_TYPES = {"abstract": "Abstract Submission", "paper": "Paper Submission", "submission": "Paper Submission",
             "supplementary": "Supplementary Material", "review_release": "Reviews Released",
             "rebuttal_end": "Rebuttal Ends", "notification": "Notification", "camera_ready": "Camera Ready"}
_HF_LEGACY = (("abstract_deadline", "Abstract Submission"), ("deadline", "Paper Submission"),
              ("review_release_date", "Reviews Released"), ("rebuttal_period_end", "Rebuttal Ends"),
              ("final_decision_date", "Notification"))


def parse_hf(doc) -> list:
    out = []
    for item in doc or []:
        listed = item.get("deadlines") or []
        has_paper = any(d.get("type") == "paper" for d in listed)
        stages = []
        for d in listed:
            kind = d.get("type")
            if kind == "submission" and has_paper:
                continue
            label, dt = _HF_TYPES.get(kind), split_dt(d.get("date"))
            if label and dt:
                stages.append(Stage(label, dt[0], dt[1], norm_tz(d.get("timezone") or item.get("timezone"))))
        if not listed:
            tz = norm_tz(item.get("timezone"))
            for key, label in _HF_LEGACY:
                dt = split_dt(item.get(key))
                if dt:
                    stages.append(Stage(label, dt[0], dt[1], tz))
        place = ", ".join(clean_text(p) for p in (item.get("city"), item.get("country")) if clean_text(p))
        out.append(Edition("ai-deadlines", int(item["year"]), clean_url(item.get("link")),
                           clean_text(item.get("date")), place, _sorted(stages)))
    return out
