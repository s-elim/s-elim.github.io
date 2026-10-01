import time
import re
import urllib.parse
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup

from .models import DiscoveredItem
from .config import load_research_profile

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Public academic RSS / feed endpoints
ACADEMIC_FEEDS = [
    {
        "name": "EURAXESS Jobs (Latest)",
        "url": "https://euraxess.ec.europa.eu/job-feed",
        "type": "euraxess"
    },
    {
        "name": "EURAXESS Jobs (Page 1)",
        "url": "https://euraxess.ec.europa.eu/job-feed?page=1",
        "type": "euraxess"
    },
    {
        "name": "EURAXESS Jobs (Page 2)",
        "url": "https://euraxess.ec.europa.eu/job-feed?page=2",
        "type": "euraxess"
    },
    {
        "name": "OpenRobotics ROS Discourse",
        "url": "https://discourse.ros.org/c/jobs.rss",
        "type": "official_rss"
    }
]

# Verified active academic research labs recruiting in Embodied AI, World Models, and Robotics
CURATED_LAB_TARGETS = [
    {
        "title": "PhD & Postdoc Positions in Embodied AI and Robot Learning",
        "url": "https://donghao51.github.io/open-positions/",
        "source_name": "ELLIS Institute Finland / Tampere University",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoctoral Fellowships in Machine Learning and Robotics",
        "url": "https://rpg.ifi.uzh.ch/positions.html",
        "source_name": "University of Zurich (RPG Lab)",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoc Positions in Embodied Minds and Agents",
        "url": "https://lema-nus.github.io/",
        "source_name": "National University of Singapore (LEMA Lab)",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoctoral Positions in Computer Vision and Visual Intelligence",
        "url": "https://sites.google.com/view/fahadkhans/open-positions",
        "source_name": "MBZUAI Vision Lab",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoctoral Positions in 3D Computer Vision and Robot Perception",
        "url": "https://sites.usc.edu/iris-cvlab/position/",
        "source_name": "USC Iris Computer Vision Lab",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoctoral Research Positions in Robot Learning",
        "url": "https://spring.epfl.ch/open_positions.html",
        "source_name": "EPFL SPRING Lab",
        "position_type": "PhD"
    }
]

def generate_search_queries(max_queries: int = 40) -> List[Dict[str, str]]:
    """
    Generate clean, high-precision search query combinations.
    Avoids over-punctuated Boolean logic that triggers search engine bot guards.
    """
    queries = [
        {"query": 'PhD position robotics "world models"', "source_type": "search_engine", "label": "PhD - World Models"},
        {"query": 'Postdoc position robotics "vision language action"', "source_type": "search_engine", "label": "Postdoc - VLA"},
        {"query": 'PhD student "embodied AI" robot learning', "source_type": "search_engine", "label": "PhD - Embodied AI"},
        {"query": 'PhD position "robot learning" manipulation', "source_type": "search_engine", "label": "PhD - Manipulation"},
        {"query": 'Postdoc "spatial intelligence" robotics 3D vision', "source_type": "search_engine", "label": "Postdoc - Spatial Vision"},
        {"query": 'site:jobs.ethz.ch robotics PhD position', "source_type": "official_university", "label": "ETH Zurich Robotics"},
        {"query": 'site:epfl.ch/about/working robotics postdoc position', "source_type": "official_university", "label": "EPFL Robotics"},
        {"query": 'site:is.mpg.de/jobs PhD robot learning', "source_type": "official_university", "label": "MPI-IS Robot Learning"},
        {"query": 'site:tudelft.nl/vacatures cognitive robotics PhD', "source_type": "official_university", "label": "TU Delft Cognitive Robotics"},
        {"query": 'site:inria.fr/en/job-offers robotics perception PhD', "source_type": "official_university", "label": "Inria Perception"},
        {"query": 'site:ri.cmu.edu PhD robot learning manipulation', "source_type": "official_university", "label": "CMU Robotics"},
        {"query": 'site:bair.berkeley.edu postdoc robot learning', "source_type": "official_university", "label": "Berkeley BAIR"}
    ]
    return queries[:max_queries]

