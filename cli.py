#!/usr/bin/env python3
"""
job-alert-scanner — main entry point

  python cli.py --scan            scan all companies, notify on new jobs
  python cli.py --scan --dry-run  preview new jobs, skip notifications
  python cli.py --demo            quick demo against Notion (Greenhouse API)
"""

import argparse
from pathlib import Path
import yaml
from scanner import greenhouse, lever, store, notifier

CONFIG_PATH = Path(__file__).parent / "config" / "companies.yml"


def load_companies():
    if not CONFIG_PATH.exists():
        return [
            {"slug": "notion",      "ats": "greenhouse"},
            {"slug": "perplexity",  "ats": "ashby"},
            {"slug": "elevenlabs",  "ats": "ashby"},
            {"slug": "harvey",      "ats": "ashby"},
            {"slug": "mistral",     "ats": "lever"},
        ]
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f).get("companies", [])


def scan(dry_run=False):
    companies = load_companies()
    db = store.JobStore()
    print(f"Scanning {len(companies)} companies | {db.total_seen} jobs in state")
    all_jobs = []

    for c in companies:
        slug = c["slug"]
        ats  = c.get("ats", "greenhouse").lower()
        print(f"  [{ats}] {slug}...", end=" ", flush=True)

        if ats == "greenhouse":
            jobs = greenhouse.fetch_jobs(slug)
        elif ats == "lever":
            jobs = lever.fetch_jobs(slug)
        elif ats == "ashby":
            from scanner import ashby
            jobs = ashby.fetch_jobs(slug)
        elif ats == "playwright":
            url = c.get("url", "")
            if not url:
                print(f"SKIP (no url field)")
                continue
            from scanner import playwright_scanner
            jobs = playwright_scanner.fetch_jobs(slug, url)
        else:
            print(f"unknown ATS, skipping")
            continue

        print(f"{len(jobs)} listings")
        all_jobs.extend(jobs)

    new_jobs = db.find_new(all_jobs)
    if not new_jobs:
        print("No new jobs found.")
        return

    print(f"\n*** {len(new_jobs)} NEW job(s) found! ***\n")
    for j in new_jobs:
        print(f"  [{j['company'].upper()}] {j['title']}")
        print(f"    {j['location']} | posted: {j['posted_at'][:10] if j['posted_at'] else 'n/a'}")
        print(f"    {j['url']}\n")

    if dry_run:
        print("[dry-run] Notifications skipped.")
    else:
        notifier.dispatch(new_jobs)


def demo():
    print("=== DEMO: Live jobs from Notion (Greenhouse API) ===\n")
    jobs = greenhouse.fetch_jobs("notion")
    print(f"Total active listings at Notion: {len(jobs)}\n")
    recent = sorted(jobs, key=lambda j: j["posted_at"] or "", reverse=True)[:5]
    for j in recent:
        print(f"  * {j['title']}")
        print(f"    {j['location']} | {j['posted_at'][:10] if j['posted_at'] else 'n/a'}")
        print(f"    {j['url']}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scan",    action="store_true")
    p.add_argument("--demo",    action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.demo:      demo()
    elif args.scan:    scan(dry_run=args.dry_run)
    else:              p.print_help()
