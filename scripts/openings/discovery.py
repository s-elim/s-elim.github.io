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
        "name": "EURAXESS Jobs (Robotics)",
        "url": "https://euraxess.ec.europa.eu/jobs/search/feed?keywords=robotics",
        "type": "euraxess"
    },
    {
        "name": "EURAXESS Jobs (Computer Vision & AI)",
        "url": "https://euraxess.ec.europa.eu/jobs/search/feed?keywords=computer%20vision",
        "type": "euraxess"
    },
    {
        "name": "Nature Careers (Computer Science)",
        "url": "https://www.nature.com/naturecareers/rss/jobs/subject/computer-science",
        "type": "nature_careers"
    },
    {
        "name": "Nature Careers (Engineering)",
        "url": "https://www.nature.com/naturecareers/rss/jobs/subject/engineering",
        "type": "nature_careers"
    }
]

def generate_search_queries(max_queries: int = 40) -> List[Dict[str, str]]:
    """
    Generate systematic query combinations:
    Role x Topic x Region x Direct Institution Portals.
    """
    profile = load_research_profile()
    focus = profile.get("research_focus", {})
    primary = [t["name"] for t in focus.get("primary_topics", [])] or [
        "World Models", "Vision-Language-Action", "Embodied AI", "Physical AI", "Robot Learning", "Agentic Robotics"
    ]
    secondary = [t["name"] for t in focus.get("secondary_topics", [])] or [
        "3D Vision", "Spatial Reasoning", "6D Pose Estimation", "Manipulation"
    ]

    roles = ["PhD", "Doctoral Researcher", "DPhil", "Postdoc", "Postdoctoral Researcher", "Research Fellow", "Research Scientist"]
    queries = []

    # 1. Primary research areas across roles
    for topic in primary:
        for role in ["PhD", "Postdoc"]:
            q = f'"{role}" "{topic}" ("robotics" OR "computer vision" OR "manipulation") (university OR lab OR institute)'
            queries.append({"query": q, "source_type": "search_engine", "label": f"{role} - {topic}"})

    # 2. Key secondary topics for robotics and spatial intelligence
    for topic in ["Manipulation", "3D Vision", "6D Pose Estimation", "Spatial Reasoning"]:
        q = f'("PhD" OR "Postdoc") "{topic}" ("robot learning" OR "robotics") university'
        queries.append({"query": q, "source_type": "search_engine", "label": f"Specialized: {topic}"})

    # 3. Direct university & institute job portals
    direct_targets = [
        ('site:jobs.ethz.ch ("PhD" OR "Postdoc") ("robotics" OR "learning" OR "vision")', "ETH Zürich"),
        ('site:epfl.ch/about/working ("PhD" OR "Postdoc") ("robotics" OR "learning")', "EPFL"),
        ('site:tum.de/jobs ("Doktorand" OR "PhD" OR "Postdoc") ("robotics" OR "autonome")', "TUM"),
        ('site:ox.ac.uk ("DPhil" OR "Postdoctoral") ("robotics" OR "computer vision" OR "engineering")', "Oxford"),
        ('site:cam.ac.uk/jobs ("PhD" OR "Research Associate") ("robotics" OR "information engineering")', "Cambridge"),
        ('site:imperial.ac.uk/jobs ("PhD" OR "Research Associate") ("robotics" OR "computing")', "Imperial College"),
        ('site:tudelft.nl/vacatures ("PhD" OR "Postdoc") ("robotics" OR "cognitive robotics")', "TU Delft"),
        ('site:inria.fr/en/job-offers ("PhD" OR "Postdoc") ("robotics" OR "perception")', "Inria"),
        ('site:is.mpg.de/jobs ("PhD" OR "Postdoc") ("robotics" OR "learning" OR "embodied")', "MPI for Intelligent Systems"),
        ('site:ri.cmu.edu ("PhD" OR "Postdoc") ("manipulation" OR "robot learning")', "CMU Robotics Institute"),
        ('site:csail.mit.edu ("Postdoc" OR "Fellow") ("robotics" OR "embodied")', "MIT CSAIL"),
        ('site:bair.berkeley.edu ("Postdoc" OR "Fellow") ("robotics" OR "learning")', "UC Berkeley BAIR"),
        ('site:kaist.ac.kr ("PhD" OR "Postdoc") ("robotics" OR "computer vision")', "KAIST"),
        ('site:nus.edu.sg ("PhD" OR "Research Fellow") ("robotics" OR "computer vision")', "NUS"),
        ('site:mbzuai.ac.ae ("PhD" OR "Postdoc") ("robotics" OR "computer vision")', "MBZUAI")
    ]
    for q, inst in direct_targets:
        queries.append({"query": q, "source_type": "official_university", "label": f"Direct: {inst}"})

    # 4. Publicly indexed LinkedIn job postings (strictly public search results)
    linkedin_topics = [
        "World Models", "Vision-Language-Action", "Embodied AI", "Physical AI", "Robot Learning", "Agentic Robotics"
    ]
    for topic in linkedin_topics:
        q = f'site:linkedin.com/jobs/view ("PhD" OR "postdoctoral" OR "research fellow") "{topic}" robotics'
        queries.append({"query": q, "source_type": "linkedin", "label": f"LinkedIn Public: {topic}"})

    return queries[:max_queries]

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
    except Exception as e:
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
            link_tag = res.select_one(".result__url") or res.select_one(".result__title a")
            title_tag = res.select_one(".result__title")
            snippet_tag = res.select_one(".result__snippet")
            
            if not title_tag or not link_tag:
                continue
            
            raw_href = link_tag.get("href", "")
            # DuckDuckGo wraps URLs in /l/?uddg=...
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
                source_name="DuckDuckGo Public Search",
                source_type=source_type,
                snippet=snippet
            ))
    except Exception:
        # Fall through on error; never block execution
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
    Gathers items across academic feeds and polite search discovery.
    """
    discovered = []
    seen_urls = set()
    
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        # 1. Fetch academic RSS feeds
        for feed in ACADEMIC_FEEDS:
            feed_items = fetch_rss_feed(client, feed)
            for it in feed_items:
                if it.url not in seen_urls:
                    seen_urls.add(it.url)
                    discovered.append(it)
            time.sleep(0.5)

        # 2. Run query combinations
        queries = generate_search_queries(max_queries=max_queries)
        for q_meta in queries:
            q = q_meta["query"]
            q_items = search_duckduckgo_public(client, q, max_results=4)
            for it in q_items:
                if it.url not in seen_urls:
                    seen_urls.add(it.url)
                    discovered.append(it)
            time.sleep(delay_between_requests)

    return discovered
