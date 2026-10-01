import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DB_PATH, ensure_directories
from .models import Opening, HistoryEvent, RelevanceExplanation

def get_connection() -> sqlite3.Connection:
    """Connect to the internal crawler SQLite database and create tables if absent."""
    ensure_directories()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn

def _init_db(conn: sqlite3.Connection):
    """Initialize schema for tracking openings, runs, and audit events."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS openings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                position_type TEXT NOT NULL,
                institution TEXT NOT NULL,
                department TEXT,
                lab TEXT,
                principal_investigator TEXT,
                city TEXT,
                country TEXT NOT NULL,
                region TEXT NOT NULL,
                research_topics TEXT,
                description TEXT,
                requirements TEXT,
                preferred_qualifications TEXT,
                salary TEXT,
                funding TEXT,
                deadline TEXT,
                deadline_human TEXT,
                start_date TEXT,
                employment_type TEXT,
                status TEXT NOT NULL,
                relevance TEXT NOT NULL,
                relevance_explanation TEXT,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                application_url TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                last_verified TEXT NOT NULL,
                content_hash TEXT,
                source_urls TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opening_id TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (opening_id) REFERENCES openings(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_discovered INTEGER DEFAULT 0,
                new_positions INTEGER DEFAULT 0,
                updated_positions INTEGER DEFAULT 0,
                unchanged_positions INTEGER DEFAULT 0,
                notes TEXT
            )
        """)

def save_or_update_opening(conn: sqlite3.Connection, op: Opening) -> str:
    """
    Save or update an opening in SQLite, detecting status and deadline transitions.
    Returns the action taken: 'NEW', 'UPDATED', 'DEADLINE_CHANGED', or 'UNCHANGED'.
    """
    today_str = datetime.date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT * FROM openings WHERE id = ?", (op.id,))
    row = cur.fetchone()

    if not row:
        # Check if deadline is already closing soon or expired
        initial_status = evaluate_deadline_status(op.deadline, "New")
        op.status = initial_status
        op.first_seen = today_str
        op.last_seen = today_str
        op.last_verified = today_str
        op.history.append(HistoryEvent(date=today_str, event=f"Discovered as {initial_status}"))

        with conn:
            conn.execute("""
                INSERT INTO openings (
                    id, title, position_type, institution, department, lab,
                    principal_investigator, city, country, region, research_topics,
                    description, requirements, preferred_qualifications, salary,
                    funding, deadline, deadline_human, start_date, employment_type,
                    status, relevance, relevance_explanation, source, source_url,
                    application_url, first_seen, last_seen, last_verified, content_hash, source_urls
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                op.id, op.title, op.position_type, op.institution, op.department, op.lab,
                op.principal_investigator, op.city, op.country, op.region,
                json.dumps(op.research_topics), op.description, json.dumps(op.requirements),
                json.dumps(op.preferred_qualifications), op.salary, op.funding,
                op.deadline, op.deadline_human, op.start_date, op.employment_type,
                op.status, op.relevance,
                json.dumps(op.relevance_explanation.model_dump() if op.relevance_explanation else {}),
                op.source, op.source_url, op.application_url, op.first_seen, op.last_seen,
                op.last_verified, op.content_hash, json.dumps(op.source_urls)
            ))

            conn.execute("""
                INSERT INTO audit_events (opening_id, event_date, event_type, details)
                VALUES (?, ?, ?, ?)
            """, (op.id, today_str, "NEW", f"Discovered from {op.source}"))

        return "NEW"

    # Opening exists: check for changes
    existing_deadline = row["deadline"]
    action = "UNCHANGED"
    updated_status = evaluate_deadline_status(op.deadline or existing_deadline, row["status"])

    with conn:
        if op.deadline and existing_deadline and op.deadline != existing_deadline:
            action = "DEADLINE_CHANGED"
            event_msg = f"Deadline changed from {existing_deadline} to {op.deadline}"
            conn.execute("""
                INSERT INTO audit_events (opening_id, event_date, event_type, details)
                VALUES (?, ?, ?, ?)
            """, (op.id, today_str, "DEADLINE_CHANGED", event_msg))
        elif op.description and row["description"] != op.description:
            action = "UPDATED"
            updated_status = "Updated"
            conn.execute("""
                INSERT INTO audit_events (opening_id, event_date, event_type, details)
                VALUES (?, ?, ?, ?)
            """, (op.id, today_str, "UPDATED", "Description updated from source"))

        conn.execute("""
            UPDATE openings SET
                last_seen = ?,
                last_verified = ?,
                status = ?,
                deadline = COALESCE(?, deadline),
                deadline_human = COALESCE(?, deadline_human),
                source_urls = ?
            WHERE id = ?
        """, (
            today_str, today_str, updated_status,
            op.deadline, op.deadline_human,
            json.dumps(list(set(json.loads(row["source_urls"] or "[]") + op.source_urls))),
            op.id
        ))

    return action

def evaluate_deadline_status(deadline_iso: Optional[str], default_status: str) -> str:
    """Evaluate whether an opening is Open, Closing Soon, or Expired."""
    if not deadline_iso or deadline_iso == "9999-12-31":
        return default_status if default_status in ["New", "Updated"] else "Open"

    try:
        deadline_date = datetime.datetime.strptime(deadline_iso, "%Y-%m-%d").date()
        today = datetime.date.today()
        diff = (deadline_date - today).days

        if diff < 0:
            return "Expired"
        elif diff <= 14:
            return "Closing Soon"
        else:
            return default_status if default_status in ["New", "Updated"] else "Open"
    except Exception:
        return default_status

def load_all_openings_from_db(conn: sqlite3.Connection) -> List[Opening]:
    """Retrieve all tracked openings from the database with history logs."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM openings ORDER BY first_seen DESC")
    rows = cur.fetchall()

    openings = []
    for r in rows:
        # Load audit events for this opening
        cur.execute("SELECT event_date, event_type, details FROM audit_events WHERE opening_id = ? ORDER BY id ASC", (r["id"],))
        events = [HistoryEvent(date=e["event_date"], event=e["details"] or e["event_type"]) for e in cur.fetchall()]

        rel_dict = json.loads(r["relevance_explanation"] or "{}")
        rel_expl = RelevanceExplanation(**rel_dict) if rel_dict else None

        openings.append(Opening(
            id=r["id"],
            title=r["title"],
            position_type=r["position_type"],
            institution=r["institution"],
            department=r["department"] or "Not specified",
            lab=r["lab"] or "Not specified",
            principal_investigator=r["principal_investigator"] or "Not specified",
            city=r["city"] or "Not specified",
            country=r["country"],
            region=r["region"],
            research_topics=json.loads(r["research_topics"] or "[]"),
            description=r["description"] or "",
            requirements=json.loads(r["requirements"] or "[]"),
            preferred_qualifications=json.loads(r["preferred_qualifications"] or "[]"),
            salary=r["salary"] or "Not specified",
            funding=r["funding"] or "Not specified",
            deadline=r["deadline"],
            deadline_human=r["deadline_human"] or "Rolling / Open until filled",
            start_date=r["start_date"] or "Not specified",
            employment_type=r["employment_type"] or "Full-time",
            status=r["status"],
            relevance=r["relevance"],
            relevance_explanation=rel_expl,
            source=r["source"],
            source_url=r["source_url"],
            application_url=r["application_url"],
            first_seen=r["first_seen"],
            last_seen=r["last_seen"],
            last_verified=r["last_verified"],
            history=events,
            source_urls=json.loads(r["source_urls"] or "[]"),
            content_hash=r["content_hash"]
        ))

    return openings
