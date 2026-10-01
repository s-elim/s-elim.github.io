import re
import urllib.parse
import unicodedata
from typing import Optional
from .config import COUNTRY_TO_REGION, REGIONS

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "trk", "trackingId", "midToken"
}

def clean_url(raw_url: str) -> str:
    """
    Normalize URL: remove tracking parameters, fragments, and redundant trailing slashes.
    """
    if not raw_url:
        return ""
    
    parsed = urllib.parse.urlparse(raw_url.strip())
    # Query parameters cleanup
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    cleaned_params = [(k, v) for k, v in query_params if k not in TRACKING_PARAMS]
    new_query = urllib.parse.urlencode(cleaned_params)

    # Standardize scheme and netloc
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    return urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))

def generate_slug(institution: str, title: str, pos_type: str, year: Optional[int] = None) -> str:
    """Generate a clean, deterministic, URL-safe slug ID."""
    base = f"{institution} {title} {pos_type} {year or 2026}"
    # Decompose unicode characters
    normalized = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("utf-8")
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', normalized).lower()
    slug = re.sub(r'[\s-]+', '-', cleaned).strip('-')
    return slug[:52]

def normalize_region(country: str, default: str = "Europe") -> str:
    """Map country string to standard regions."""
    for known_country, region in COUNTRY_TO_REGION.items():
        if known_country.lower() in country.lower():
            return region
    return default
