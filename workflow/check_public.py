import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import expect, sync_playwright

from check_content import ROOT, WORKFLOW, load, save


def check_site(base):
    results = []
    browser_version = ""
    assets = [
        ("", "index.html"), ("wiki.html", "wiki.html"), ("slides.html", "slides.html"),
    ]
    filenames = [row["file"] for row in load(WORKFLOW / "browser-check.json")["screenshots"]]
    proof = ["clock-check.json", "ingest.json", "content-check.json", "browser-check.json",
             "query.json", "draft-v0.json", "draft-v1.json"]
    paths = [f"evidence/{name}" for name in filenames] + [f"workflow/{name}" for name in proof]
    assets.extend((path, path) for path in paths)

    with sync_playwright() as app:
        browser = app.chromium.launch(channel="chrome")
        browser_version = browser.version
        with browser.new_context(viewport={"width": 1440, "height": 900}) as context:
            assert not context.cookies()
            for path, local_file in assets:
                target = urljoin(base, path)
                response = context.request.get(target, max_redirects=0, timeout=20000)
                assert response.status == 200 and response.url == target, (target, response.status)
                digest = hashlib.sha256(response.body()).hexdigest()
                assert digest == hashlib.sha256((ROOT / local_file).read_bytes()).hexdigest(), target
                results.append({"url": response.url, "status": response.status, "sha256": digest})
                response.dispose()

            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base, wait_until="domcontentloaded")
            page.locator(".actions a[href='slides.html']").click()
            expect(page.locator("#intro")).to_be_visible()
            page.locator("#next").click()
            expect(page.locator("#copy")).to_be_visible()
            page.locator("#slide-select").select_option("quiz")
            for item in page.locator(".quiz").all():
                item.locator("[data-correct=true]").click()
                expect(item.locator(".feedback")).to_contain_text("答對了")
            page.locator("#quiz a[href='wiki.html#K03-match']").click()
            expect(page.locator("#K03-match")).to_be_visible()
            page.locator("#K03-match a[href='#S02-section-15.4.5']").click()
            expect(page.locator("#S02-section-15\\.4\\.5")).to_be_visible()
            assert urlsplit(page.url).fragment == "S02-section-15.4.5"
            expect(page.locator("#wiki-search")).to_be_visible()
            page.locator("#wiki-search").fill("304")
            assert 0 < page.locator(".wiki-card:visible").count() < 10
            assert not errors, errors
        browser.close()

    now = datetime.now(timezone.utc)
    save(WORKFLOW / "public-check.json", {
        "verified_utc": now.isoformat(timespec="seconds"),
        "verified_taipei": now.astimezone(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "base_url": base, "chrome": browser_version, "anonymous_context": True,
        "pages_and_assets": results, "navigation_quizzes_wiki": "pass",
    })
    print(f"Verified {len(results)} public HTTP 200 URLs and file hashes, plus anonymous Chrome interaction.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    args = parser.parse_args()
    check_site(args.base.rstrip("/") + "/")
