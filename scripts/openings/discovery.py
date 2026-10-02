import time
import re
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup

from .models import DiscoveredItem
from .config import load_research_profile, COUNTRY_TO_REGION

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
        "name": "EURAXESS Jobs (Page 3)",
        "url": "https://euraxess.ec.europa.eu/job-feed?page=3",
        "type": "euraxess"
    },
    {
        "name": "EURAXESS Jobs (Page 4)",
        "url": "https://euraxess.ec.europa.eu/job-feed?page=4",
        "type": "euraxess"
    },
    {
        "name": "OpenRobotics ROS Discourse",
        "url": "https://discourse.ros.org/c/jobs.rss",
        "type": "official_rss"
    }
]

US_STATES = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"}

CITY_TO_COUNTRY_REGION = {
    # UAE
    "abu dhabi": ("Abu Dhabi", "UAE", "Middle East"),
    "dubai": ("Dubai", "UAE", "Middle East"),
    "sharjah": ("Sharjah", "UAE", "Middle East"),
    "ajman": ("Ajman", "UAE", "Middle East"),
    # Saudi Arabia
    "riyadh": ("Riyadh", "Saudi Arabia", "Middle East"),
    "thuwal": ("Thuwal", "Saudi Arabia", "Middle East"),
    "dhahran": ("Dhahran", "Saudi Arabia", "Middle East"),
    "jeddah": ("Jeddah", "Saudi Arabia", "Middle East"),
    "al khobar": ("Al Khobar", "Saudi Arabia", "Middle East"),
    "dammam": ("Dammam", "Saudi Arabia", "Middle East"),
    "makkah": ("Makkah", "Saudi Arabia", "Middle East"),
    # Switzerland
    "zurich": ("Zurich", "Switzerland", "Europe"),
    "zürich": ("Zurich", "Switzerland", "Europe"),
    "lausanne": ("Lausanne", "Switzerland", "Europe"),
    "geneva": ("Geneva", "Switzerland", "Europe"),
    # Germany
    "munich": ("Munich", "Germany", "Europe"),
    "münchen": ("Munich", "Germany", "Europe"),
    "berlin": ("Berlin", "Germany", "Europe"),
    "stuttgart": ("Stuttgart", "Germany", "Europe"),
    "tübingen": ("Tübingen", "Germany", "Europe"),
    "tubingen": ("Tübingen", "Germany", "Europe"),
    "heidelberg": ("Heidelberg", "Germany", "Europe"),
    "aachen": ("Aachen", "Germany", "Europe"),
    "karlsruhe": ("Karlsruhe", "Germany", "Europe"),
    # Netherlands
    "delft": ("Delft", "Netherlands", "Europe"),
    "amsterdam": ("Amsterdam", "Netherlands", "Europe"),
    "eindhoven": ("Eindhoven", "Netherlands", "Europe"),
    "enschede": ("Enschede", "Netherlands", "Europe"),
    "wageningen": ("Wageningen", "Netherlands", "Europe"),
    "utrecht": ("Utrecht", "Netherlands", "Europe"),
    # France
    "paris": ("Paris", "France", "Europe"),
    "grenoble": ("Grenoble", "France", "Europe"),
    "rennes": ("Rennes", "France", "Europe"),
    "lyon": ("Lyon", "France", "Europe"),
    # Sweden & Finland
    "stockholm": ("Stockholm", "Sweden", "Europe"),
    "gothenburg": ("Gothenburg", "Sweden", "Europe"),
    "linköping": ("Linköping", "Sweden", "Europe"),
    "helsinki": ("Helsinki", "Finland", "Europe"),
    "tampere": ("Tampere", "Finland", "Europe"),
    # UK
    "london": ("London", "UK", "UK"),
    "oxford": ("Oxford", "UK", "UK"),
    "cambridge": ("Cambridge", "UK", "UK"),
    "edinburgh": ("Edinburgh", "UK", "UK"),
    "bristol": ("Bristol", "UK", "UK"),
}

