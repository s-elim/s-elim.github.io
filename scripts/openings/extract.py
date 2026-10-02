import os
import re
import datetime
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup
import httpx

from .models import DiscoveredItem, Opening
from .config import POSITION_TYPES, COUNTRY_TO_REGION

# Known university domains to canonical names
INSTITUTION_DOMAIN_MAP = {
    "ethz.ch": ("ETH Zürich", "Switzerland"),
    "epfl.ch": ("EPFL", "Switzerland"),
    "tum.de": ("Technical University of Munich (TUM)", "Germany"),
    "ox.ac.uk": ("University of Oxford", "UK"),
    "cam.ac.uk": ("University of Cambridge", "UK"),
    "imperial.ac.uk": ("Imperial College London", "UK"),
    "ucl.ac.uk": ("University College London (UCL)", "UK"),
    "ed.ac.uk": ("University of Edinburgh", "UK"),
    "tudelft.nl": ("TU Delft", "Netherlands"),
    "uva.nl": ("University of Amsterdam", "Netherlands"),
    "kth.se": ("KTH Royal Institute of Technology", "Sweden"),
    "inria.fr": ("Inria", "France"),
    "mpg.de": ("Max Planck Institute", "Germany"),
    "cmu.edu": ("Carnegie Mellon University", "USA"),
    "mit.edu": ("MIT", "USA"),
    "stanford.edu": ("Stanford University", "USA"),
    "berkeley.edu": ("UC Berkeley", "USA"),
    "utexas.edu": ("UT Austin", "USA"),
    "utoronto.ca": ("University of Toronto", "Canada"),
    "ubc.ca": ("University of British Columbia", "Canada"),
    "kaist.ac.kr": ("KAIST", "South Korea"),
    "snu.ac.kr": ("Seoul National University", "South Korea"),
    "nus.edu.sg": ("National University of Singapore", "Singapore"),
    "ntu.edu.sg": ("Nanyang Technological University", "Singapore"),
    "u-tokyo.ac.jp": ("University of Tokyo", "Japan"),
    "mbzuai.ac.ae": ("MBZUAI", "UAE"),
    "kaust.edu.sa": ("KAUST", "Saudi Arabia"),
    "uzh.ch": ("University of Zurich", "Switzerland"),
    "bristol.ac.uk": ("University of Bristol", "UK"),
    "usc.edu": ("University of Southern California", "USA"),
    "kuleuven.be": ("KU Leuven", "Belgium"),
    "donghao51.github.io": ("ELLIS Institute Finland & Tampere University", "Finland"),
    "lema-nus.github.io": ("National University of Singapore (NUS)", "Singapore"),
    "rpg.ifi.uzh.ch": ("University of Zurich", "Switzerland"),
    "spring.epfl.ch": ("EPFL", "Switzerland"),
    "sites.google.com/view/fahadkhans": ("MBZUAI", "UAE"),
    "sites.usc.edu/iris-cvlab": ("USC Iris CV Lab", "USA")
}

def detect_position_type(text: str) -> Optional[str]:
    """Classify position role from title or text. Returns None if not an academic research role."""
    lower = text.lower()
    if "dphil" in lower:
        return "DPhil"
    if any(k in lower for k in ["phd", "ph.d", "doctoral candidate", "doctoral student", "graduate student", "studentship"]):
        return "PhD"
    if any(k in lower for k in ["doctoral researcher", "doktorand", "pre-doc"]):
        return "Doctoral Researcher"
    if any(k in lower for k in ["postdoctoral", "post-doctoral", "post doctoral", "postdoc", "post-doc"]):
        return "Postdoc"
    if "research scientist" in lower:
        return "Research Scientist"
    if "research engineer" in lower:
        return "Research Engineer"
    if "research fellow" in lower:
        return "Research Fellow"
    if "research associate" in lower:
        return "Research Associate"
    if "fellowship" in lower:
        return "PhD"
    return None

def detect_institution_and_location(url: str, text: str) -> Tuple[str, str, str]:
    """Extract institution, city, and country deterministically."""
    # 1. Check domain first
    url_lower = url.lower()
    for domain, (inst, country) in INSTITUTION_DOMAIN_MAP.items():
        if domain in url_lower:
            return inst, "Not specified", country

    # 2. Check text for major institutions using word boundaries (prevent "submit" matching "MIT")
    for domain, (inst, country) in INSTITUTION_DOMAIN_MAP.items():
        if len(inst) <= 4:
            pattern = rf'\b{re.escape(inst)}\b'
        else:
            pattern = rf'(?i)\b{re.escape(inst)}\b'
        if re.search(pattern, text):
            return inst, "Not specified", country

    # 3. Fallback to country detection
    detected_country = "Not specified"
    for country in COUNTRY_TO_REGION.keys():
        if re.search(rf'\b{re.escape(country)}\b', text, re.IGNORECASE):
            detected_country = country
            break

    return "University / Research Institute", "Not specified", detected_country

