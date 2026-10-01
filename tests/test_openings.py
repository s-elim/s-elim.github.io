import os
import sys
import datetime
import tempfile
import sqlite3
from pathlib import Path
import pytest

# Ensure scripts is on sys.path
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from openings.normalize import clean_url, generate_slug, normalize_region
from openings.extract import parse_iso_date, format_human_date, extract_deadline, detect_position_type
from openings.classifier import classify_relevance
from openings.deduplicate import deduplicate_openings, compute_content_hash, classify_source_rank
from openings.models import Opening, HistoryEvent, RelevanceExplanation
from openings.storage import evaluate_deadline_status, save_or_update_opening, load_all_openings_from_db
from openings.pipeline import export_to_yaml

def test_url_normalization_and_utm_stripping():
    raw = "https://jobs.ethz.ch/position-42/?utm_source=linkedin&utm_medium=cpc&utm_campaign=hiring&ref=feed#apply"
    cleaned = clean_url(raw)
    assert "utm_source" not in cleaned
    assert "utm_medium" not in cleaned
    assert "ref" not in cleaned
    assert cleaned == "https://jobs.ethz.ch/position-42"

def test_date_parsing_and_deadline_extraction():
    # ISO date parsing
    assert parse_iso_date("2026-10-31") == "2026-10-31"
    assert parse_iso_date("31 October 2026") == "2026-10-31"
    assert parse_iso_date("October 31, 2026") == "2026-10-31"

    # Deadline extraction from text
    iso, human = extract_deadline("The application deadline is 31 October 2026.")
    assert iso == "2026-10-31"
    assert "31 October 2026" in human

    iso_rolling, human_rolling = extract_deadline("Applications are considered on a rolling basis until filled.")
    assert iso_rolling is None
    assert "Rolling" in human_rolling

def test_role_detection():
    assert detect_position_type("PhD Candidate in Robot Learning") == "PhD"
    assert detect_position_type("Postdoctoral Fellow in Autonomous Manipulation") == "Postdoc"
    assert detect_position_type("Doctoral Researcher (Doktorand) in Computer Vision") == "Doctoral Researcher"
    assert detect_position_type("Research Scientist in World Models") == "Research Scientist"

def test_slug_generation_and_region_mapping():
    slug = generate_slug("ETH Zürich", "Robot Learning PhD", "PhD", 2026)
    assert "eth-zurich-robot-learning-phd" in slug
    assert normalize_region("Switzerland") == "Europe"
    assert normalize_region("United Kingdom") == "UK"
    assert normalize_region("South Korea") == "Asia-Pacific"
    assert normalize_region("United States") == "USA"

def test_relevance_classification():
    # High relevance: primary topics (World Models + Robot Learning)
    tier_high, topics_high, expl_high = classify_relevance(
        "PhD in Robot Learning and Latent World Models",
        "Investigating action-conditioned latent dynamics for mobile manipulation."
    )
    assert tier_high == "Highly Relevant"
    assert "World Models" in topics_high
    assert "Robot Learning" in topics_high
    assert expl_high.technical_alignment is not None
    assert expl_high.potential_gaps is not None

    # Relevant: secondary topic + manipulation
    tier_rel, topics_rel, expl_rel = classify_relevance(
        "Postdoctoral Position in 3D Computer Vision",
        "Working on 3D Gaussian Splatting and spatial reasoning tokens."
    )
    assert tier_rel in ["Highly Relevant", "Relevant"]

    # Low relevance: non-aligned domain
    tier_low, topics_low, expl_low = classify_relevance(
        "Financial Quantitative Analyst",
        "Risk management and stochastic portfolio optimization in banking."
    )
    assert tier_low == "Low Relevance"
    assert len(topics_low) == 0

