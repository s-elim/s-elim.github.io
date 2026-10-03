"""Open course routes in headless Chromium, report console errors, save screenshots.

INPUT   a base URL serving the site root (python -m http.server from the repo root)
PROCESS for each route: load, wait for labs to start, scroll through the page so
        lazily mounted labs mount, optionally press Play, collect console messages
OUTPUT  screenshots in --out and a non-zero exit status if any page logged an error

Usage:
  python tools/browser_check.py --base http://127.0.0.1:8765/learn/mujoco/ \
      --routes "#/" "#/lesson/0.1" "#/playground" --out /tmp/shots

Needs Playwright and a Chromium build. On machines without system graphics
libraries, pass --chrome to a headless-shell binary and set LD_LIBRARY_PATH;
WebGL then runs on SwiftShader (--use-angle=swiftshader).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--routes", nargs="+", default=["#/"])
    ap.add_argument("--out", type=Path, default=Path("shots"))
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--wait", type=int, default=6000, help="ms to wait for WASM and labs")
    ap.add_argument("--play", action="store_true", help="click every Play button and run for a while")
    ap.add_argument("--dark", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    with sync_playwright() as p:
        launch = {"args": ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]}
        if args.chrome:
            launch["executable_path"] = args.chrome
        browser = p.chromium.launch(**launch)
        ctx = browser.new_context(viewport={"width": args.width, "height": args.height},
                                  color_scheme="dark" if args.dark else "light")
        for route in args.routes:
            page = ctx.new_page()
            logs: list[str] = []
            page.on("console", lambda m, logs=logs: logs.append(f"{m.type}: {m.text}"))
            page.on("pageerror", lambda e, logs=logs: logs.append(f"pageerror: {e}"))
            page.goto(args.base + route, wait_until="networkidle")
            page.wait_for_timeout(args.wait)
            # Scroll through the page so lazily mounted labs start.
            height = page.evaluate("document.body.scrollHeight")
            for y in range(0, height, 700):
                page.evaluate(f"window.scrollTo(0, {y})")
                page.wait_for_timeout(250)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(args.wait // 2)
            if args.play:
                for btn in page.query_selector_all("button.btn--primary"):
                    if "Play" in (btn.inner_text() or ""):
                        try:
                            btn.click(timeout=2000)
                        except Exception:  # noqa: BLE001 - off-screen buttons are fine to skip
                            pass
                page.wait_for_timeout(3000)
            name = route.strip("#/").replace("/", "_") or "home"
            page.screenshot(path=str(args.out / f"{name}.png"), full_page=False)
            page.screenshot(path=str(args.out / f"{name}_full.png"), full_page=True)
            errors = [l for l in logs if l.startswith(("error", "pageerror"))]
            print(f"== {route}: {len(logs)} console messages, {len(errors)} errors")
            for line in logs:
                print("   ", line[:300])
            failures += bool(errors)
            page.close()
        browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
