import os
from pathlib import Path
import yaml

# Base directory paths
CRAWLER_DIR = Path(__file__).resolve().parent
REPO_ROOT = CRAWLER_DIR.parent.parent
DATA_DIR = REPO_ROOT / "_data"
OPENINGS_YML = DATA_DIR / "openings.yml"
LOCAL_DATA_DIR = CRAWLER_DIR / "data"
DB_PATH = LOCAL_DATA_DIR / "openings_state.db"
PROFILE_PATH = CRAWLER_DIR / "research_profile.yaml"

# Geographic taxonomy
REGIONS = ["Europe", "UK", "USA", "Canada", "Middle East", "Asia-Pacific"]

COUNTRY_TO_REGION = {
    "Germany": "Europe",
    "Switzerland": "Europe",
    "Netherlands": "Europe",
    "France": "Europe",
    "Sweden": "Europe",
    "Denmark": "Europe",
    "Finland": "Europe",
    "Norway": "Europe",
    "Austria": "Europe",
    "Belgium": "Europe",
    "Italy": "Europe",
    "Spain": "Europe",
    "Ireland": "Europe",
    "Czech Republic": "Europe",
    "Poland": "Europe",
    "Portugal": "Europe",
    "UK": "UK",
    "United Kingdom": "UK",
    "England": "UK",
    "Scotland": "UK",
    "Wales": "UK",
    "Northern Ireland": "UK",
    "USA": "USA",
    "United States": "USA",
    "Canada": "Canada",
    "UAE": "Middle East",
    "United Arab Emirates": "Middle East",
    "Saudi Arabia": "Middle East",
    "Qatar": "Middle East",
    "South Korea": "Asia-Pacific",
    "Korea": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "Taiwan": "Asia-Pacific",
    "India": "Asia-Pacific",
    "Hong Kong": "Asia-Pacific",
    "New Zealand": "Asia-Pacific"
}

# Position types taxonomy
POSITION_TYPES = [
    "PhD",
    "Doctoral Researcher",
    "DPhil",
    "Postdoc",
    "Research Scientist",
    "Research Engineer",
    "Research Fellow",
    "Research Associate"
]

# Status taxonomy
STATUS_TYPES = [
    "New",
    "Open",
    "Updated",
    "Closing Soon",
    "Expired",
    "Closed",
    "Needs Verification"
]

# Relevance categories
RELEVANCE_LEVELS = [
    "Highly Relevant",
    "Relevant",
    "Potentially Relevant",
    "Low Relevance"
]

# Source priority hierarchy (lower index = higher priority)
SOURCE_PRIORITY = {
    "official_university": 1,
    "official_lab": 2,
    "euraxess": 3,
    "academic_positions": 4,
    "academic_jobs_online": 5,
    "nature_careers": 6,
    "linkedin": 7,
    "search_engine": 8,
    "other": 9
}

def load_research_profile() -> dict:
    """Load research profile configuration from YAML."""
    if not PROFILE_PATH.exists():
        return {}
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def ensure_directories():
    """Ensure required local directories exist."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
