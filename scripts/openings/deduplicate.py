import hashlib
import re
from typing import List, Dict, Tuple, Optional
from .models import Opening
from .config import SOURCE_PRIORITY
from .normalize import clean_url

def compute_content_hash(institution: str, title: str, pos_type: str) -> str:
    """Generate SHA-256 hash representing canonical entity key."""
    norm = f"{institution.lower().strip()}|{title.lower().strip()}|{pos_type.lower().strip()}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

def classify_source_rank(url: str, source_name: str) -> int:
    """Rank source priority (lower number = higher priority)."""
    low_url = url.lower()
    low_src = source_name.lower()

    if any(u in low_url for u in [".edu", ".ac.uk", ".ch", ".de", ".nl", ".fr", ".se"]) and "jobs." in low_url:
        return SOURCE_PRIORITY["official_university"]
    if "lab" in low_url or "group" in low_url:
        return SOURCE_PRIORITY["official_lab"]
    if "euraxess" in low_url or "euraxess" in low_src:
        return SOURCE_PRIORITY["euraxess"]
    if "academicpositions" in low_url or "academic positions" in low_src:
        return SOURCE_PRIORITY["academic_positions"]
    if "academicjobsonline" in low_url or "academicjobsonline" in low_src:
        return SOURCE_PRIORITY["academic_jobs_online"]
    if "nature.com" in low_url or "nature" in low_src:
        return SOURCE_PRIORITY["nature_careers"]
    if "linkedin.com" in low_url or "linkedin" in low_src:
        return SOURCE_PRIORITY["linkedin"]
    return SOURCE_PRIORITY["search_engine"]

def are_similar(a_inst: str, a_title: str, b_inst: str, b_title: str) -> bool:
    """Fuzzy check if two postings represent the exact same opportunity."""
    if a_inst.lower() != b_inst.lower() and a_inst != "University / Research Institute" and b_inst != "University / Research Institute":
        return False
    
    # Token jaccard similarity on titles
    tokens_a = set(re.findall(r'\w+', a_title.lower()))
    tokens_b = set(re.findall(r'\w+', b_title.lower()))
    if not tokens_a or not tokens_b:
        return False
    
    overlap = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    return overlap > 0.7

def deduplicate_openings(candidates: List[Opening]) -> List[Opening]:
    """
    Deduplicate a list of candidate Openings.
    Prioritizes canonical official links over aggregators and preserves secondary sources.
    """
    deduped: List[Opening] = []

    for cand in candidates:
        match_idx = -1
        cand_hash = compute_content_hash(cand.institution, cand.title, cand.position_type)

        for idx, existing in enumerate(deduped):
            existing_hash = compute_content_hash(existing.institution, existing.title, existing.position_type)
            if cand_hash == existing_hash or are_similar(cand.institution, cand.title, existing.institution, existing.title):
                match_idx = idx
                break

        if match_idx == -1:
            cand.content_hash = cand_hash
            if cand.source_url not in cand.source_urls:
                cand.source_urls.append(cand.source_url)
            deduped.append(cand)
        else:
            existing = deduped[match_idx]
            # Add URL to secondary sources
            if cand.source_url not in existing.source_urls:
                existing.source_urls.append(cand.source_url)

            # Check if candidate has higher source priority
            cand_rank = classify_source_rank(cand.source_url, cand.source)
            existing_rank = classify_source_rank(existing.source_url, existing.source)

            if cand_rank < existing_rank:
                # Promote candidate as primary source
                existing.source = cand.source
                existing.source_url = cand.source_url
                if cand.application_url:
                    existing.application_url = cand.application_url
                # Fill missing details
                if existing.deadline is None and cand.deadline is not None:
                    existing.deadline = cand.deadline
                    existing.deadline_human = cand.deadline_human

    return deduped
