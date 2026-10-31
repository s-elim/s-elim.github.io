"""Check a date against the conference's own web page."""
import datetime
import re
from typing import Optional

_ORDINAL = re.compile(r"(\d)(st|nd|rd|th)\b")
_MONTH_ABBR = {9: ["sep", "sept"]}
# Confirmation wants the date close after words like these, so a matching
# notification or workshop date elsewhere on the page does not count.
DEADLINE_WORDS = ("paper", "submission", "submit", "deadline", "due")
_WINDOW = 160


def _normalise(text: str) -> str:
    text = _ORDINAL.sub(r"\1", text.lower())
    text = re.sub(r"[,.]", " ", text)
    return re.sub(r"\s+", " ", text)


def _patterns(ymd: str) -> list:
    d = datetime.date.fromisoformat(ymd)
    full = d.strftime("%B").lower()
    abbrs = _MONTH_ABBR.get(d.month, [d.strftime("%b").lower()])
    day, month, year = d.day, d.month, d.year
    out = [ymd, "%d/%02d/%02d" % (year, month, day)]
    for m in [full] + abbrs:
        out += ["%s %d" % (m, day), "%d %s" % (day, m)]
    if day > 12:  # 03/04/2027 could be either order; 16/11/2026 cannot
        for dd in {str(day), "%02d" % day}:
            for mm in {str(month), "%02d" % month}:
                out += ["%s/%s/%d" % (mm, dd, year), "%s/%s/%d" % (dd, mm, year)]
    return out


def page_mentions(text: str, ymd: str, near=()) -> bool:
    """Does the page write this date in any usual way ("November 16, 2026",
    "16 Nov", "2026-11-16", "11/16/2026", ...)? Year-less forms count, since
    call-for-papers pages often leave the year out. With `near`, one of those
    words must come shortly before the date."""
    body = _normalise(text)
    for p in _patterns(ymd):
        for m in re.finditer(r"(?<![\w/-])" + re.escape(p) + r"(?![\w/-])", body):
            before = body[max(0, m.start() - _WINDOW):m.start()]
            if not near or any(w in before for w in near):
                return True
    return False


def fetch_text(client, url: str) -> Optional[str]:
    """The page's visible text, or None when it cannot be read."""
    if not url.startswith(("http://", "https://")):
        return None
    try:
        r = client.get(url)
        if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
            return None
    except Exception as exc:  # network errors, TLS, timeouts: treat as unconfirmed
        print("    could not read %s: %s" % (url, exc.__class__.__name__))
        return None
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ")


def confirmed(client, url: str, ymd: str) -> bool:
    text = fetch_text(client, url)
    return bool(text) and page_mentions(text, ymd, DEADLINE_WORDS)
