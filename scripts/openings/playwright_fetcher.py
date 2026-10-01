import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

SPA_DOMAINS = [
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "taleo.net",
    "oraclecloud.com",
    "successfactors.eu",
    "successfactors.com",
    "brassring.com",
    "smartrecruiters.com",
    "applytojob.com"
]

def is_spa_portal(url: str) -> bool:
    """Detect if a portal typically relies on client-side JS rendering."""
    low = url.lower()
    return any(domain in low for domain in SPA_DOMAINS)

def fetch_rendered_html(url: str, timeout: float = 15.0) -> Optional[str]:
    """
    Fetch and execute JavaScript to capture rendered DOM from dynamic portals.
    Falls back gracefully to httpx if Playwright is unavailable or fails.
    """
    # 1. Try Playwright headless fetch first if available
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            # Route abort for image and font assets to accelerate rendering
            page = context.new_page()
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                # Brief wait for client-side frameworks to mount
                page.wait_for_timeout(1000)
                html = page.content()
                browser.close()
                if html and len(html) > 500:
                    return html
            except Exception as nav_err:
                browser.close()
                logger.debug(f"Playwright navigation failed for {url}: {nav_err}")
    except (ImportError, Exception) as pw_err:
        logger.debug(f"Playwright launch failed: {pw_err}")

    # 2. Resilient fallback to HTTP request
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception as http_err:
        logger.debug(f"HTTP fallback failed for {url}: {http_err}")

    return None