def parse_linkedin_location(loc_str: str) -> Tuple[str, str, str]:
    """Parse city, country, and macro-region from LinkedIn location strings."""
    if not loc_str:
        return "Not specified", "Not specified", "Europe"
    
    loc_lower = loc_str.lower()
    for city_key, (c_name, country_name, reg_name) in CITY_TO_COUNTRY_REGION.items():
        if city_key in loc_lower:
            return c_name, country_name, reg_name

    parts = [p.strip() for p in loc_str.split(",")]
    city = parts[0] if parts else "Not specified"
    country = "Not specified"

    if "united arab emirates" in loc_lower or "uae" in loc_lower or "emirates" in loc_lower:
        return city, "UAE", "Middle East"
    if "saudi arabia" in loc_lower or "saudi" in loc_lower or "ksa" in loc_lower:
        return city, "Saudi Arabia", "Middle East"

    last_part = parts[-1].strip()
    if last_part in US_STATES or last_part in ["United States", "USA", "US"]:
        country = "USA"
    elif "United Kingdom" in loc_str or "UK" in parts or "England" in parts or "Scotland" in parts:
        country = "UK"
    else:
        for c in COUNTRY_TO_REGION.keys():
            if c.lower() in loc_lower:
                country = c
                break
    region = COUNTRY_TO_REGION.get(country, "Europe" if country == "Not specified" else "Europe")
    return city, country, region

LINKEDIN_ACADEMIC_QUERIES = [
    "postdoctoral robotics",
    "phd robotics",
    "postdoc robot learning",
    "embodied ai research",
    "world models robotics",
    "computer vision postdoc",
    "phd computer vision",
    "robot manipulation research",
    "vision language action robotics",
    "spatial intelligence robotics",
    "3d computer vision research",
    "postdoctoral researcher machine learning",
    "phd student machine learning",
    "postdoctoral fellow reinforcement learning",
    "phd robot learning",
    "research scientist embodied ai",
    "research scientist robotics",
    "postdoc autonomous systems",
    "research fellow robotics",
    "doctoral candidate computer vision"
]