def test_duplicate_detection_and_source_prioritization():
    # Candidate 1: aggregator (EURAXESS)
    op_euraxess = Opening(
        id="ethz-robotics-phd-2026",
        title="PhD in Robot Learning",
        position_type="PhD",
        institution="ETH Zürich",
        country="Switzerland",
        region="Europe",
        source="EURAXESS",
        source_url="https://euraxess.ec.europa.eu/jobs/123",
        application_url=None,
        deadline="2026-10-31",
        first_seen="2026-10-02",
        last_seen="2026-10-02",
        last_verified="2026-10-02"
    )

    # Candidate 2: official university portal (ETH Zürich)
    op_official = Opening(
        id="ethz-robot-learning-phd-2026",
        title="PhD in Robot Learning",
        position_type="PhD",
        institution="ETH Zürich",
        country="Switzerland",
        region="Europe",
        source="ETH Zürich Jobs",
        source_url="https://jobs.ethz.ch/position-456",
        application_url="https://jobs.ethz.ch/position-456/apply",
        deadline="2026-10-31",
        first_seen="2026-10-02",
        last_seen="2026-10-02",
        last_verified="2026-10-02"
    )

    # Candidate 3: LinkedIn aggregator
    op_linkedin = Opening(
        id="ethz-phd-robot-learning",
        title="PhD in Robot Learning",
        position_type="PhD",
        institution="ETH Zürich",
        country="Switzerland",
        region="Europe",
        source="LinkedIn Jobs",
        source_url="https://linkedin.com/jobs/view/789",
        application_url=None,
        deadline="2026-10-31",
        first_seen="2026-10-02",
        last_seen="2026-10-02",
        last_verified="2026-10-02"
    )

    deduped = deduplicate_openings([op_euraxess, op_official, op_linkedin])
    assert len(deduped) == 1
    canonical = deduped[0]
    # The official university URL should be selected as the canonical source
    assert canonical.source == "ETH Zürich Jobs"
    assert canonical.source_url == "https://jobs.ethz.ch/position-456"
    assert canonical.application_url == "https://jobs.ethz.ch/position-456/apply"
    # Secondary sources must be recorded
    assert len(canonical.source_urls) >= 2

def test_status_and_deadline_evaluation():
    today = datetime.date.today()
    future_date = (today + datetime.timedelta(days=40)).isoformat()
    closing_soon_date = (today + datetime.timedelta(days=5)).isoformat()
    past_date = (today - datetime.timedelta(days=5)).isoformat()

    assert evaluate_deadline_status(future_date, "Open") == "Open"
    assert evaluate_deadline_status(closing_soon_date, "Open") == "Closing Soon"
    assert evaluate_deadline_status(past_date, "Open") == "Expired"
    assert evaluate_deadline_status(None, "New") == "New"

def test_sqlite_storage_and_history_audit(tmp_path):
    # Test SQLite persistence in isolated temporary directory
    db_file = tmp_path / "test_openings.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    from openings.storage import _init_db
    _init_db(conn)

    op = Opening(
        id="test-phd-2026",
        title="Doctoral Researcher in World Models",
        position_type="PhD",
        institution="TU Munich",
        country="Germany",
        region="Europe",
        source="TUM Jobs",
        source_url="https://tum.de/jobs/1",
        deadline="2026-11-01",
        deadline_human="1 November 2026",
        first_seen="2026-10-02",
        last_seen="2026-10-02",
        last_verified="2026-10-02"
    )

    # First insert: detected as NEW
    action1 = save_or_update_opening(conn, op)
    assert action1 == "NEW"

    # Second pass with deadline changed
    op.deadline = "2026-11-15"
    op.deadline_human = "15 November 2026"
    action2 = save_or_update_opening(conn, op)
    assert action2 == "DEADLINE_CHANGED"

    loaded = load_all_openings_from_db(conn)
    assert len(loaded) == 1
    assert loaded[0].deadline == "2026-11-15"
    assert len(loaded[0].history) >= 2

def test_yaml_export_hygiene(tmp_path):
    yml_file = tmp_path / "openings_test.yml"
    op = Opening(
        id="test-phd-export",
        title="Postdoc in Physical AI",
        position_type="Postdoc",
        institution="Oxford",
        country="UK",
        region="UK",
        source="Oxford Jobs",
        source_url="https://ox.ac.uk/jobs/1",
        deadline="2026-12-01",
        first_seen="2026-10-02",
        last_seen="2026-10-02",
        last_verified="2026-10-02"
    )

    export_to_yaml([op], output_path=yml_file)
    assert yml_file.exists()
    content = yml_file.read_text(encoding="utf-8")
    assert "test-phd-export" in content
    assert "Postdoc in Physical AI" in content
    # Ensure no internal-only keys leak
    assert "content_hash" not in content

def test_spa_detection_and_playwright_fetcher():
    from openings.playwright_fetcher import is_spa_portal
    assert is_spa_portal("https://ethz.myworkdayjobs.com/en-US/eth-jobs/job/PhD-Position_123") is True
    assert is_spa_portal("https://boards.greenhouse.io/universitylab/jobs/456") is True
    assert is_spa_portal("https://jobs.ox.ac.uk/details") is False