def fetch_curated_labs(client: httpx.Client) -> List[DiscoveredItem]:
    """Fetch verified academic research lab recruiting portals."""
    items = []
    for lab in CURATED_LAB_TARGETS:
        try:
            resp = client.get(lab["url"], timeout=10.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                items.append(DiscoveredItem(
                    title=lab["title"],
                    url=lab["url"],
                    source_name=lab["source_name"],
                    source_type="official_university",
                    snippet=text[:1500],
                    raw_html=resp.text
                ))
        except Exception:
            pass
    return items

def fetch_rss_feed(client: httpx.Client, feed_meta: Dict[str, str]) -> List[DiscoveredItem]:
    """Fetch and parse public RSS/ATOM academic feeds."""
    items = []
    try:
        resp = client.get(feed_meta["url"], timeout=12.0)
        if resp.status_code != 200:
            return items
        
        root = ET.fromstring(resp.content)
        # Handle RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            desc = item.findtext("description") or ""
            if link and title:
                items.append(DiscoveredItem(
                    title=clean_text(title),
                    url=link.strip(),
                    source_name=feed_meta["name"],
                    source_type=feed_meta["type"],
                    snippet=clean_text(desc)[:400]
                ))
    except Exception:
        # Graceful degradation on network/feed failure
        pass
    return items

def search_duckduckgo_public(client: httpx.Client, query: str, max_results: int = 5) -> List[DiscoveredItem]:
    """
    Search DuckDuckGo public HTML interface without paid APIs.
    Gracefully returns empty list if challenged or rate-limited.
    """
    items = []
    url = "https://html.duckduckgo.com/html/"
    try:
        resp = client.post(url, data={"q": query}, timeout=12.0)
        if resp.status_code != 200:
            return items
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select(".result")
        for res in results[:max_results]:
            if res.select_one(".no-results"):
                continue
            link_tag = res.select_one(".result__url") or res.select_one(".result__title a") or res.select_one(".result__a")
            title_tag = res.select_one(".result__title") or res.select_one(".result__a")
            snippet_tag = res.select_one(".result__snippet")
            
            if not title_tag or not link_tag:
                continue
            
            raw_href = link_tag.get("href", "")
            target_url = extract_ddg_url(raw_href)
            if not target_url:
                continue
                
            title = clean_text(title_tag.get_text())
            snippet = clean_text(snippet_tag.get_text()) if snippet_tag else ""
            
            # Determine source type
            source_type = "search_engine"
            if "linkedin.com/jobs/view" in target_url:
                source_type = "linkedin"
            elif any(u in target_url for u in [".edu", ".ac.uk", ".ethz.ch", ".epfl.ch", "mpg.de", "inria.fr"]):
                source_type = "official_university"
            elif "euraxess.ec.europa.eu" in target_url:
                source_type = "euraxess"
                
            items.append(DiscoveredItem(
                title=title,
                url=target_url,
                source_name="Public Academic Search",
                source_type=source_type,
                snippet=snippet
            ))
    except Exception:
        pass
    return items

def extract_ddg_url(href: str) -> Optional[str]:
    """Unwrap actual URL from DuckDuckGo redirect link."""
    if "uddg=" in href:
        match = re.search(r'uddg=([^&]+)', href)
        if match:
            return urllib.parse.unquote(match.group(1))
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return None

def clean_text(text: str) -> str:
    """Strip extraneous whitespace and HTML artefacts."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    return " ".join(text.split()).strip()

def run_discovery(max_queries: int = 15, delay_between_requests: float = 1.0) -> List[DiscoveredItem]:
    """
    Main discovery orchestrator.
    Gathers items across curated lab targets, academic feeds, and public search.
    """
    discovered = []
    seen_urls = set()
    
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        # 1. Fetch curated research lab targets
        lab_items = fetch_curated_labs(client)
        for it in lab_items:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 2. Fetch academic RSS feeds
        for feed in ACADEMIC_FEEDS:
            feed_items = fetch_rss_feed(client, feed)
            for it in feed_items:
                if it.url not in seen_urls:
                    seen_urls.add(it.url)
                    discovered.append(it)
            time.sleep(0.3)

        # 3. Run query combinations
        queries = generate_search_queries(max_queries=max_queries)
        for q_meta in queries:
            q = q_meta["query"]
            q_items = search_duckduckgo_public(client, q, max_results=3)
            for it in q_items:
                if it.url not in seen_urls:
                    seen_urls.add(it.url)
                    discovered.append(it)
            time.sleep(delay_between_requests)

    return discovered
