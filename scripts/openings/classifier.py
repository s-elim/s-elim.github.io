import re
from typing import Dict, Any, List, Tuple
from .config import load_research_profile
from .models import RelevanceExplanation

def classify_relevance(title: str, text: str) -> Tuple[str, List[str], RelevanceExplanation]:
    """
    Classify research opening into explainable categories based on research_profile.yaml:
    - Highly Relevant
    - Relevant
    - Potentially Relevant
    - Low Relevance
    """
    profile = load_research_profile()
    focus = profile.get("research_focus", {})
    primary_defs = focus.get("primary_topics", [])
    secondary_defs = focus.get("secondary_topics", [])

    corpus = f"{title}\n{text}".lower()

    matched_primary = []
    for item in primary_defs:
        name = item["name"]
        keywords = item.get("keywords", [])
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw.lower())}\b', corpus):
                matched_primary.append(name)
                break

    matched_secondary = []
    for item in secondary_defs:
        name = item["name"]
        keywords = item.get("keywords", [])
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw.lower())}\b', corpus):
                matched_secondary.append(name)
                break

    all_matched = list(dict.fromkeys(matched_primary + matched_secondary))

    # Evaluate relevance tier
    if len(matched_primary) >= 2 or (len(matched_primary) >= 1 and any(t in matched_secondary for t in ["Manipulation", "3D Vision", "Foundation Models"])):
        tier = "Highly Relevant"
        tech_align = f"Focuses directly on {', '.join(matched_primary[:2])} and physical robot control."
        res_align = "Core alignment with Physical Super Intelligence and world model thesis directions."
    elif len(matched_primary) >= 1 or len(matched_secondary) >= 2:
        tier = "Relevant"
        tech_align = f"Involves {', '.join((matched_primary + matched_secondary)[:2])} methodology."
        res_align = "Substantial overlap with embodied perception and robotic manipulation priorities."
    elif len(matched_secondary) >= 1:
        tier = "Potentially Relevant"
        tech_align = f"Touches related methods in {', '.join(matched_secondary[:2])}."
        res_align = "Adjacent domain in visual intelligence or robotic systems."
    else:
        tier = "Low Relevance"
        tech_align = "Broad computing or general engineering with limited physical AI overlap."
        res_align = "Not closely aligned with current spatial intelligence or world model priorities."

    qual_align = "Candidate background in M.Sc. EE (AI & CV) with PyTorch and robotics experience meets baseline requirements."
    gaps = "None identified"
    if "phd" in corpus and ("german c1" in corpus or "french c1" in corpus):
        gaps = "Local European language requirement (C1 level)"

    explanation = RelevanceExplanation(
        matched_topics=all_matched,
        technical_alignment=tech_align,
        research_alignment=res_align,
        qualification_alignment=qual_align,
        potential_gaps=gaps
    )

    return tier, all_matched, explanation