LINKEDIN_REGIONAL_TARGETS = [
    # United Arab Emirates
    ("postdoctoral", "United Arab Emirates"),
    ("research scientist", "United Arab Emirates"),
    ("robotics", "United Arab Emirates"),
    ("computer vision", "United Arab Emirates"),
    ("MBZUAI", "United Arab Emirates"),
    ("New York University Abu Dhabi", "United Arab Emirates"),
    ("Technology Innovation Institute", "United Arab Emirates"),
    ("Khalifa University", "United Arab Emirates"),
    ("world models", "United Arab Emirates"),
    # Saudi Arabia
    ("postdoctoral", "Saudi Arabia"),
    ("research scientist", "Saudi Arabia"),
    ("robotics", "Saudi Arabia"),
    ("computer vision", "Saudi Arabia"),
    ("KAUST", "Saudi Arabia"),
    ("KFUPM", "Saudi Arabia"),
    # European Hubs
    ("robotics", "Munich, Germany"),
    ("robot learning", "Munich, Germany"),
    ("computer vision", "Munich, Germany"),
    ("computer vision", "Delft, Netherlands"),
    ("robotics", "Paris, France"),
    ("robot learning", "London, United Kingdom"),
    ("robotics", "London, United Kingdom"),
    ("robotics", "Stockholm, Sweden")
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
    },
    {
        "title": "PhD & Postdoctoral Fellowships in Machine Learning and Computer Vision",
        "url": "https://mbzuai.ac.ae/study/phd-programs/",
        "source_name": "MBZUAI",
        "position_type": "PhD"
    },
    {
        "title": "Post-Doctoral Associate & Research Scientist in Computer Science and Robotics",
        "url": "https://nyuad.nyu.edu/en/academics/divisions/science/faculty/computer-science.html",
        "source_name": "NYU Abu Dhabi",
        "position_type": "Postdoc"
    },
    {
        "title": "Research Scientist & Robotics Engineer in Autonomous Systems and World Models",
        "url": "https://www.tii.ae/",
        "source_name": "Technology Innovation Institute (TII)",
        "position_type": "Research Scientist"
    },
    {
        "title": "Postdoctoral Fellowships and PhD Openings in Visual Computing and AI",
        "url": "https://vcc.kaust.edu.sa/",
        "source_name": "KAUST Visual Computing Center",
        "position_type": "Postdoc"
    },
    {
        "title": "Postdoctoral Research Fellow in Computer Vision and Deep Learning",
        "url": "https://opra.kaust.edu.sa/postdocs/prospective",
        "source_name": "KAUST (OPRA)",
        "position_type": "Postdoc"
    },
    {
        "title": "PhD and Postdoc Positions in Autonomous Mobile Robotics and Perception",
        "url": "https://asl.ethz.ch/",
        "source_name": "ETH Zürich (ASL)",
        "position_type": "PhD"
    },
    {
        "title": "PhD & Postdoc Positions in Legged Robotics and Dexterous Manipulation",
        "url": "https://rsl.ethz.ch/",
        "source_name": "ETH Zürich (RSL)",
        "position_type": "PhD"
    },
    {
        "title": "Doctoral and Postdoctoral Positions in 3D Computer Vision and Spatial AI",
        "url": "https://cvg.ethz.ch/",
        "source_name": "ETH Zürich (CVG)",
        "position_type": "Postdoc"
    },
    {
        "title": "PhD & Postdoctoral Positions in Robot Learning and Control",
        "url": "https://www.epfl.ch/labs/lasa/",
        "source_name": "EPFL (LASA)",
        "position_type": "PhD"
    },
    {
        "title": "Postdoc and PhD Positions in Deep Learning and Computer Vision",
        "url": "https://www.epfl.ch/labs/cvlab/",
        "source_name": "EPFL (CVLab)",
        "position_type": "Postdoc"
    },
    {
        "title": "Doctoral Researcher & Postdoc Openings in Visual SLAM and 3D Perception",
        "url": "https://cvg.cit.tum.de/",
        "source_name": "TU Munich (Cremers Lab)",
        "position_type": "Doctoral Researcher"
    },
    {
        "title": "Postdoctoral Fellowships in Autonomous Systems and Robot Learning",
        "url": "https://is.mpg.de/jobs",
        "source_name": "Max Planck Institute for Intelligent Systems",
        "position_type": "Postdoc"
    },
    {
        "title": "PhD & Postdoctoral Positions in Cognitive Robotics and Robot Learning",
        "url": "https://www.tudelft.nl/3me/over-de-faculteit/afdelingen/cognitive-robotics-cor",
        "source_name": "TU Delft (Cognitive Robotics)",
        "position_type": "PhD"
    },
    {
        "title": "Postdoctoral Research Assistant in Autonomous Robot Navigation and Learning",
        "url": "https://ori.ox.ac.uk/",
        "source_name": "Oxford Robotics Institute",
        "position_type": "Postdoc"
    },
    {
        "title": "Research Associate & PhD Positions in Robot Learning and Dexterity",
        "url": "https://www.imperial.ac.uk/robot-intelligence/",
        "source_name": "Imperial College London",
        "position_type": "Research Associate"
    },
    {
        "title": "Doctoral and Postdoc Openings in Robotics, Perception, and Learning",
        "url": "https://www.kth.se/is/rpl",
        "source_name": "KTH Royal Institute of Technology",
        "position_type": "PhD"
    },
    {
        "title": "Postdoctoral and PhD Fellowships in Robotics and Computer Vision",
        "url": "https://www.inria.fr/en/join-inria",
        "source_name": "Inria",
        "position_type": "Postdoc"
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
    """Strip extraneous whitespace, HTML artefacts, and convert dashes."""
    if not text:
        return ""
    text = text.replace("—", " - ").replace("–", " - ")
    text = re.sub(r'<[^>]+>', ' ', text)
    return " ".join(text.split()).strip()

def search_linkedin_guest(client: httpx.Client, max_queries: int = 10, max_pages_per_query: int = 2) -> List[DiscoveredItem]:
    """
    Search LinkedIn's public guest job postings endpoint for authentic academic,
    laboratory, and institutional research openings.
    """
    items = []
    seen = set()
    for q in LINKEDIN_ACADEMIC_QUERIES[:max_queries]:
        kw = urllib.parse.quote_plus(q)
        for p in range(max_pages_per_query):
            start = p * 10
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw}&start={start}"
            try:
                resp = client.get(url, timeout=10.0)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                jobs = soup.select("li")
                if not jobs:
                    break
                for li in jobs:
                    t_el = li.select_one("h3.base-search-card__title")
                    c_el = li.select_one("h4.base-search-card__subtitle")
                    l_el = li.select_one(".job-search-card__location")
                    a_el = li.select_one("a.base-card__full-link")
                    if not t_el or not a_el:
                        continue
                    job_url = a_el["href"].split("?")[0]
                    if job_url in seen:
                        continue
                    seen.add(job_url)

                    title = clean_text(t_el.get_text())
                    comp = clean_text(c_el.get_text()) if c_el else "Research Institution"
                    raw_loc = clean_text(l_el.get_text()) if l_el else ""
                    city, country, region = parse_linkedin_location(raw_loc)

                    snippet = f"{title} at {comp}. Location: {raw_loc}. Public research opening tracked via LinkedIn academic search."

                    items.append(DiscoveredItem(
                        title=title,
                        url=job_url,
                        source_name=f"LinkedIn ({comp})",
                        source_type="linkedin",
                        snippet=snippet,
                        detected_institution=comp,
                        detected_city=city,
                        detected_country=country,
                        detected_region=region
                    ))
                time.sleep(0.3)
            except Exception:
                break
    return items

