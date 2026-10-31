import sys
from pathlib import Path

import yaml

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from deadlines.config import CONFERENCES_YML, SOURCES
from deadlines.confirm import page_mentions
from deadlines.merge import COMMUNITY_NOTE, plan_venue, unconfirmed
from deadlines.sources import Edition, Stage, norm_tz, parse_ccf, parse_hf
from deadlines.yamlio import render_entry, replace_entries, stamp_header

CCF_DOC = [{
    "title": "WACV",
    "confs": [
        {"year": 2026, "link": "https://wacv2026.thecvf.com/", "timezone": "UTC-12", "date": "Mar 6-10, 2026",
         "place": "Tucson, Arizona, USA", "timeline": [{"deadline": "2025-07-11 23:59:59"}]},
        {"year": 2027, "link": "https://wacv.thecvf.com/", "timezone": "AoE", "date": "Jan 4 - 8, 2027",
         "place": "Buena Vista, FL, United States (Hybrid)",
         "timeline": [
             {"abstract_deadline": "2026-06-19 23:59:59", "deadline": "2026-06-26 23:59:59", "comment": "First round"},
             {"deadline": "2026-08-28 12:00:00", "decision_deadline": "2026-10-09 23:59:59", "comment": "Second round"},
         ]},
    ],
}]

HF_DOC = [{
    "title": "NeurIPS", "year": 2027, "link": "https://neurips.cc/", "date": "December 5-11, 2027",
    "city": "Lisbon", "country": "Portugal",
    "deadlines": [
        {"type": "abstract", "date": "2027-05-04 23:59:59", "timezone": "AoE"},
        {"type": "paper", "date": "2027-05-11 23:59:59", "timezone": "AoE"},
        {"type": "submission", "date": "2027-05-11 23:59:59", "timezone": "AoE"},
        {"type": "rebuttal_start", "date": "2027-07-27 00:00:00", "timezone": "AoE"},
        {"type": "notification", "date": "2027-09-24 23:59:59", "timezone": "UTC-08"},
    ],
}]


def edition(year, paper, source="ccf-deadlines", link="https://example.org/", place="Lisbon, Portugal", extra=()):
    stages = tuple(extra) + ((Stage("Paper Submission", paper, "", "AoE"),) if paper else ())
    return Edition(source, year, link, "May 1-5, %d" % year, place, stages)


# ---- reading the community datasets --------------------------------------------

def test_norm_tz_maps_the_dataset_spellings_onto_the_page_vocabulary():
    assert [norm_tz(t) for t in ["UTC-12", "AoE", "UTC+0", "UTC", "UTC-08", "GMT+02", "PT", "Pacific/Honolulu", "Europe/London", None]] == \
        ["AoE", "AoE", "UTC", "UTC", "UTC-8", "UTC+2", "PT", "UTC-10", "", ""]


def test_parse_ccf_reads_rounds_times_and_zones():
    eds = parse_ccf(CCF_DOC)
    assert [e.year for e in eds] == [2026, 2027]
    wacv = eds[1]
    assert [(s.label, s.date, s.time, s.tz) for s in wacv.stages] == [
        ("First round: Abstract Submission", "2026-06-19", "", "AoE"),
        ("First round: Paper Submission", "2026-06-26", "", "AoE"),
        ("Second round: Paper Submission", "2026-08-28", "12:00", "AoE"),
        ("Second round: Notification", "2026-10-09", "", "AoE"),
    ]
    assert wacv.paper.date == "2026-06-26"


def test_parse_hf_keeps_known_stages_and_prefers_paper_over_submission():
    ed = parse_hf(HF_DOC)[0]
    assert [(s.label, s.date, s.tz) for s in ed.stages] == [
        ("Abstract Submission", "2027-05-04", "AoE"),
        ("Paper Submission", "2027-05-11", "AoE"),
        ("Notification", "2027-09-24", "UTC-8"),
    ]
    assert ed.place == "Lisbon, Portugal"


