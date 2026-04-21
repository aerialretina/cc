#!/usr/bin/env python3
"""
NYC Startup Sales/GTM Job Scraper

Scrapes Built In NYC, Wellfound, and Work at a Startup (YC), then POSTs
new listings to a Google Apps Script webhook that appends rows to a Sheet.

Usage:
    python scraper.py

Environment:
    SHEETS_WEBHOOK_URL  Google Apps Script web-app URL (dry-run if unset)

First-time setup:
    pip install -r requirements.txt
    playwright install chromium
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sys.exit(
        "playwright not installed.\n"
        "Run: pip install playwright && playwright install chromium"
    )

import requests

# ── Configuration ──────────────────────────────────────────────────────────

SHEETS_WEBHOOK_URL: str = os.environ.get("SHEETS_WEBHOOK_URL", "")
SEEN_JOBS_FILE: Path = Path("seen_jobs.json")
RATE_LIMIT_DELAY: float = 2.0  # seconds between scraper runs and outbound POSTs

# Matches any relevant sales/GTM keyword at a word boundary (case-insensitive)
TITLE_RE = re.compile(
    r"\b("
    r"sales"
    r"|account[\s\-]?executive"
    r"|ae"
    r"|sdr"
    r"|bdr"
    r"|business[\s\-]?development"
    r"|gtm"
    r"|go[\s\-]?to[\s\-]?market"
    r"|revenue"
    r"|partnerships?"
    r"|customer[\s\-]?success"
    r")\b",
    re.IGNORECASE,
)

# Realistic browser UA so sites don't trivially block the headless browser
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


# ── Persistence ────────────────────────────────────────────────────────────

def load_seen() -> dict:
    if SEEN_JOBS_FILE.exists():
        try:
            return json.loads(SEEN_JOBS_FILE.read_text())
        except json.JSONDecodeError:
            print(f"[WARN] {SEEN_JOBS_FILE} is malformed — starting fresh.")
    return {}


def save_seen(seen: dict) -> None:
    SEEN_JOBS_FILE.write_text(json.dumps(seen, indent=2))


def job_key(company: str, title: str) -> str:
    _n = lambda s: re.sub(r"\s+", " ", s.lower().strip())
    return f"{_n(company)}|||{_n(title)}"


# ── Filters ────────────────────────────────────────────────────────────────

def relevant(title: str) -> bool:
    return bool(TITLE_RE.search(title))


# ── robots.txt ─────────────────────────────────────────────────────────────

def robots_ok(base_url: str, target_url: str) -> bool:
    rp = RobotFileParser()
    rp.set_url(urljoin(base_url, "/robots.txt"))
    try:
        rp.read()
        return rp.can_fetch(UA, target_url)
    except Exception:
        return True  # allow if robots.txt is unreachable


# ── Google Sheets POST ─────────────────────────────────────────────────────

def post_row(job: dict) -> bool:
    """POST one job row to the Google Apps Script webhook."""
    row = {k: job[k] for k in ("date", "source", "company", "title", "location", "url")}
    if not SHEETS_WEBHOOK_URL:
        print(f"  [DRY RUN] {row['source']} | {row['company']} | {row['title']}")
        return True
    try:
        resp = requests.post(SHEETS_WEBHOOK_URL, json=row, timeout=30)
        resp.raise_for_status()
        return True
    except Exception as exc:
        print(f"  [POST ERROR] {exc}")
        return False


# ── Playwright DOM helpers ─────────────────────────────────────────────────

async def _txt(el) -> str:
    try:
        return (await el.inner_text()).strip() if el else ""
    except Exception:
        return ""


async def _attr(el, name: str) -> str:
    try:
        return ((await el.get_attribute(name)) or "").strip() if el else ""
    except Exception:
        return ""


async def _first(handle, *selectors: str):
    """Return the first Playwright element matching any CSS selector."""
    for sel in selectors:
        try:
            el = await handle.query_selector(sel)
            if el:
                return el
        except Exception:
            pass
    return None


async def _scroll_load(page, rounds: int = 6, pause_ms: int = 1_200) -> None:
    """Scroll down to trigger infinite-scroll or lazy loading."""
    for _ in range(rounds):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(pause_ms)


# ── Scraper: Built In NYC ──────────────────────────────────────────────────

async def scrape_builtin(page) -> list[dict]:
    """
    builtin.com/jobs filtered to New York + Sales.
    The page is React-rendered; we scroll to trigger lazy-loading of job cards.
    Multiple selector fallbacks guard against CSS class name changes.
    """
    BASE = "https://builtin.com"
    URL = "https://builtin.com/jobs?city=new-york&role=Sales"
    SOURCE = "Built In NYC"

    if not robots_ok(BASE, URL):
        print(f"[{SOURCE}] robots.txt disallows this path — skipping.")
        return []

    jobs: list[dict] = []
    print(f"\n[{SOURCE}] Fetching {URL}")

    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3_000)
        await _scroll_load(page)

        cards = []
        for sel in (
            "[data-id='job-card']",
            "div[class*='JobCard']",
            "article[class*='job']",
            "li[class*='job']",
        ):
            cards = await page.query_selector_all(sel)
            if cards:
                print(f"[{SOURCE}] {len(cards)} cards via {sel!r}")
                break

        if not cards:
            print(f"[{SOURCE}] No job cards found — selectors may need updating.")
            return []

        for card in cards:
            title_el   = await _first(card, "[data-id='job-title']", "[class*='JobTitle']",
                                      "h2[class*='title']", "h2", "h3")
            company_el = await _first(card, "[data-id='company-title']", "[class*='CompanyName']",
                                      "[class*='company-name']", "[class*='employer']")
            link_el    = await _first(card, "a[href*='/job/']", "a")
            loc_el     = await _first(card, "[data-id='location']", "[class*='location']",
                                      "[class*='Location']")
            date_el    = await _first(card, "time", "[datetime]", "[class*='date']")

            title    = await _txt(title_el)
            company  = await _txt(company_el)
            href     = await _attr(link_el, "href")
            location = await _txt(loc_el) or "New York, NY"
            posted   = await _attr(date_el, "datetime") or await _txt(date_el)

            if not title or not company or not relevant(title):
                continue

            jobs.append({
                "date":     str(date.today()),
                "source":   SOURCE,
                "company":  company,
                "title":    title,
                "location": location,
                "url":      urljoin(BASE, href) if href else URL,
                "posted":   posted,
            })

    except PlaywrightTimeout:
        print(f"[{SOURCE}] Page load timed out.")
    except Exception as exc:
        print(f"[{SOURCE}] Error: {exc}")

    print(f"[{SOURCE}] {len(jobs)} relevant jobs.")
    return jobs


# ── Scraper: Wellfound ─────────────────────────────────────────────────────

async def scrape_wellfound(page) -> list[dict]:
    """
    wellfound.com/jobs filtered to Sales + NYC.
    Heavily React-rendered; falls back to an anchor-tag scan when expected
    card structure is absent (e.g. after a site redesign).
    """
    BASE = "https://wellfound.com"
    URL = "https://wellfound.com/jobs?role=Sales&location=New+York+City%2C+NY%2C+USA"
    SOURCE = "Wellfound"

    if not robots_ok(BASE, URL):
        print(f"[{SOURCE}] robots.txt disallows this path — skipping.")
        return []

    jobs: list[dict] = []
    print(f"\n[{SOURCE}] Fetching {URL}")

    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(4_000)
        await _scroll_load(page, rounds=8)

        cards = []
        for sel in (
            "[class*='styles_jobListing']",
            "[class*='JobListing']",
            "[data-test*='job']",
            "div[class*='job-listing']",
            "li[class*='job']",
        ):
            cards = await page.query_selector_all(sel)
            if cards:
                print(f"[{SOURCE}] {len(cards)} cards via {sel!r}")
                break

        # Fallback: walk all job-page anchor tags rendered on the page
        if not cards:
            print(f"[{SOURCE}] No cards — falling back to anchor scan.")
            for link in await page.query_selector_all("a[href*='/jobs/'][href*='-']"):
                title = await _txt(link)
                href  = await _attr(link, "href")
                if not title or not relevant(title):
                    continue
                company = ""
                try:
                    parent_jsh = await link.evaluate_handle(
                        "el => el.closest('[class*=\"company\"], li, article, section')"
                    )
                    parent_el = parent_jsh.as_element()
                    if parent_el:
                        company = await _txt(
                            await parent_el.query_selector("[class*='company'], h2, h3")
                        )
                except Exception:
                    pass
                jobs.append({
                    "date":     str(date.today()),
                    "source":   SOURCE,
                    "company":  company or "Unknown",
                    "title":    title,
                    "location": "New York, NY",
                    "url":      urljoin(BASE, href) if href.startswith("/") else href,
                    "posted":   "",
                })
            print(f"[{SOURCE}] {len(jobs)} jobs (fallback mode).")
            return jobs

        for card in cards:
            title_el   = await _first(card, "a[href*='/jobs/']", "[class*='title']",
                                      "[class*='Title']", "h2", "h3")
            company_el = await _first(card, "[class*='company']", "[class*='Company']",
                                      "[class*='startup']")
            link_el    = await _first(card, "a[href*='/jobs/']")
            loc_el     = await _first(card, "[class*='location']", "[class*='Location']",
                                      "[class*='remote']")

            title    = await _txt(title_el)
            company  = await _txt(company_el)
            href     = await _attr(link_el, "href")
            location = await _txt(loc_el) or "New York, NY"

            if not title or not company or not relevant(title):
                continue

            jobs.append({
                "date":     str(date.today()),
                "source":   SOURCE,
                "company":  company,
                "title":    title,
                "location": location,
                "url":      urljoin(BASE, href) if href.startswith("/") else href or URL,
                "posted":   "",
            })

    except PlaywrightTimeout:
        print(f"[{SOURCE}] Page load timed out.")
    except Exception as exc:
        print(f"[{SOURCE}] Error: {exc}")

    print(f"[{SOURCE}] {len(jobs)} relevant jobs.")
    return jobs


# ── Scraper: Work at a Startup (YC) ───────────────────────────────────────

async def scrape_workatastartup(page) -> list[dict]:
    """
    workatastartup.com filtered to sales + US in-person, sorted by date.
    YC's board is React-rendered. Falls back to anchor scan if card
    selectors don't match. Note: WATS lacks a city-level filter, so results
    span the US; downstream consumers should re-filter on location if needed.
    """
    BASE = "https://www.workatastartup.com"
    URL = (
        "https://www.workatastartup.com/jobs"
        "?role=sales&usa_only=true&remote=no&orderBy=date"
    )
    SOURCE = "Work at a Startup"

    if not robots_ok(BASE, URL):
        print(f"[{SOURCE}] robots.txt disallows this path — skipping.")
        return []

    jobs: list[dict] = []
    print(f"\n[{SOURCE}] Fetching {URL}")

    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(4_000)

        # Bail if we hit a login wall
        if any(kw in page.url.lower() for kw in ("login", "signin", "sign-in")):
            print(f"[{SOURCE}] Redirected to login page — skipping.")
            return []

        await _scroll_load(page, rounds=10, pause_ms=800)

        cards = []
        for sel in (
            ".job-name",
            "[class*='JobRow']",
            "[class*='job-row']",
            "div[class*='JobListing']",
            "li[class*='job']",
        ):
            cards = await page.query_selector_all(sel)
            if len(cards) > 1:
                print(f"[{SOURCE}] {len(cards)} cards via {sel!r}")
                break

        if not cards:
            print(f"[{SOURCE}] No cards — falling back to anchor scan.")
            for link in await page.query_selector_all("a[href*='/jobs/']"):
                title = await _txt(link)
                href  = await _attr(link, "href")
                if not title or len(title) < 3 or not relevant(title):
                    continue
                company  = ""
                location = ""
                try:
                    parent_jsh = await link.evaluate_handle(
                        "el => el.closest('li, article, .job, [class*=\"listing\"]')"
                    )
                    parent_el = parent_jsh.as_element()
                    if parent_el:
                        company  = await _txt(
                            await parent_el.query_selector(
                                "[class*='company'], .company-name, h2, h3"
                            )
                        )
                        location = await _txt(
                            await parent_el.query_selector(
                                "[class*='location'], [class*='city']"
                            )
                        )
                except Exception:
                    pass
                jobs.append({
                    "date":     str(date.today()),
                    "source":   SOURCE,
                    "company":  company or "Unknown",
                    "title":    title,
                    "location": location or "USA",
                    "url":      urljoin(BASE, href) if href.startswith("/") else href,
                    "posted":   "",
                })
            print(f"[{SOURCE}] {len(jobs)} jobs (fallback mode).")
            return jobs

        for card in cards:
            title_el   = await _first(card, "a[href*='/jobs/']", "[class*='title']",
                                      "[class*='role']", "h2", "h3")
            company_el = await _first(card, "[class*='company']", ".company-name",
                                      "[class*='employer']")
            link_el    = await _first(card, "a[href*='/jobs/']", "a")
            loc_el     = await _first(card, "[class*='location']", "[class*='remote']",
                                      "[class*='city']")
            date_el    = await _first(card, "time", "[datetime]", "[class*='date']",
                                      "[class*='posted']")

            title    = await _txt(title_el)
            company  = await _txt(company_el)
            href     = await _attr(link_el, "href")
            location = await _txt(loc_el) or "USA"
            posted   = await _attr(date_el, "datetime") or await _txt(date_el)

            if not title or not relevant(title):
                continue

            jobs.append({
                "date":     str(date.today()),
                "source":   SOURCE,
                "company":  company or "Unknown",
                "title":    title,
                "location": location,
                "url":      urljoin(BASE, href) if href.startswith("/") else href or URL,
                "posted":   posted,
            })

    except PlaywrightTimeout:
        print(f"[{SOURCE}] Page load timed out.")
    except Exception as exc:
        print(f"[{SOURCE}] Error: {exc}")

    print(f"[{SOURCE}] {len(jobs)} relevant jobs.")
    return jobs


# ── Main ───────────────────────────────────────────────────────────────────

async def run() -> None:
    seen = load_seen()
    all_jobs: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            # --no-sandbox required in Docker / CI environments
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )

        for scrape_fn in (scrape_builtin, scrape_wellfound, scrape_workatastartup):
            page = await ctx.new_page()
            try:
                results = await scrape_fn(page)
                all_jobs.extend(results)
            finally:
                await page.close()
            await asyncio.sleep(RATE_LIMIT_DELAY)

        await browser.close()

    # Cross-source dedup: keep first occurrence when same company+title appears
    # on more than one job board
    unique: dict[str, dict] = {}
    for job in all_jobs:
        k = job_key(job["company"], job["title"])
        if k not in unique:
            unique[k] = job

    # Post only jobs not already recorded in seen_jobs.json
    new_count = 0
    for k, job in unique.items():
        if k in seen:
            continue
        print(f"[NEW] {job['source']} | {job['company']} | {job['title']}")
        if post_row(job):
            seen[k] = {
                "company":    job["company"],
                "title":      job["title"],
                "source":     job["source"],
                "first_seen": str(date.today()),
            }
            new_count += 1
        time.sleep(0.5)  # gentle rate-limit on outbound POSTs

    save_seen(seen)
    print(f"\nDone — {len(unique)} unique jobs found, {new_count} new and posted.")


if __name__ == "__main__":
    asyncio.run(run())