def search_linkedin_regional(client: httpx.Client, targets: Optional[List[Tuple[str, str]]] = None) -> List[DiscoveredItem]:
    """
    Search LinkedIn guest API specifically across targeted geographies
    including UAE, Saudi Arabia, and premier European academic hubs.
    """
    if targets is None:
        targets = LINKEDIN_REGIONAL_TARGETS
    items = []
    seen = set()
    for kw, loc in targets:
        encoded_kw = urllib.parse.quote_plus(kw)
        encoded_loc = urllib.parse.quote_plus(loc)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_kw}&location={encoded_loc}&start=0"
        try:
            resp = client.get(url, timeout=10.0)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            jobs = soup.select("li")
            for li in jobs:
                t_el = li.select_one("h3.base-search-card__title")
                c_el = li.select_one("h4.base-search-card__subtitle")
                l_el = li.select_one(".job-search-card__location")
                a_el = li.select_one("a.base-card__full-link")
                if not t_el or not a_el:
                    continue
                job_url = a_el["href"].split("?")[0]
                if job_url in seen:
                    continue
                seen.add(job_url)

                title = clean_text(t_el.get_text())
                comp = clean_text(c_el.get_text()) if c_el else "Research Institution"
                raw_loc = clean_text(l_el.get_text()) if l_el else loc
                city, country, region = parse_linkedin_location(raw_loc)

                snippet = f"{title} at {comp}. Location: {raw_loc}. Regional research opportunity."

                items.append(DiscoveredItem(
                    title=title,
                    url=job_url,
                    source_name=f"LinkedIn ({comp})",
                    source_type="linkedin",
                    snippet=snippet,
                    detected_institution=comp,
                    detected_city=city,
                    detected_country=country,
                    detected_region=region
                ))
            time.sleep(0.3)
        except Exception:
            pass
    return items

