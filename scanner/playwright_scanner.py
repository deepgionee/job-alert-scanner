"""
Playwright-based scanner for JavaScript-rendered career pages.

Used for sites like PeopleStrong (Care Hospital) that:
  - Render job listings via JavaScript (no static HTML)
  - Don't expose a documented public API
  - Make hidden XHR/fetch calls to an internal API when the page loads

Strategy:
  1. Launch headless Chromium
  2. Intercept every network response that returns JSON with "job" in the URL
  3. Extract and normalize job records from the captured payload
  4. Fall back to DOM-based scraping if no API response is captured

Install:
  pip install playwright
  playwright install chromium --with-deps   # (run once)
"""

import json
import asyncio
from urllib.parse import urljoin


def _extract_jobs_from_json(data, slug, source_url):
    jobs_raw = []
    if isinstance(data, list):
        jobs_raw = data
    elif isinstance(data, dict):
        for key in ("jobList", "jobs", "data", "result", "records",
                    "jobPostings", "content", "items", "list", "positions"):
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                jobs_raw = val
                break
            if isinstance(val, dict):
                for inner in ("jobList", "jobs", "records", "items"):
                    inner_val = val.get(inner)
                    if isinstance(inner_val, list) and len(inner_val) > 0:
                        jobs_raw = inner_val
                        break
                if jobs_raw:
                    break
    if not jobs_raw:
        return []

    normalized = []
    for j in jobs_raw:
        if not isinstance(j, dict):
            continue
        job_id  = str(j.get("jobId") or j.get("id") or j.get("jobCode") or "")
        title   = (j.get("jobTitle") or j.get("title") or
                   j.get("designation") or j.get("jobName") or "").strip()
        posted  = (j.get("postedDate") or j.get("createdDate") or
                   j.get("publishDate") or j.get("postDate") or "")
        raw_loc = (j.get("location") or j.get("jobLocation") or
                   j.get("city")     or j.get("workLocation") or "")
        if isinstance(raw_loc, dict):
            location = raw_loc.get("name") or raw_loc.get("city") or "Unknown"
        else:
            location = str(raw_loc) if raw_loc else "Unknown"
        job_url = j.get("jobUrl") or j.get("applyUrl") or ""
        if not job_url and job_id:
            domain = source_url.split("/job/")[0]
            job_url = f"{domain}/job/jobdetail/{job_id}"
        if not job_url:
            job_url = source_url
        if not title and not job_id:
            continue
        normalized.append({
            "id":          job_id or title,
            "title":       title,
            "company":     slug,
            "source":      "playwright",
            "location":    location,
            "url":         job_url,
            "posted_at":   posted,
            "departments": [],
        })
    return normalized


async def _dom_extract(page, slug, base_url):
    selectors = [
        ".job-card", ".job-listing", ".job-item",
        "[class*=\'job-card\']", "[class*=\'job-listing\']",
        ".career-card", ".position-card",
        "li.job", "div.job", "[data-testid*=\'job\']",
    ]
    for sel in selectors:
        try:
            cards = await page.query_selector_all(sel)
        except Exception:
            continue
        if not cards:
            continue
        jobs = []
        for i, card in enumerate(cards):
            try:
                text    = (await card.inner_text()).strip()
                link_el = await card.query_selector("a")
                href    = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = urljoin(base_url, href)
                jobs.append({
                    "id":          href or f"{slug}-dom-{i}",
                    "title":       text[:120],
                    "company":     slug,
                    "source":      "playwright-dom",
                    "location":    "See listing",
                    "url":         href or base_url,
                    "posted_at":   "",
                    "departments": [],
                })
            except Exception:
                continue
        if jobs:
            return jobs
    return []


async def _fetch_async(url, slug):
    from playwright.async_api import async_playwright
    captured = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        async def on_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                rurl = response.url.lower()
                if not any(kw in rurl for kw in (
                    "job", "career", "posting", "vacancy", "position", "recruit", "opening"
                )):
                    return
                body = await response.json()
                jobs = _extract_jobs_from_json(body, slug, url)
                if jobs:
                    captured.extend(jobs)
            except Exception:
                pass

        page.on("response", on_response)
        try:
            await page.goto(url, wait_until="networkidle", timeout=40_000)
        except Exception:
            pass
        await page.wait_for_timeout(4_000)

        if not captured:
            print(f"  [playwright] No API response captured — trying DOM extraction")
            captured = await _dom_extract(page, slug, url)

        await browser.close()

    seen_ids = set()
    unique = []
    for j in captured:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            unique.append(j)
    return unique


def fetch_jobs(slug, url):
    """
    Fetch jobs from any JS-rendered career page.
    slug: short name used as company identifier (e.g. 'care-hospital')
    url:  full URL of the job listings page
    """
    try:
        return asyncio.run(_fetch_async(url, slug))
    except ImportError:
        print(
            "  [playwright] ERROR: not installed.\n"
            "  Run: pip install playwright && playwright install chromium --with-deps"
        )
        return []
    except Exception as e:
        print(f"  [playwright] {slug}: {e}")
        return []
