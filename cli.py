#!/usr/bin/env python3
"""
job-alert-scanner — CLI entry point

Usage:
  python cli.py --scan            # scan all companies, notify on new jobs
  python cli.py --scan --dry-run  # show new jobs without sending notifications
  python cli.py --demo            # one-shot demo: fetch today's jobs from Notion (Greenhouse)

Run automatically every 3 minutes (Linux/Mac):
  */3 * * * * cd /path/to/repo && python cli.py --scan >> logs/cron.log 2>&1

Run automatically on Windows Task Scheduler:
  Program:  python
  Args:     C:\path\to\repo\cli.py --scan
  Start in: C:\path\to\repo
"""

import argparse
import yaml
from pathlib import Path
from scanner import greenhouse, lever, store, notifier

CONFIG_PATH = Path(__file__).parent / "config" / "companies.yml"


def load_companies() -> list[dict]:
    if not CONFIG_PATH.exists():
        return [
            {"slug": "notion",  "ats": "greenhouse"},
            {"slug": "figma",   "ats": "greenhouse"},
            {"slug": "linear",  "ats": "lever"},
        ]
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f).get("companies", [])


def scan(dry_run: bool = False):
    companies = load_companies()
    job_store = store.JobStore()

    print(f"Scanning {len(companies)} companies  |  {job_store.total_seen} jobs seen so far")
    all_jobs: list[dict] = []

    for c in companies:
        slug = c["slug"]
        ats  = c.get("ats", "greenhouse").lower()
        print(f"  Fetching [{ats}] {slug}...")
        if ats == "greenhouse":
            jobs = greenhouse.fetch_jobs(slug)
        elif ats == "lever":
            jobs = lever.fetch_jobs(slug)
        else:
            print(f"  Unknown ATS '{ats}' for {slug} — skipping")
            continue
        print(f"    -> {len(jobs)} active listings")
        all_jobs.extend(jobs)

    new_jobs = job_store.find_new(all_jobs)

    if not new_jobs:
        print("No new jobs found.")
        return

    print(f"\n{len(new_jobs)} NEW job(s) found!\n")
    for j in new_jobs:
        print(f"  [{j['company'].upper()}] {j['title']}")
        print(f"    {j['location']}  |  {j['posted_at'][:10]}")
        print(f"    {j['url']}\n")

    if dry_run:
        print("[dry-run] Skipping notifications.")
    else:
        notifier.dispatch(new_jobs)


def demo():
    print("=== DEMO: Fetching jobs from Notion (Greenhouse API) ===\n")
    jobs = greenhouse.fetch_jobs("notion")
    print(f"Total active listings: {len(jobs)}\n")

    today_jobs = greenhouse.filter_recent(jobs)
    if today_jobs:
        print(f"Jobs posted TODAY ({len(today_jobs)}):")
        for j in today_jobs:
            print(f"  * {j['title']}  |  {j['location']}")
            print(f"    {j['url']}")
    else:
        print("No jobs posted today. Showing 5 most recent instead:\n")
        recent = sorted(jobs, key=lambda j: j["posted_at"] or "", reverse=True)[:5]
        for j in recent:
            print(f"  * {j['title']}")
            print(f"    Location: {j['location']}")
            print(f"    Posted:   {j['posted_at'][:10] if j['posted_at'] else 'unknown'}")
            print(f"    URL:      {j['url']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Alert Scanner")
    parser.add_argument("--scan",    action="store_true", help="Scan all companies for new jobs")
    parser.add_argument("--demo",    action="store_true", help="Run demo against Notion (Greenhouse)")
    parser.add_argument("--dry-run", action="store_true", help="Don't send notifications")
    args = parser.parse_args()

    if args.demo:
        demo()
    elif args.scan:
        scan(dry_run=args.dry_run)
    else:
        parser.print_help()
