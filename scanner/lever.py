"""Lever ATS — public JSON API, no auth needed."""
import urllib.request, json
from datetime import datetime, timezone

def fetch_jobs(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            postings = json.loads(r.read())
    except Exception as e:
        print(f"[lever] {slug}: {e}"); return []
    jobs = []
    for p in postings:
        ms = p.get("createdAt", 0)
        iso = datetime.fromtimestamp(ms/1000, tz=timezone.utc).isoformat()
        jobs.append({
            "id":          p["id"],
            "title":       p["text"],
            "company":     slug,
            "source":      "lever",
            "location":    p.get("categories", {}).get("location", "Unknown"),
            "url":         p.get("hostedUrl", f"https://jobs.lever.co/{slug}/{p['id']}"),
            "posted_at":   iso,
            "departments": [p.get("categories", {}).get("team", "")],
        })
    return jobs
