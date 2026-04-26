"""
Lever ATS — public API client.
Companies host jobs at:  https://jobs.lever.co/{company_slug}
API endpoint:            https://api.lever.co/v0/postings/{company_slug}
"""

import urllib.request
import json
from datetime import datetime, timezone


def fetch_jobs(company_slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            postings = json.loads(resp.read())
    except Exception as e:
        print(f"  [lever] Could not fetch {company_slug}: {e}")
        return []

    jobs = []
    for p in postings:
        created_ms = p.get("createdAt", 0)
        created_iso = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
        jobs.append({
            "id": p["id"],
            "title": p["text"],
            "company": company_slug,
            "source": "lever",
            "location": p.get("categories", {}).get("location", "Remote/Unknown"),
            "url": p.get("hostedUrl", f"https://jobs.lever.co/{company_slug}/{p['id']}"),
            "posted_at": created_iso,
            "departments": [p.get("categories", {}).get("team", "")],
        })
    return jobs


def filter_recent(jobs: list[dict], since_iso: str | None = None) -> list[dict]:
    if since_iso is None:
        today = datetime.now(timezone.utc).date()
        return [
            j for j in jobs
            if j["posted_at"] and datetime.fromisoformat(j["posted_at"]).date() >= today
        ]
    cutoff = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    return [
        j for j in jobs
        if j["posted_at"] and datetime.fromisoformat(j["posted_at"]) >= cutoff
    ]
