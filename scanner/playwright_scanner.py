"""
Playwright-based scanner for JS-rendered career pages.
Used as fallback by peoplestrong.py, or directly via ats: playwright.

Key fix: _extract_jobs_from_json now checks the 'response' key
(PeopleStrong v2 API pattern) and handles locationName field.
"""

import json
import asyncio
from urllib.parse import urljoin


def _extract_jobs_from_json(data, slug, source_url):
    jobs_raw = []
    if isinstance(data, list):
        jobs_raw = data
    elif isinstance(data, dict):
        # PeopleStrong v2 uses "response" key — check it first
        for key in ("response", "jobList", "jobs", "data", "result", "records",
                    "jobPostings", "content", "items", "list", "positions"):
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                jobs_raw = val
                break
            if isinstance(val, dict):
                for inner in ("jobList", "jobs", "records", "items", "response"):
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
        job_id = str(j.get("jobCode") or j.get("jobId") or j.get("id") or j.get("jobCode") or "")
        title  = (j.get("jobTitle") or j.get("title") or
                  j.get("designation") or j.get("jobName") or "").strip()
        posted = (j.get("postedDate") or j.get("createdDate") or
                  j.get("publishDate") or j.get("postDate") or "")
        # PeopleStrong v2 uses locationName
        raw_loc = (j.get("locationName") or j.get("location") or
                   j.get("jobLocation") or j.get("city") or j.get("workLocation") or "")
        if isinstance(raw_loc, dict):
            location = (raw_loc.get("locationName") or raw_loc.get("name") or
                        raw_loc.get("city") or "Unknown")
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
    selectors = [".job-card", ".job-listing", ".job-item",
                 ".career-card", ".position-card", "li.job", "div.job"]
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
                    "id": href or f"{slug}-dom-{i}", "title": text[:120],
                    "company": slug, "source": "playwright-dom",
                    "location": "See listing", "url": href or base_url,
                    "posted_at": "", "departments": [],
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
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        async def on_response(response):
            try:
                rurl = response.url.lower()
                if any(rurl.endswith(ext) for ext in (
                    ".js", ".css", ".png", ".jpg", ".jpeg", ".svg",
                    ".woff", ".woff2", ".ttf", ".ico", ".gif", ".map",
                )):
                    return
                raw = await response.body()
                stripped = raw.strip()
                if not (stripped.startswith(b"{") or stripped.startswith(b"[")):
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
            print(f"  [playwright] No job data in JSON responses — trying DOM extraction")
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
    """Fetch jobs from any JS-rendered career page."""
    try:
        return asyncio.run(_fetch_async(url, slug))
    except ImportError:
        print("  [playwright] Not installed. Run: pip install playwright && "
              "python -m playwright install chromium --with-deps")
        return []
    except Exception as e:
        print(f"  [playwright] {slug}: {e}")
        return []