def fetch_jobs_ac_uk(client: httpx.Client, keywords: Optional[List[str]] = None) -> List[DiscoveredItem]:
    """Fetch academic research positions from jobs.ac.uk."""
    if keywords is None:
        keywords = ["robotics", "computer vision", "robot learning", "physical ai"]
    items = []
    seen = set()
    for kw in keywords:
        q = urllib.parse.quote_plus(kw)
        url = f"https://www.jobs.ac.uk/search/?keywords={q}"
        try:
            resp = client.get(url, timeout=12.0)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href*='/job/']"):
                href = a.get("href", "")
                title = clean_text(a.text)
                if not title or not href:
                    continue
                job_url = "https://www.jobs.ac.uk" + href if href.startswith("/") else href
                if job_url in seen:
                    continue
                seen.add(job_url)

                parent = a.find_parent("div", class_="j-search-result__text") or a.find_parent("div")
                text_snippet = clean_text(parent.get_text(separator=" ", strip=True)) if parent else title
                
                employer_el = parent.select_one(".employer") if parent else None
                inst = clean_text(employer_el.get_text()) if employer_el else "UK Academic Institution"

                items.append(DiscoveredItem(
                    title=title,
                    url=job_url,
                    source_name=f"jobs.ac.uk ({inst})",
                    source_type="official_university",
                    snippet=text_snippet[:1500],
                    detected_institution=inst,
                    detected_country="UK",
                    detected_region="UK"
                ))
            time.sleep(0.3)
        except Exception:
            pass
    return items

def fetch_academictransfer(client: httpx.Client, keywords: Optional[List[str]] = None) -> List[DiscoveredItem]:
    """Fetch Dutch academic university research positions from AcademicTransfer."""
    if keywords is None:
        keywords = ["robotics", "computer vision", "robot learning", "autonomous systems"]
    items = []
    seen = set()
    for kw in keywords:
        q = urllib.parse.quote_plus(kw)
        url = f"https://www.academictransfer.com/en/jobs/?q={q}"
        try:
            resp = client.get(url, timeout=12.0)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href*='/jobs/']"):
                href = a.get("href", "")
                if not href.startswith("/en/jobs/") or len(href.split("/")) <= 4:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                job_url = "https://www.academictransfer.com" + href

                container = a.find_parent("div", class_="grid") or a.parent
                raw_snippet = clean_text(container.get_text(separator=" ", strip=True)) if container else ""
                
                slug_part = [s for s in href.split("/") if s and not s.isdigit() and s != "en" and s != "jobs"]
                slug_title = slug_part[-1].replace("-", " ").capitalize() if slug_part else "Research Position"
                title = clean_text(slug_title)
                
                items.append(DiscoveredItem(
                    title=title,
                    url=job_url,
                    source_name="AcademicTransfer (Netherlands)",
                    source_type="official_university",
                    snippet=raw_snippet[:1500] if raw_snippet else f"{title} at Dutch Research University.",
                    detected_institution="Dutch Universities",
                    detected_city="Delft / Amsterdam",
                    detected_country="Netherlands",
                    detected_region="Europe"
                ))
            time.sleep(0.3)
        except Exception:
            pass
    return items

def run_discovery(max_queries: int = 15, delay_between_requests: float = 1.0) -> List[DiscoveredItem]:
    """
    Main discovery orchestrator.
    Gathers items across curated lab targets, regional LinkedIn jobs (UAE, Saudi, EU),
    academic aggregators (jobs.ac.uk, AcademicTransfer, EURAXESS), and public search.
    """
    discovered = []
    seen_urls = set()
    
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        # 1. Fetch curated research lab targets (Europe, UAE, Saudi, Asia-Pacific, USA)
        lab_items = fetch_curated_labs(client)
        for it in lab_items:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 2. Fetch LinkedIn public academic jobs (General queries)
        linkedin_items = search_linkedin_guest(client, max_queries=15, max_pages_per_query=2)
        for it in linkedin_items:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 3. Fetch LinkedIn regional targets (UAE, Saudi Arabia, European hubs)
        regional_li_items = search_linkedin_regional(client)
        for it in regional_li_items:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 4. Fetch jobs.ac.uk UK academic openings
        jobs_uk = fetch_jobs_ac_uk(client)
        for it in jobs_uk:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 5. Fetch AcademicTransfer Dutch university openings
        jobs_nl = fetch_academictransfer(client)
        for it in jobs_nl:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                discovered.append(it)

        # 6. Fetch academic RSS feeds (EURAXESS, OpenRobotics)
        for feed in ACADEMIC_FEEDS:
            feed_items = fetch_rss_feed(client, feed)
            for it in feed_items:
                if it.url not in seen_urls:
                    seen_urls.add(it.url)
                    discovered.append(it)
            time.sleep(0.3)

        # 7. Run query combinations
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