def extract_deadline(text: str) -> Tuple[Optional[str], str]:
    """
    Extract deadline date as ISO (YYYY-MM-DD) and human-readable string.
    Returns (iso_date_or_none, human_string).
    """
    # Regex patterns for deadlines
    patterns = [
        # YYYY-MM-DD
        r'(?:deadline|closing date|closes|apply by|until)(?:\s+(?:is|on|by))?[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # DD Month YYYY
        r'(?:deadline|closing date|closes|apply by|until)(?:\s+(?:is|on|by))?[:\s]+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        # Month DD, YYYY
        r'(?:deadline|closing date|closes|apply by|until)(?:\s+(?:is|on|by))?[:\s]+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw_val = m.group(1).strip()
            iso_val = parse_iso_date(raw_val)
            if iso_val:
                return iso_val, format_human_date(iso_val)

    if re.search(r'\b(rolling|open until filled|as soon as possible|continuous)\b', text, re.IGNORECASE):
        return None, "Rolling / Open until filled"

    return None, "Rolling / Open until filled"

def parse_iso_date(raw: str) -> Optional[str]:
    """Parse various date formats into YYYY-MM-DD."""
    cleaned = raw.replace("/", "-").strip()
    # Try YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %d %Y"):
        try:
            dt = datetime.datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def format_human_date(iso_date: str) -> str:
    """Format YYYY-MM-DD into DD Month YYYY."""
    try:
        dt = datetime.datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%-d %B %Y")
    except Exception:
        return iso_date

# ==============================================================================
#  LLM Provider Abstraction (Optional modular fallback)
# ==============================================================================
class LLMProvider:
    def extract_position_info(self, raw_html: str, url: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def extract_position_info(self, raw_html: str, url: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        # Stub for optional gemini client calls via official google-genai
        # Will only execute when explicitly configured and needed
        return None

class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def extract_position_info(self, raw_html: str, url: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        # Stub for optional anthropic client calls
        return None

def extract_from_discovered(item: DiscoveredItem, llm_provider: Optional[LLMProvider] = None, enable_headless: bool = True) -> Dict[str, Any]:
    """
    Main extraction pipeline: deterministic parser first, optional Playwright rendered fetch for SPAs, optional LLM fallback.
    """
    raw_content = item.raw_html or ""
    # Fetch rendered DOM if it's an SPA portal or official university page without full content
    if enable_headless and not raw_content and (item.source_type == "official_university" or "jobs" in item.url):
        from .playwright_fetcher import is_spa_portal, fetch_rendered_html
        if is_spa_portal(item.url):
            rendered = fetch_rendered_html(item.url, timeout=12.0)
            if rendered:
                raw_content = rendered

    if raw_content:
        soup = BeautifulSoup(raw_content, "html.parser")
        # Strip script and style tags
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        page_text = soup.get_text(separator=" ", strip=True)[:5000]
    else:
        page_text = ""

    combined_text = f"{item.title}\n{item.snippet or ''}\n{page_text}"
    pos_type = detect_position_type(item.title + " " + (item.snippet or "") + " " + page_text[:400])
    if not pos_type:
        if item.source_type == "official_university":
            pos_type = "PhD"
        else:
            return None
    inst, city, country = detect_institution_and_location(item.url, combined_text)
    if item.detected_institution and (inst == "University / Research Institute" or item.source_type == "linkedin"):
        inst = item.detected_institution
    if item.detected_city and (city == "Not specified" or item.source_type == "linkedin"):
        city = item.detected_city
    if item.detected_country and (country == "Not specified" or item.source_type == "linkedin"):
        country = item.detected_country
    deadline_iso, deadline_human = extract_deadline(combined_text)

    region = item.detected_region or COUNTRY_TO_REGION.get(country, "Europe")

    # If deterministic extraction needs refinement and LLM is available
    if llm_provider and inst == "University / Research Institute":
        llm_data = llm_provider.extract_position_info(combined_text[:3000], item.url)
        if llm_data:
            inst = llm_data.get("institution", inst)
            country = llm_data.get("country", country)
            region = COUNTRY_TO_REGION.get(country, region)
            deadline_iso = llm_data.get("deadline", deadline_iso)
            if deadline_iso:
                deadline_human = format_human_date(deadline_iso)

    return {
        "title": item.title,
        "position_type": pos_type,
        "institution": inst,
        "city": city,
        "country": country,
        "region": region,
        "deadline": deadline_iso,
        "deadline_human": deadline_human,
        "description": item.snippet or "Research opening in academic laboratory.",
        "source": item.source_name,
        "source_url": item.url,
        "application_url": item.url if item.source_type == "official_university" else None,
        "raw_text": combined_text
    }
