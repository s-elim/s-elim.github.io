"""Monthly refresh of _data/conferences.yml. merge.py holds the rules."""
import datetime
import os

import httpx
import yaml

from .config import BIENNIAL, CCF_RAW, CONFERENCES_YML, HF_RAW, SOURCES, USER_AGENT
from .confirm import confirmed
from .merge import is_unconfirmed, plan_venue, unconfirmed
from .sources import ISO_DATE, parse_ccf, parse_hf
from .yamlio import replace_entries, stamp_header


def _fetch(client, url, parse, tries: int = 2):
    """Editions from one list file, or ([], reason) when it cannot be used."""
    reason = ""
    for _ in range(tries):
        try:
            r = client.get(url)
            if r.status_code == 200:
                return parse(yaml.safe_load(r.text)), ""
            reason = "%s answered %d" % (url, r.status_code)
            if r.status_code == 404:
                break  # a moved file does not come back on a retry
        except httpx.HTTPError as exc:
            reason = "%s: %s" % (url, exc.__class__.__name__)
        except (yaml.YAMLError, KeyError, ValueError, TypeError) as exc:
            return [], "%s could not be read: %s" % (url, exc.__class__.__name__)
    return [], reason


def _editions(client, name):
    """ccf-deadlines first: merge.py prefers the first list that has dates."""
    ccf, hf = SOURCES[name]
    found, errors = [], []
    for path, base, parse in ((ccf, CCF_RAW, parse_ccf), (hf and hf + ".yml", HF_RAW, parse_hf)):
        if path:
            eds, err = _fetch(client, base + path, parse)
            found += eds
            if err:
                errors.append(err)
    return found, errors


def _paper_date(entry) -> str:
    for stage in entry.get("timeline") or []:
        if str(stage.get("label", "")).endswith("Paper Submission") and ISO_DATE.match(str(stage.get("date"))):
            return str(stage["date"])
    return ""


def _plan_one(client, entry, today, changed, rows, failures):
    name = entry["name"]
    if SOURCES.get(name, (None, None)) == (None, None):
        rows.append((name, "manual", "in neither community list"))
        return
    eds, errors = _editions(client, name)
    failures += errors
    if not eds:
        rows.append((name, "skipped", "; ".join(errors) or "no editions listed"))
        return
    plan = plan_venue(entry, eds, today, BIENNIAL.get(name, 1))
    if plan and errors and plan.kind in ("roll", "roll-tba"):
        # The unreadable list may carry the next edition; wait for a full read.
        rows.append((name, "skipped", plan.summary + "; not applied because " + "; ".join(errors)))
        return
    if plan and plan.kind == "review":
        rows.append((name, "needs a look", plan.summary))
        return
    if plan is None:
        # Filled from a list in an earlier month: does the official site show it now?
        paper = _paper_date(entry)
        if is_unconfirmed(entry) and paper and confirmed(client, str(entry.get("website") or ""), paper):
            changed[name] = unconfirmed(entry, "", False)
            rows.append((name, "confirmed", "the official site now shows %s" % paper))
        return
    if plan.kind == "roll-tba":
        changed[name] = plan.entry
        rows.append((name, plan.kind, plan.summary))
        return
    ok = confirmed(client, plan.edition.link or str(plan.entry.get("website") or ""), plan.check)
    if plan.kind == "change":
        if ok:
            changed[name] = plan.entry
            rows.append((name, "change", plan.summary + " (confirmed on the official site)"))
        else:
            rows.append((name, "needs a look", plan.summary + "; not on the official site, so left as it was"))
        return
    changed[name] = unconfirmed(plan.entry, plan.edition.source, not ok)
    how = "confirmed on the official site" if ok else "from %s%s; not yet on the official site" % (
        plan.edition.source, ", both lists agree" if plan.agree else "")
    rows.append((name, plan.kind, "%s (%s)" % (plan.summary, how)))


def _report(rows, today, dry_run, count):
    title = "Conference deadlines sync, %s%s: %d venue%s changed" % (
        today, " (dry run)" if dry_run else "", count, "" if count == 1 else "s")
    print("=== " + title + " ===")
    for name, kind, detail in rows:
        print("  %-14s %-13s %s" % (name, kind, detail))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### %s\n\n| Venue | Result | Detail |\n|---|---|---|\n" % title)
            for name, kind, detail in rows:
                f.write("| %s | %s | %s |\n" % (name, kind, detail.replace("|", "\\|")))
            f.write("\nVenues not listed had nothing new.\n")


def _check(before, after, changed):
    """Never write a file that lost a venue or changed one nobody planned."""
    if [e["name"] for e in after] != [e["name"] for e in before]:
        raise SystemExit("Refusing to write: the venue list changed shape.")
    for old, new in zip(before, after):
        if old["name"] not in changed and old != new:
            raise SystemExit("Refusing to write: %s changed without a plan." % old["name"])


def run_deadlines(dry_run: bool = False, today: str = "") -> int:
    today = today or datetime.date.today().isoformat()
    text = CONFERENCES_YML.read_text(encoding="utf-8")
    entries = yaml.safe_load(text)
    changed, rows, failures = {}, [], []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for entry in entries:
            _plan_one(client, entry, today, changed, rows, failures)
    _report(rows, today, dry_run, len(changed))
    for reason in failures:  # shown as warnings on the workflow run's page
        print("::warning title=Deadline list unreadable::%s" % reason)
    reads = sum(1 for e in entries for path in SOURCES.get(e["name"], (None, None)) if path)
    if reads and len(failures) >= reads:
        raise SystemExit("Neither community list could be read; nothing was changed.")
    if changed and not dry_run:
        new_text = stamp_header(replace_entries(text, changed), today, len(changed))
        _check(entries, yaml.safe_load(new_text), changed)
        with open(CONFERENCES_YML, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        print("Wrote %s" % CONFERENCES_YML)
    return len(changed)