def test_text_from_the_lists_cannot_carry_markup_or_odd_links():
    doc = [{"title": "X", "confs": [{
        "year": 2027, "timezone": "AoE", "link": "javascript:alert(1)",
        "date": 'May 1-5, 2027 <img src=x onerror=alert(1)> {{ site.data }}',
        "place": 'Xi\'an, "China"\n<script>', "timeline": [
            {"deadline": "2027-01-10 23:59:59", "comment": "<b>Round</b> {% raw %}"},
            {"deadline": "2027-02-10 23:59:59", "comment": "Two"}]}]}]
    ed = parse_ccf(doc)[0]
    assert ed.link == ""
    for text in [ed.dates, ed.place] + [s.label for s in ed.stages]:
        assert not set(text) & set('<>"{}\n'), text
    assert ed.place == "Xi'an, China"
    assert parse_ccf([{"confs": [dict(doc[0]["confs"][0], link="https://ok.org/cfp?a=1")]}])[0].link == "https://ok.org/cfp?a=1"


def test_every_tracked_venue_has_a_source_entry():
    names = [c["name"] for c in yaml.safe_load(CONFERENCES_YML.read_text(encoding="utf-8"))]
    assert sorted(names) == sorted(SOURCES)


# ---- planning a change -----------------------------------------------------------

TBA = {"name": "NeurIPS", "edition": 2027, "category": "aiml", "rank": "A*", "location": "TBA",
       "website": "https://neurips.cc/", "note": "The 2027 call is not out yet.",
       "timeline": [{"label": "Paper Submission", "date": "tba"}]}


def test_a_tba_entry_is_filled_from_the_same_edition():
    plan = plan_venue(TBA, [edition(2027, "2027-05-11")], "2026-11-01")
    assert plan.kind == "fill"
    assert plan.entry["timeline"] == [{"label": "Paper Submission", "date": "2027-05-11", "tz": "AoE"}]
    assert plan.entry["location"] == "Lisbon, Portugal"
    assert plan.entry["flag"] == "🇵🇹"
    assert "note" not in plan.entry, "the 'not out yet' note no longer applies"
    assert plan.entry["rank"] == "A*" and plan.entry["category"] == "aiml"


def test_a_fill_replaces_a_link_to_last_years_site_but_keeps_a_current_one():
    old_site = dict(TBA, website="https://kr.org/KR2026/")
    assert plan_venue(old_site, [edition(2027, "2027-05-11", link="https://kr.org/KR2027/")], "2026-11-01").entry["website"] == \
        "https://kr.org/KR2027/"
    this_year = dict(TBA, website="https://ieee-cas.org/2027-icme")
    assert plan_venue(this_year, [edition(2027, "2027-05-11")], "2026-11-01").entry["website"] == "https://ieee-cas.org/2027-icme"


def test_a_tba_entry_without_published_dates_is_left_alone():
    assert plan_venue(TBA, [edition(2027, None)], "2026-11-01") is None


def test_a_closed_edition_rolls_to_the_next_one_with_dates():
    old = dict(TBA, edition=2026, location="Sydney, Australia",
               timeline=[{"label": "Paper Submission", "date": "2026-05-06"}])
    plan = plan_venue(old, [edition(2026, "2026-05-06"), edition(2027, "2027-05-11")], "2026-11-01")
    assert plan.kind == "roll"
    assert plan.entry["edition"] == 2027
    assert plan.entry["timeline"][0]["date"] == "2027-05-11"


