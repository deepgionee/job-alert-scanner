"""Ashby ATS — public API (POST request), no auth needed."""
import urllib.request, json
from datetime import datetime, timezone

def fetch_jobs(slug):
    url  = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    body = json.dumps({}).encode()
    req  = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "User-Agent":   "job-alert-scanner/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"[ashby] {slug}: {e}"); return []
    jobs = []
    for j in data.get("jobPostings", []):
        loc = j.get("location") or {}
        if isinstance(loc, dict):
            location = "Remote" if j.get("isRemote") else ", ".join(
                filter(None, [loc.get("city",""), loc.get("state","")])) or "Unknown"
        else:
            location = str(loc) or "Unknown"
        jobs.append({
            "id":          j.get("id",""),
            "title":       j.get("title",""),
            "company":     slug,
            "source":      "ashby",
            "location":    location,
            "url":         j.get("jobPostingUrl") or
                           f"https://jobs.ashbyhq.com/{slug}/{j.get('id','')}",
            "posted_at":   j.get("publishedDate","") or "",
            "departments": [j.get("department","")],
        })
    return jobs
