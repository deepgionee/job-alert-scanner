"""Greenhouse ATS — public JSON API, no auth needed."""
import urllib.request, json
from datetime import datetime, timezone

def fetch_jobs(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"[greenhouse] {slug}: {e}"); return []
    return [{
        "id":          str(j["id"]),
        "title":       j["title"],
        "company":     slug,
        "source":      "greenhouse",
        "location":    j.get("location", {}).get("name", "Unknown"),
        "url":         j.get("absolute_url", ""),
        "posted_at":   j.get("updated_at", ""),
        "departments": [d["name"] for d in j.get("departments", [])],
    } for j in data.get("jobs", [])]

def filter_recent(jobs, since_iso=None):
    today = datetime.now(timezone.utc).date()
    return [j for j in jobs if j["posted_at"] and
            datetime.fromisoformat(j["posted_at"].replace("Z","+00:00")).date() >= today]