def test_a_closed_edition_with_nothing_announced_becomes_tba_with_a_note():
    old = {"name": "ECCV", "edition": 2026, "category": "vision", "rank": "A*", "location": "Malmö, Sweden",
           "flag": "🇸🇪", "dates": "Sep 8-13, 2026", "website": "https://eccv.ecva.net/",
           "timeline": [{"label": "Paper Submission", "date": "2026-03-05"}]}
    plan = plan_venue(old, [edition(2026, "2026-03-05")], "2026-11-01", step=2)
    assert plan.kind == "roll-tba"
    assert plan.entry["edition"] == 2028
    assert plan.entry["location"] == "TBA" and "flag" not in plan.entry and "dates" not in plan.entry
    assert plan.entry["note"] == "ECCV 2026 closed 5 Mar 2026. The 2028 call is not out yet."
    assert plan.entry["timeline"] == [{"label": "Paper Submission", "date": "tba"}]


def test_a_running_edition_keeps_its_dates_but_reports_a_moved_deadline():
    cur = dict(TBA, timeline=[{"label": "Paper Submission", "date": "2027-05-11"},
                              {"label": "Notification", "date": "2027-09-24"}])
    assert plan_venue(cur, [edition(2027, "2027-05-11")], "2026-11-01") is None
    plan = plan_venue(cur, [edition(2027, "2027-05-18")], "2026-11-01")
    assert plan.kind == "change"
    assert plan.check == "2027-05-18"
    assert [s["date"] for s in plan.entry["timeline"]] == ["2027-05-18", "2027-09-24"], "only the paper date moves"


def test_a_moved_deadline_keeps_the_entrys_own_time_zone():
    cur = dict(TBA, timeline=[{"label": "Paper Submission", "date": "2027-05-11", "time": "12:00", "tz": "AoE"}])
    plan = plan_venue(cur, [edition(2027, None, extra=[Stage("Paper Submission", "2027-05-18")])], "2026-11-01")
    assert plan.entry["timeline"][0] == {"label": "Paper Submission", "date": "2027-05-18", "time": "12:00", "tz": "AoE"}


def test_doubtful_moves_are_only_reported():
    cur = dict(TBA, timeline=[{"label": "Paper Submission", "date": "2027-05-11", "tz": "AoE"}])
    assert plan_venue(cur, [edition(2027, "2027-05-04")], "2026-11-01").kind == "review", "earlier: a stale list"
    pst = edition(2027, None, extra=[Stage("Paper Submission", "2027-05-18", "", "PST")])
    assert plan_venue(cur, [pst], "2026-11-01").kind == "review", "a different zone"
    rounds = edition(2027, None, extra=[Stage("Round 1: Paper Submission", "2027-05-18", "", "AoE"),
                                        Stage("Round 2: Paper Submission", "2027-08-18", "", "AoE")])
    assert plan_venue(cur, [rounds], "2026-11-01").kind == "review", "several rounds"


def test_an_edition_without_a_paper_deadline_is_not_used():
    placeholder = edition(2027, None, extra=[Stage("Notification", "2027-08-01")])
    assert plan_venue(TBA, [placeholder], "2026-11-01") is None


def test_ccf_wins_over_hf_and_agreement_is_recorded():
    eds = [edition(2027, "2027-05-11"), edition(2027, "2027-05-11", source="ai-deadlines")]
    assert plan_venue(TBA, eds, "2026-11-01").agree is True
    eds = [edition(2027, None), edition(2027, "2027-05-12", source="ai-deadlines")]
    plan = plan_venue(TBA, eds, "2026-11-01")
    assert plan.edition.source == "ai-deadlines" and plan.agree is False


def test_unconfirmed_marks_and_clears_the_community_note():
    entry = dict(TBA, note="Two sites.")
    marked = unconfirmed(entry, "ccf-deadlines", True)
    assert marked["note"] == "Two sites. " + COMMUNITY_NOTE.format(source="ccf-deadlines")
    assert unconfirmed(marked, "ccf-deadlines", False)["note"] == "Two sites."
    assert "note" not in unconfirmed(dict(TBA, note=COMMUNITY_NOTE.format(source="x")), "x", False)


# ---- checking the official page -------------------------------------------------

