"""
PeopleStrong ATS — direct API probe + Playwright fallback.

PeopleStrong powers many hospital and corporate career portals in India.
The page loads via JavaScript, but internally it calls a hidden JSON API.
We probe all known API patterns directly (no browser, ~1-3s each).
If all fail, we hand off to playwright_scanner as a last resort (~30s).

Usage (in config/companies.yml):
  - slug: care-hospital
    ats: peoplestrong
    url: https://carecareers.peoplestrong.com/job/joblist
"""

import json
import urllib.request
import urllib.error

ENDPOINTS = [
    ("POST", "/job/getJobList",             {"pageNo": 1, "pageSize": 200, "searchText": ""}),
    ("POST", "/job/getjoblist",             {"pageNo": 1, "pageSize": 200, "searchText": ""}),
    ("POST", "/job/getJobListForCareer",    {"pageNo": 1, "pageSize": 200}),
    ("POST", "/job/getJobListForCareer",    {"pageNo": 1, "pageSize": 200, "searchText": ""}),
    ("POST", "/api/v1/job/search",          {"page": 1, "size": 200, "keyword": ""}),
    ("POST", "/api/v1/jobs/list",           {"page": 1, "size": 200}),
    ("POST", "/career/getJobList",          {"pageNo": 1, "pageSize": 200}),
    ("POST", "/job/jobList",                {"pageNo": 1, "pageSize": 200}),
    ("GET",  "/job/getJobList?pageNo=1&pageSize=200", None),
    ("GET",  "/job/getAllJobs",             None),
    ("GET",  "/job/jobList",               None),
    ("GET",  "/api/jobs?page=1&limit=200", None),
]


def _headers(base_url):
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


def _try_endpoint(base_url, method, path, body):
    url = base_url + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(base_url), method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
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
    jobs_raw = []
    if isinstance(data, list):
        jobs_raw = data
    elif isinstance(data, dict):
        for key in ("jobList", "jobs", "data", "result", "records",
                    "jobPostings", "content", "items", "list", "positions",
                    "jobData", "jobDetails"):
            val = data.get(key)
            if isinstance(val, list) and val:
                jobs_raw = val
                break
            if isinstance(val, dict):
                for inner in ("jobList", "jobs", "records", "items", "list"):
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
            location = str(raw_loc).strip() if raw_loc else "Unknown"
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
            "departments": [],
        })
    return normalized


def fetch_jobs(slug, url):
    """
    Fetch jobs from a PeopleStrong career portal.
    slug: company identifier (e.g. 'care-hospital')
    url:  full URL of the job listings page
    """
    base_url = url.split("/job/")[0] if "/job/" in url else url.rstrip("/")

    for method, path, body in ENDPOINTS:
        result = _try_endpoint(base_url, method, path, body)
        if result is not None:
            jobs = _extract_jobs(result, slug, base_url)
            if jobs:
                print(f"    PeopleStrong API found via {method} {path}")
                return jobs

    print(f"  [peoplestrong] Direct API exhausted — launching headless browser...")
    try:
        from scanner import playwright_scanner
        return playwright_scanner.fetch_jobs(slug, url)
    except Exception as e:
        print(f"  [peoplestrong] Browser fallback failed: {e}")
        return []
