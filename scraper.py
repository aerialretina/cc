#!/usr/bin/env python3
"""
NYC Startup Sales/GTM Job Scraper

Scrapes Built In NYC, Wellfound, Work at a Startup (YC), Otta, Indeed,
and LinkedIn (via Google dorking), then POSTs new listings to a Google
Apps Script webhook that appends rows to a Sheet.

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
from urllib.parse import urljoin, unquote
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


# ── Google-result helpers ──────────────────────────────────────────────────

def _decode_google_href(href: str) -> str:
    """Extract the real URL from a Google /url?q=<actual> redirect href.
    Handles both plain (https://) and percent-encoded (https%3A%2F%2F) forms.
    """
    if not href:
        return ""
    if href.startswith("https://www.linkedin.com"):
        return href
    # Match q= value up to the next & or end-of-string; covers encoded URLs too
    m = re.search(r"[?&]q=(https?(?:%3A|:).+?)(?:&|$)", href, re.IGNORECASE)
    return unquote(m.group(1)) if m else href


def _parse_linkedin_title(raw: str) -> tuple[str, str]:
    """
    Return (job_title, company) from a LinkedIn Google-result title.
    Handles three common formats:
      "Account Executive at Acme Corp | LinkedIn"
      "Senior SDR | Acme Corp | LinkedIn"
      "Sales Manager - New York, NY | LinkedIn"
    """
    text = re.sub(r"\s*\|\s*LinkedIn\s*$", "", raw, flags=re.IGNORECASE).strip()
    # "Title at Company"
    m = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # "Title | Company"
    parts = [p.strip() for p in text.split("|")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    # "Title - location …" — company unknown
    return re.split(r"\s+[-–]\s+", text)[0].strip(), ""


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

    DOM structure: jobs are grouped *under* company blocks — the company
    name sits in an a[href*='/companies/'] link that is a PARENT of the
    individual job entries, not inside them.  We anchor on those company
    links, walk up to the nearest ancestor that also holds job links, then
    collect every matching job within that container.
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

        if any(kw in page.url.lower() for kw in ("login", "signin", "sign-in")):
            print(f"[{SOURCE}] Redirected to login page — skipping.")
            return []

        await _scroll_load(page, rounds=10, pause_ms=800)

        company_links = await page.query_selector_all("a[href*='/companies/']")
        if not company_links:
            print(f"[{SOURCE}] No company links found — page may not have loaded.")
            return []

        print(f"[{SOURCE}] {len(company_links)} company blocks found.")
        seen_containers: set[str] = set()

        for co_link in company_links:
            company = await _txt(co_link)
            if not company:
                continue

            # Walk up to the nearest ancestor that also contains a job link.
            # Company name is always above the job entries in the DOM.
            container_jsh = await co_link.evaluate_handle("""el => {
                let node = el.parentElement;
                while (node && node.tagName !== 'BODY') {
                    if (node.querySelector('a[href*="/jobs/"]')) return node;
                    node = node.parentElement;
                }
                return null;
            }""")
            container_el = container_jsh.as_element()
            if not container_el:
                continue

            # Deduplicate: the same container element can hold several
            # /companies/ links (e.g. logo + name); skip if already visited.
            try:
                fingerprint = f"{company}||" + await container_el.evaluate(
                    "el => el.className + String(el.childElementCount)"
                )
            except Exception:
                fingerprint = company
            if fingerprint in seen_containers:
                continue
            seen_containers.add(fingerprint)

            for job_link in await container_el.query_selector_all("a[href*='/jobs/']"):
                title = await _txt(job_link)
                href  = await _attr(job_link, "href")
                if not title or not relevant(title):
                    continue

                # Location lives near the job link, not in the company header
                location = ""
                try:
                    parent_jsh = await job_link.evaluate_handle("el => el.parentElement")
                    parent_el  = parent_jsh.as_element()
                    if parent_el:
                        loc_el = await _first(
                            parent_el,
                            "[class*='location']", "[class*='city']", "[class*='remote']",
                        )
                        location = await _txt(loc_el)
                except Exception:
                    pass

                posted = ""
                try:
                    date_jsh = await job_link.evaluate_handle(
                        "el => el.closest('li,div,article')"
                        "?.querySelector('time,[datetime]')"
                    )
                    date_el = date_jsh.as_element()
                    if date_el:
                        posted = await _attr(date_el, "datetime") or await _txt(date_el)
                except Exception:
                    pass

                jobs.append({
                    "date":     str(date.today()),
                    "source":   SOURCE,
                    "company":  company,
                    "title":    title,
                    "location": location or "USA",
                    "url":      urljoin(BASE, href) if href.startswith("/") else href or URL,
                    "posted":   posted,
                })

    except PlaywrightTimeout:
        print(f"[{SOURCE}] Page load timed out.")
    except Exception as exc:
        print(f"[{SOURCE}] Error: {exc}")

    print(f"[{SOURCE}] {len(jobs)} relevant jobs.")
    return jobs


# ── Scraper: Otta ─────────────────────────────────────────────────────────

async def scrape_otta(page) -> list[dict]:
    """
    app.otta.com — sales/GTM roles in NYC.
    React-rendered; may gate full results behind login.  We try the public
    search endpoint and bail gracefully on a login wall.
    """
    BASE = "https://app.otta.com"
    URL = (
        "https://app.otta.com/jobs/search"
        "?functions=Sales&locationPreferences=new-york-city-area"
    )
    SOURCE = "Otta"

    if not robots_ok(BASE, URL):
        print(f"[{SOURCE}] robots.txt disallows this path — skipping.")
        return []

    jobs: list[dict] = []
    print(f"\n[{SOURCE}] Fetching {URL}")

    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(4_000)

        if any(kw in page.url.lower() for kw in ("login", "signin", "sign-in", "register")):
            print(f"[{SOURCE}] Login wall detected — skipping.")
            return []

        await _scroll_load(page, rounds=8)

        cards = []
        for sel in (
            "[class*='JobCard']",
            "[class*='job-card']",
            "article[class*='job']",
            "[data-testid*='job']",
            "li[class*='job']",
        ):
            cards = await page.query_selector_all(sel)
            if cards:
                print(f"[{SOURCE}] {len(cards)} cards via {sel!r}")
                break

        if not cards:
            print(f"[{SOURCE}] No cards — falling back to anchor scan.")
            for link in await page.query_selector_all("a[href*='/jobs/']"):
                title = await _txt(link)
                href  = await _attr(link, "href")
                if not title or not relevant(title):
                    continue
                company = ""
                try:
                    p_jsh = await link.evaluate_handle(
                        "el => el.closest('li,article,[class*=\"card\"],section')"
                    )
                    p_el = p_jsh.as_element()
                    if p_el:
                        company = await _txt(
                            await p_el.query_selector(
                                "[class*='company'],[class*='Company'],h2,h3"
                            )
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
            title_el   = await _first(card, "[class*='title']", "[class*='Title']",
                                      "[class*='role']", "h2", "h3", "h4")
            company_el = await _first(card, "[class*='company']", "[class*='Company']",
                                      "[class*='employer']", "[class*='org']")
            link_el    = await _first(card, "a[href*='/jobs/']", "a")
            loc_el     = await _first(card, "[class*='location']", "[class*='Location']",
                                      "[class*='city']", "[class*='remote']")

            title    = await _txt(title_el)
            company  = await _txt(company_el)
            href     = await _attr(link_el, "href")
            location = await _txt(loc_el) or "New York, NY"

            if not title or not relevant(title):
                continue

            jobs.append({
                "date":     str(date.today()),
                "source":   SOURCE,
                "company":  company or "Unknown",
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


# ── Scraper: Indeed ────────────────────────────────────────────────────────

async def scrape_indeed(page) -> list[dict]:
    """
    indeed.com — sales/GTM roles at NYC startups, last 14 days, by date.
    Indeed uses strong anti-bot defences; we detect CAPTCHA/robot-check
    pages and bail gracefully.  data-testid attributes are more stable
    across redesigns than class names.
    """
    BASE = "https://www.indeed.com"
    URL = (
        "https://www.indeed.com/jobs"
        "?q=sales+startup&l=New+York%2C+NY&sort=date&fromage=14"
    )
    SOURCE = "Indeed"

    if not robots_ok(BASE, URL):
        print(f"[{SOURCE}] robots.txt disallows this path — skipping.")
        return []

    jobs: list[dict] = []
    print(f"\n[{SOURCE}] Fetching {URL}")

    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(4_000)

        body_text = await page.evaluate("document.body.innerText")
        if any(kw in body_text.lower() for kw in (
            "captcha", "robot", "unusual traffic", "verify you are human",
        )):
            print(f"[{SOURCE}] Anti-bot check triggered — skipping.")
            return []

        await _scroll_load(page, rounds=6)

        cards = []
        for sel in (
            ".job_seen_beacon",
            "[class*='jobCard']",
            "li[class*='result']",
            "div[class*='result']",
        ):
            cards = await page.query_selector_all(sel)
            if cards:
                print(f"[{SOURCE}] {len(cards)} cards via {sel!r}")
                break

        if not cards:
            print(f"[{SOURCE}] No cards — Indeed may have blocked the request.")
            return []

        for card in cards:
            title_el   = await _first(
                card,
                "h2[class*='jobTitle'] a span[title]",
                "h2[class*='jobTitle'] a span",
                "[data-testid='jobTitle']",
                "a.jcs-JobTitle span",
                "h2",
            )
            company_el = await _first(
                card,
                "[data-testid='company-name']",
                "[class*='companyName']",
                "span[class*='company']",
            )
            link_el    = await _first(
                card,
                "h2[class*='jobTitle'] a",
                "a.jcs-JobTitle",
                "a[data-jk]",
            )
            loc_el     = await _first(
                card,
                "[data-testid='text-location']",
                "[class*='companyLocation']",
            )
            date_el    = await _first(
                card,
                "[data-testid='myJobsStateDate']",
                "span[class*='date']",
            )

            # Prefer the title attribute (often cleaner than inner text on Indeed)
            title    = await _attr(title_el, "title") or await _txt(title_el)
            company  = await _txt(company_el)
            href     = await _attr(link_el, "href")
            location = await _txt(loc_el) or "New York, NY"
            posted   = await _txt(date_el)

            if not title or not relevant(title):
                continue

            if href and not href.startswith("http"):
                href = urljoin(BASE, href)

            jobs.append({
                "date":     str(date.today()),
                "source":   SOURCE,
                "company":  company or "Unknown",
                "title":    title,
                "location": location,
                "url":      href or URL,
                "posted":   posted,
            })

    except PlaywrightTimeout:
        print(f"[{SOURCE}] Page load timed out.")
    except Exception as exc:
        print(f"[{SOURCE}] Error: {exc}")

    print(f"[{SOURCE}] {len(jobs)} relevant jobs.")
    return jobs


# ── Scraper: LinkedIn via Google dorking ───────────────────────────────────

async def scrape_linkedin_google(page) -> list[dict]:
    """
    Google dorking for LinkedIn job listings in NYC.
    Issues targeted searches for site:linkedin.com/jobs matching
    sales/GTM keywords, then parses result titles and URLs.

    Note: automating Google Search is against Google's Terms of Service.
    Google may block requests after a few queries; we detect CAPTCHA /
    consent pages and stop early rather than retrying aggressively.
    """
    SOURCE = "LinkedIn (via Google)"

    QUERIES = [
        'site:linkedin.com/jobs "account executive" OR "sales" "New York" startup',
        'site:linkedin.com/jobs "SDR" OR "BDR" OR "business development" "New York"',
        'site:linkedin.com/jobs "customer success" OR "GTM" OR "revenue" "New York" startup',
    ]

    jobs: list[dict] = []

    for query in QUERIES:
        search_url = (
            "https://www.google.com/search"
            f"?q={requests.utils.quote(query)}&num=20&hl=en&gl=us"
        )

        if not robots_ok("https://www.google.com", search_url):
            print(f"[{SOURCE}] Google robots.txt disallows — stopping.")
            break

        print(f"\n[{SOURCE}] Query: {query[:70]}…")

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(3_000)

            body_text = await page.evaluate("document.body.innerText")
            if any(kw in body_text.lower() for kw in (
                "captcha", "unusual traffic", "not a robot", "verify",
            )):
                print(f"[{SOURCE}] Google CAPTCHA triggered — stopping.")
                break
            if "consent.google.com" in page.url or "before you continue" in body_text.lower():
                print(f"[{SOURCE}] Google consent gate — stopping.")
                break

            # Each organic result lives in div.g or a [data-sokoban-container]
            result_els = await page.query_selector_all(
                "div.g, div[data-sokoban-container]"
            )
            if not result_els:
                result_els = await page.query_selector_all("div:has(h3)")

            seen_urls: set[str] = set()
            for el in result_els:
                h3_el     = await _first(el, "h3")
                raw_title = await _txt(h3_el)
                if not raw_title:
                    continue

                link_el  = await _first(el, "a[href*='linkedin.com']", "a[href]")
                raw_href = await _attr(link_el, "href")
                url      = _decode_google_href(raw_href)

                if not url or "linkedin.com/jobs" not in url:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                job_title, company = _parse_linkedin_title(raw_title)
                if not job_title or not relevant(job_title):
                    continue

                jobs.append({
                    "date":     str(date.today()),
                    "source":   SOURCE,
                    "company":  company or "Unknown",
                    "title":    job_title,
                    "location": "New York, NY",
                    "url":      url,
                    "posted":   "",
                })

        except PlaywrightTimeout:
            print(f"[{SOURCE}] Timed out — stopping.")
            break
        except Exception as exc:
            print(f"[{SOURCE}] Error on query: {exc}")
            break

        # Extra pause between Google queries to reduce block risk
        await asyncio.sleep(RATE_LIMIT_DELAY * 2)

    print(f"[{SOURCE}] {len(jobs)} relevant jobs total.")
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

        for scrape_fn in (
            scrape_builtin,
            scrape_wellfound,
            scrape_workatastartup,
            scrape_otta,
            scrape_indeed,
            scrape_linkedin_google,
        ):
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