def test_page_mentions_finds_a_date_written_the_usual_ways():
    for text in ["Paper submission: November 16, 2026 (AoE)", "Deadline Nov. 16th, 2026", "16 November 2026",
                 "due 2026-11-16 23:59", "Submission: Mon, Nov 16"]:
        assert page_mentions(text, "2026-11-16"), text
    assert not page_mentions("Paper submission: November 6, 2026", "2026-11-16")
    assert not page_mentions("Nov 160 attendees", "2026-11-16")
    assert not page_mentions("Workshop on 03/04/2027", "2027-04-03"), "day and month could be swapped"


def test_confirmation_wants_the_date_near_deadline_words():
    words = ("paper", "submission", "deadline")
    assert page_mentions("Paper submission deadline: November 16, 2026", "2026-11-16", words)
    assert not page_mentions("Author notification: November 16, 2026", "2026-11-16", words)
    far = "Paper submission. " + "Lots of other text about the venue. " * 10 + "Banquet on November 16."
    assert not page_mentions(far, "2026-11-16", words)


# ---- writing conferences.yml ----------------------------------------------------

SAMPLE = """# header line
#  Last automated update: never

# ---- Vision ----

- name: CVPR
  edition: 2027
  rank: "A*"
  timeline:
    - label: Paper Submission
      date: 2026-11-16
      tz: AoE

- name: ECCV
  edition: 2026
  note: "Odd: but true"
  timeline:
    - label: Paper Submission
      date: 2026-03-05

# ---- Robotics ----

- name: CoRL
  edition: 2027
  timeline:
    - label: Paper Submission
      date: tba
"""


def test_replace_entries_rewrites_only_the_changed_venue():
    new = {"name": "ECCV", "edition": 2028, "location": "TBA", "note": "ECCV 2026 closed 5 Mar 2026: next one TBA.",
           "timeline": [{"label": "Paper Submission", "date": "tba"}]}
    out = replace_entries(SAMPLE, {"ECCV": new})
    assert out.split("- name: ECCV")[0] == SAMPLE.split("- name: ECCV")[0], "earlier venues are untouched"
    assert out.split("# ---- Robotics ----")[1] == SAMPLE.split("# ---- Robotics ----")[1], "later venues and comments too"
    data = yaml.safe_load(out)
    assert data[1] == new
    assert yaml.safe_load(replace_entries(SAMPLE, {})) == yaml.safe_load(SAMPLE)


def test_render_entry_matches_the_hand_written_style():
    text = render_entry({"name": "ICRA", "edition": 2028, "category": "robotics", "rank": "A*", "location": "Seoul, South Korea",
                         "flag": "🇰🇷", "website": "https://x.org/", "timeline": [{"label": "Paper Submission", "date": "2027-09-15", "time": "12:00", "tz": "PST"}]})
    assert text == ('- name: ICRA\n  edition: 2028\n  category: robotics\n  rank: "A*"\n  location: Seoul, South Korea\n'
                    '  flag: "🇰🇷"\n  website: https://x.org/\n  timeline:\n    - label: Paper Submission\n'
                    '      date: 2027-09-15\n      time: "12:00"\n      tz: PST\n')


def test_the_write_guard_refuses_a_lost_or_unplanned_venue():
    import pytest
    from deadlines.pipeline import _check
    before = yaml.safe_load(SAMPLE)
    _check(before, yaml.safe_load(replace_entries(SAMPLE, {})), {})
    with pytest.raises(SystemExit):
        _check(before, before[:2], {})
    edited = [dict(before[0], edition=2028)] + before[1:]
    with pytest.raises(SystemExit):
        _check(before, edited, {})
    _check(before, edited, {"CVPR": edited[0]})


def test_stamp_header_records_the_run():
    out = stamp_header(SAMPLE, "2026-11-01", 3)
    assert "#  Last automated update: 2026-11-01 (3 venues changed)" in out
    assert out.count("Last automated update") == 1
