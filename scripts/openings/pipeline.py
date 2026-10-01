import sys
import datetime
from pathlib import Path
from typing import List, Optional
import yaml

from .models import Opening, DiscoveredItem, HistoryEvent
from .discovery import run_discovery
from .extract import extract_from_discovered, format_human_date
from .normalize import clean_url, generate_slug, normalize_region
from .deduplicate import deduplicate_openings, compute_content_hash
from .classifier import classify_relevance
from .storage import get_connection, save_or_update_opening, load_all_openings_from_db
from .config import OPENINGS_YML, load_research_profile

OPENINGS_HEADER = """# ==========================================================================
#  PhD & Postdoc Openings - data source for /phd-postdoc-openings/
# ==========================================================================
#
#  Rendered by _pages/phd-postdoc-openings.html, driven by initOpeningsTracker() in
#  assets/js/main.js, styled by _sass/theme/_openings.scss.
#  This file is an automated collection of research positions, populated by the
#  discovery crawler in scripts/openings/.
#
#  Update openings: python scripts/manage.py openings run
# ==========================================================================

"""

# Custom YAML Dumper matching manage.py
class CleanDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(CleanDumper, self).increase_indent(flow, False)

def string_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    if len(data) > 120:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
    if any(char in data for char in ["'", '"', '<', '>', '&', '·', ':']):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

CleanDumper.add_representer(str, string_representer)

def export_to_yaml(openings: List[Opening], output_path: Path = OPENINGS_YML):
    """
    Export sanitized list of openings to public YAML for Jekyll.
    Ensures internal crawler logs or credentials are never exposed.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    today_human = datetime.date.today().strftime("%-d %B %Y")

    # Filter out Low Relevance or Expired positions from the public active display if preferred,
    # or keep them with status "Expired"
    active_openings = [op for op in openings if op.relevance != "Low Relevance" and op.status != "Expired"]

    data = {
        "last_updated": now.isoformat(),
        "last_updated_human": today_human,
        "total_count": len(active_openings),
        "openings": [op.model_dump(exclude={"content_hash", "source_urls"}, exclude_none=True) for op in active_openings]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(OPENINGS_HEADER)
        yaml.dump(data, f, Dumper=CleanDumper, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)

    print(f"Exported {len(active_openings)} openings to {output_path}")

def run_openings_pipeline(dry_run: bool = False, max_queries: int = 15) -> List[Opening]:
    """
    Execute full pipeline:
    Discovery -> Extract -> Normalize -> Classify -> Deduplicate -> Store -> Export
    """
    print("=== PhD & Postdoc Openings Discovery Pipeline ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # 1. Discovery
    print("Phase 1: Discovering openings across public academic sources...")
    discovered = run_discovery(max_queries=max_queries)
    print(f"  Discovered {len(discovered)} raw candidate opportunities.")

    if not discovered:
        print("  No new raw candidates found from active queries.")
        # If not dry run, re-export existing database in case statuses changed
        if not dry_run:
            conn = get_connection()
            existing = load_all_openings_from_db(conn)
            export_to_yaml(existing)
        return []

    # 2. Extract & Normalize & Classify
    print("Phase 2: Extracting, normalizing, and classifying relevance...")
    extracted_candidates: List[Opening] = []
    today_str = datetime.date.today().isoformat()

    for item in discovered:
        data = extract_from_discovered(item)
        if not data:
            continue
        tier, topics, expl = classify_relevance(data["title"], data["raw_text"])

        # Discard irrelevant general engineering/computing
        if tier == "Low Relevance":
            continue

        c_url = clean_url(data["source_url"])
        slug = generate_slug(data["institution"], data["title"], data["position_type"])

        opening = Opening(
            id=slug,
            title=data["title"],
            position_type=data["position_type"],
            institution=data["institution"],
            city=data["city"],
            country=data["country"],
            region=data["region"],
            research_topics=topics,
            description=data["description"],
            deadline=data["deadline"],
            deadline_human=data["deadline_human"],
            status="Open",
            relevance=tier,
            relevance_explanation=expl,
            source=data["source"],
            source_url=c_url,
            application_url=data["application_url"],
            first_seen=today_str,
            last_seen=today_str,
            last_verified=today_str,
            source_urls=[c_url]
        )
        extracted_candidates.append(opening)

    print(f"  {len(extracted_candidates)} opportunities matched research priorities.")

    # 3. Deduplicate
    print("Phase 3: Deduplicating and resolving canonical sources...")
    deduped = deduplicate_openings(extracted_candidates)
    print(f"  {len(deduped)} canonical openings after deduplication.")

    if dry_run:
        print("\n[Dry Run Summary]:")
        for op in deduped:
            print(f"  [{op.relevance}] {op.title} - {op.institution} ({op.country}) | Deadline: {op.deadline_human}")
        return deduped

    # 4. Store in SQLite
    print("Phase 4: Persisting to internal SQLite store and audit log...")
    conn = get_connection()
    stats = {"NEW": 0, "UPDATED": 0, "DEADLINE_CHANGED": 0, "UNCHANGED": 0}

    for op in deduped:
        action = save_or_update_opening(conn, op)
        stats[action] = stats.get(action, 0) + 1

    print(f"  Changes: {stats['NEW']} new, {stats['UPDATED']} updated, {stats['DEADLINE_CHANGED']} deadline changes.")

    # 5. Export clean YAML
    print("Phase 5: Generating public Jekyll data in _data/openings.yml...")
    all_openings = load_all_openings_from_db(conn)
    export_to_yaml(all_openings)

    return all_openings
