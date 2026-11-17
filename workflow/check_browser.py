"""Exercise the offline HTML and a browser cache example in Chrome.

Install Playwright for Python and have Chrome installed. Run from any directory.
Pass --capture to save representative screenshots outside the deliverable.
"""

import argparse
import binascii
import hashlib
import json
import platform
import struct
import threading
import time
import zlib
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from check_content import ROOT, WORKFLOW, load, save


class PageLinks(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, attrs["id"]
            self.ids.add(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


def check_links():
    pages = {path.name: PageLinks(path) for path in ROOT.glob("*.html")}
    assert set(pages) == {"index.html", "slides.html", "wiki.html"}
    count = 0
    for page, info in pages.items():
        for href in info.links:
            parsed = urlsplit(href)
            if parsed.scheme:
                continue
            if parsed.path and parsed.path not in pages:
                assert parsed.path.startswith("evidence/") and (ROOT / parsed.path).is_file(), href
                count += 1
                continue
            dest = pages[parsed.path or page]
            assert not parsed.fragment or parsed.fragment in dest.ids, (page, href)
            count += 1
    return count


def png(red, green, blue):
    def chunk(name, data):
        return (struct.pack(">I", len(data)) + name + data
                + struct.pack(">I", binascii.crc32(name + data)))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes([0, red, green, blue]))) + chunk(b"IEND", b""))


def check_cache(browser):
    requests = []
    versions = {1: png(200, 100, 50), 2: png(50, 150, 200)}
    state = {"version": 1}
    max_age = 2

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_GET(self):
            if urlsplit(self.path).path != "/poster.png":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b'<!doctype html><img src="/poster.png" alt="poster">')
                return

            tag = f'"poster-v{state["version"]}"'
            supplied = self.headers.get("If-None-Match")
            matched = supplied == tag
            status = 304 if matched else 200
            data = b"" if matched else versions[state["version"]]
            self.send_response(status)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", f"max-age={max_age}")
            self.send_header("ETag", tag)
            if not matched:
                self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            requests.append({"if_none_match": supplied, "etag": tag, "status": status,
                             "body_bytes": len(data)})
            if data:
                self.wfile.write(data)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        context = browser.new_context()
        try:
            page = context.new_page()
            observations = []
            for i, phase in enumerate(("first", "fresh", "expired_same", "expired_changed"), 1):
                if i >= 3:
                    if i == 4:
                        state["version"] = 2
                    time.sleep(max_age + .35)
                before = len(requests)
                page.goto(f"http://127.0.0.1:{server.server_port}/visit-{i}")
                assert page.locator("img").evaluate("(img) => img.complete && img.naturalWidth === 1")
                events = requests[before:]
                observations.append({"phase": phase, "network": events})
            assert [len(o["network"]) for o in observations] == [1, 0, 1, 1], observations
            assert [r["status"] for r in requests] == [200, 304, 200], requests
            assert requests[1]["if_none_match"] == requests[2]["if_none_match"] == '"poster-v1"'
            assert requests[1]["body_bytes"] == 0 and requests[2]["etag"] == '"poster-v2"'
            return {"max_age": max_age, "visits": observations}
        finally:
            context.close()
            server.shutdown()
            worker.join()


