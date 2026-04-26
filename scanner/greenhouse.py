"""
Greenhouse ATS — public API client (no scraping, no auth needed).
Most startups/tech companies host jobs at:
  https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs
"""

import urllib.request
import json
from datetime import datetime, timezone


def fetch_jobs(company_slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  [greenhouse] Could not fetch {company_slug}: {e}")
        return []

    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "id": str(j["id"]),
            "title": j["title"],
            "company": company_slug,
            "source": "greenhouse",
            "location": j.get("location", {}).get("name", "Remote/Unknown"),
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("updated_at", ""),
            "departments": [d["name"] for d in j.get("departments", [])],
        })
    return jobs


def filter_recent(jobs: list[dict], since_iso: str | None = None) -> list[dict]:
    if since_iso is None:
        today = datetime.now(timezone.utc).date()
        return [
            j for j in jobs
            if j["posted_at"] and datetime.fromisoformat(
                j["posted_at"].replace("Z", "+00:00")
            ).date() >= today
        ]
    cutoff = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    return [
        j for j in jobs
        if j["posted_at"] and datetime.fromisoformat(
            j["posted_at"].replace("Z", "+00:00")
        ) >= cutoff
    ]
