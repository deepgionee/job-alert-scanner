"""
PeopleStrong ATS — direct API scanner for Care Hospital and similar portals.

Discovered endpoint (via network analysis):
  GET /api/cp/rest/altone/cp/jobs/v1?offset=0&limit=200
  Response: {"totalRecords": N, "response": [...jobs...], "messageCode": "...", "solrSearch": ...}

Falls back to Playwright (browser) if the direct call fails.
"""

import json
import urllib.request
import urllib.error
import http.cookiejar

BASE_PATH = "/api/cp/rest/altone/cp"

# Endpoints in priority order — the first one is the confirmed working pattern
ENDPOINTS = [
    ("GET",  f"{BASE_PATH}/jobs/v1?offset=0&limit=200",  None),
    ("GET",  f"{BASE_PATH}/jobs/v1?offset=0&limit=100",  None),
    # Legacy patterns tried as fallback
    ("POST", "/job/getJobList",            {"pageNo": 1, "pageSize": 200, "searchText": ""}),
    ("POST", "/job/getjoblist",            {"pageNo": 1, "pageSize": 200, "searchText": ""}),
    ("POST", "/job/getJobListForCareer",   {"pageNo": 1, "pageSize": 200}),
    ("POST", "/api/v1/job/search",         {"page": 1,  "size": 200,     "keyword": ""}),
    ("POST", "/career/getJobList",         {"pageNo": 1, "pageSize": 200}),
]


def _req_headers(base_url):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Referer": base_url + "/job/joblist",
        "Origin": base_url,
        "X-Requested-With": "XMLHttpRequest",
    }


def _make_opener(base_url):
    """Create an opener with cookie support, optionally seeded by /session call."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    # Warm up the session (mimics what the browser does first)
    try:
        session_url = base_url + f"{BASE_PATH}/session"
        req = urllib.request.Request(
            session_url, headers=_req_headers(base_url), method="GET"
        )
        opener.open(req, timeout=8)
    except Exception:
        pass  # best-effort — jobs call may still work without session
    return opener


def _try_endpoint(opener, base_url, method, path, body):
    url = base_url + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, headers=_req_headers(base_url), method=method
    )
    try:
        with opener.open(req, timeout=15) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type", "")
            if ("json" in ct
                    or raw.strip().startswith(b"{")
                    or raw.strip().startswith(b"[")):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
    except urllib.error.HTTPError as e:
        if e.code in (400, 500):
            try:
                return json.loads(e.read())
            except Exception:
                pass
    except Exception:
        pass
    return None


def _extract_jobs(data, slug, base_url):
    """
    PeopleStrong v2 API returns:
      {"totalRecords": N, "response": [...jobs...], "messageCode": "...", ...}
    Each job has fields like: jobCode, jobTitle, locationName, postedDate, etc.
    """
    jobs_raw = []

    if isinstance(data, list):
        jobs_raw = data
    elif isinstance(data, dict):
        # PeopleStrong v2: jobs are in "response" key
        # Also try other common key names for older PeopleStrong versions
        for key in ("response", "jobList", "jobs", "data", "result", "records",
                    "jobPostings", "content", "items", "list", "positions",
                    "jobData", "jobDetails"):
            val = data.get(key)
            if isinstance(val, list) and val:
                jobs_raw = val
                break
            if isinstance(val, dict):
                for inner in ("jobList", "jobs", "records", "items", "list", "response"):
                    inner_val = val.get(inner)
                    if isinstance(inner_val, list) and inner_val:
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

        # PeopleStrong v2 uses jobCode as the primary identifier
        job_id = str(
            j.get("jobCode") or j.get("jobId") or j.get("id") or ""
        )
        title = (
            j.get("jobTitle") or j.get("title") or
            j.get("designation") or j.get("jobName") or ""
        ).strip()
        posted = (
            j.get("postedDate") or j.get("createdDate") or
            j.get("publishDate") or j.get("postDate") or ""
        )

        # PeopleStrong v2 uses locationName (not location)
        raw_loc = (
            j.get("locationName") or j.get("location") or
            j.get("jobLocation") or j.get("city") or
            j.get("workLocation") or ""
        )
        if isinstance(raw_loc, dict):
            location = (raw_loc.get("locationName") or
                        raw_loc.get("name") or
                        raw_loc.get("city") or "Unknown")
        else:
            location = str(raw_loc).strip() if raw_loc else "Unknown"

        # Department / function area
        dept = (
            j.get("functionalAreaName") or j.get("functionalArea") or
            j.get("department") or j.get("function") or ""
        )

        # Build apply URL
        job_url = j.get("jobUrl") or j.get("applyUrl") or ""
        if not job_url and job_id:
            job_url = f"{base_url}/job/jobdetail/{job_id}"
        if not job_url:
            job_url = base_url + "/job/joblist"

        if not title and not job_id:
            continue

        normalized.append({
            "id":          job_id or title,
            "title":       title,
            "company":     slug,
            "source":      "peoplestrong",
            "location":    location,
            "url":         job_url,
            "posted_at":   str(posted),
            "departments": [dept] if dept else [],
        })

    return normalized


def fetch_jobs(slug, url):
    """
    Fetch jobs from a PeopleStrong career portal.
    slug: identifier (e.g. 'care-hospital')
    url:  full careers page URL (e.g. https://carecareers.peoplestrong.com/job/joblist)
    """
    base_url = url.split("/job/")[0] if "/job/" in url else url.rstrip("/")

    # Create a cookie-aware opener and warm up session
    opener = _make_opener(base_url)

    for method, path, body in ENDPOINTS:
        result = _try_endpoint(opener, base_url, method, path, body)
        if result is not None:
            jobs = _extract_jobs(result, slug, base_url)
            if jobs:
                print(f"    PeopleStrong API hit: {method} {path} -> {len(jobs)} jobs")
                return jobs

    # All direct calls exhausted — try headless browser
    print(f"  [peoplestrong] Direct API exhausted — launching headless browser...")
    try:
        from scanner import playwright_scanner
        return playwright_scanner.fetch_jobs(slug, url)
    except Exception as e:
        print(f"  [peoplestrong] Browser fallback failed: {e}")
        return []