def check_deck(browser, capture):
    slides = load(WORKFLOW / "draft-v1.json")
    results = []
    for width, height in [(1440, 900), (1280, 720), (390, 844), (320, 760)]:
        page = browser.new_page(viewport={"width":width, "height":height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "slides.html").as_uri())
        expect(page.locator("#previous")).to_be_disabled()
        for i, slide in enumerate(slides):
            if i:
                page.locator("#next").click()
            active = page.locator("section.slide:visible")
            expect(active).to_have_count(1)
            assert active.get_attribute("id") == slide["id"]
            expect(page.locator("#page-count")).to_have_text(f"{i+1:02} / {len(slides):02}")
            size = page.evaluate("""() => {
              const d = document.documentElement;
              const s = document.querySelector('.slide:not([hidden])');
              return [d.scrollWidth, d.clientWidth, d.scrollHeight, d.clientHeight, s.scrollWidth, s.clientWidth];
            }""")
            assert size[0] <= size[1] and size[4] <= size[5], (slide["id"], width, size)
            if width >= 1280:
                assert size[2] <= size[3], (slide["id"], width, size)
            for link in active.locator(".citations a").all():
                assert link.get_attribute("href").startswith("wiki.html#K")
            if capture and (width, slide["id"]) in {
                (1440,"intro"), (1440,"fresh"), (1440,"validate"), (1440,"quiz"), (390,"validate")
            }:
                page.screenshot(path=str(capture / f"deck-{width}-{slide['id']}.png"))
        expect(page.locator("#next")).to_be_disabled()
        page.locator("#page-count").click()
        page.keyboard.press("Home")
        expect(page.locator("#intro")).to_be_visible()
        page.keyboard.press("ArrowRight")
        expect(page.locator("#copy")).to_be_visible()
        page.keyboard.press("ArrowLeft")
        expect(page.locator("#intro")).to_be_visible()
        page.locator("#slide-select").select_option("quiz")
        expect(page.locator("#quiz")).to_be_visible()
        for quiz in page.locator(".quiz").all():
            quiz.locator("[data-correct=false]").click()
            expect(quiz.locator(".feedback")).to_contain_text("再想想")
            quiz.locator("[data-correct=true]").click()
            expect(quiz.locator(".feedback")).to_contain_text("答對了")
        if capture and width == 1440:
            page.screenshot(path=str(capture / "deck-1440-quiz-feedback.png"))
        for href in ["wiki.html#K03-match", "wiki.html#K04-validate"]:
            page.locator(f"#quiz [href='{href}']").click()
            assert page.url.endswith(href)
            expect(page.locator(href.split(".html")[1])).to_be_visible()
            page.go_back()
            expect(page.locator("#quiz")).to_be_visible()
        assert not errors, errors
        results.append({"width":width, "height":height, "slides":len(slides)})
        page.close()
    return results


def check_wiki_report(browser, capture):
    for width, height in [(1440, 900), (390, 844)]:
        page = browser.new_page(viewport={"width":width, "height":height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri())
        expect(page.locator("h1")).to_contain_text("HTTP 快取入門")
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        if capture and width == 1440:
            page.screenshot(path=str(capture / "report.png"), full_page=True)
        page.locator(".actions a[href='wiki.html']").click()
        expect(page.locator(".wiki-card:visible")).to_have_count(10)
        if capture and width == 1440:
            page.screenshot(path=str(capture / "wiki.png"))
        page.locator("#wiki-search").fill("304")
        count = page.locator(".wiki-card:visible").count()
        assert 0 < count < 10
        page.locator("#wiki-search").fill("nonexistent_entry")
        expect(page.locator("#no-result")).to_be_visible()
        page.locator(".side a[href='#K05']").click()
        expect(page.locator("#K05")).to_be_visible()
        page.locator("#K05 a[href='#S05-headers']").click()
        expect(page.locator("#S05-headers")).to_be_visible()
        assert page.url.endswith("#S05-headers") and not errors
        if capture and width == 1440:
            page.screenshot(path=str(capture / "wiki-origin-link.png"))
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        page.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    opts = parser.parse_args()
    if opts.capture:
        opts.capture.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    with sync_playwright() as app:
        browser = app.chromium.launch(channel="chrome")
        sizes = check_deck(browser, opts.capture)
        check_wiki_report(browser, opts.capture)
        trace = check_cache(browser)
        finished = datetime.now(timezone.utc)
        local_links = check_links()
        screenshots = []
        if opts.capture:
            for filename in sorted(opts.capture.glob("*.png")):
                file_bytes = filename.read_bytes()
                screenshots.append({"file": filename.name, "bytes": len(file_bytes),
                                    "sha256": hashlib.sha256(file_bytes).hexdigest()})
        result = {
            "started_utc": started.isoformat(timespec="seconds"),
            "finished_utc": finished.isoformat(timespec="seconds"),
            "finished_taipei": finished.astimezone(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
            "os": platform.system(), "browser_channel": "chrome",
            "chrome": browser.version, "local_links": local_links, "viewports": sizes,
            "deck_controls": "pass", "quizzes": "pass", "wiki_search_and_links": "pass",
            "screenshots": screenshots,
            "html_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                            for name in ("index.html", "wiki.html", "slides.html")},
            "cache_example": trace
        }
        browser.close()
    save(WORKFLOW / "browser-check.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
