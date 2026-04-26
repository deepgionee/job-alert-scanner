#!/usr/bin/env python3
"""
job-alert-scanner — main entry point

  python cli.py --scan            scan all companies, notify on new jobs
  python cli.py --scan --dry-run  preview new jobs, skip notifications
  python cli.py --demo            quick demo against Figma (Greenhouse API)
"""

import argparse
import yaml
from pathlib import Path
from scanner import greenhouse, lever, store, notifier

CONFIG_PATH = Path(__file__).parent / "config" / "companies.yml"


def load_companies():
    if not CONFIG_PATH.exists():
        return [
            {"slug": "figma",   "ats": "greenhouse"},
            {"slug": "stripe",  "ats": "greenhouse"},
            {"slug": "mistral", "ats": "lever"},
        ]
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f).get("companies", [])


def scan(dry_run=False):
    companies = load_companies()
    job_store = store.JobStore()

    print(f"Scanning {len(companies)} companies  |  {job_store.total_seen} jobs seen so far")
    all_jobs = []

    for c in companies:
        slug = c["slug"]
        ats  = c.get("ats", "greenhouse").lower()
        print(f"  Fetching [{ats}] {slug}...")

        if ats == "greenhouse":
            jobs = greenhouse.fetch_jobs(slug)
        elif ats == "lever":
            jobs = lever.fetch_jobs(slug)
        elif ats == "ashby":
            from scanner import ashby
            jobs = ashby.fetch_jobs(slug)
        elif ats == "peoplestrong":
            url = c.get("url", "")
            if not url:
                print(f"  SKIP: no 'url' field for '{slug}'")
                continue
            from scanner import peoplestrong
            jobs = peoplestrong.fetch_jobs(slug, url)
        elif ats == "playwright":
            url = c.get("url", "")
            if not url:
                print(f"  SKIP: no 'url' field for '{slug}'")
                continue
            from scanner import playwright_scanner
            jobs = playwright_scanner.fetch_jobs(slug, url)
        else:
            print(f"  Unknown ATS '{ats}' — skipping")
            continue

        print(f"    -> {len(jobs)} active listings")
        all_jobs.extend(jobs)

    new_jobs = job_store.find_new(all_jobs)

    if not new_jobs:
        print("No new jobs found.")
        return

    print(f"\n*** {len(new_jobs)} NEW job(s) found! ***\n")
    for j in new_jobs:
        print(f"  [{j['company'].upper()}] {j['title']}")
        print(f"    {j['location']}  |  {(j['posted_at'] or '')[:10]}")
        print(f"    {j['url']}\n")

    if dry_run:
        print("[dry-run] Skipping notifications.")
    else:
        notifier.dispatch(new_jobs)


def demo():
    print("=== DEMO: Live jobs from Figma (Greenhouse API) ===\n")
    jobs = greenhouse.fetch_jobs("figma")
    print(f"Total active listings at Figma: {len(jobs)}\n")
    recent = sorted(jobs, key=lambda j: j["posted_at"] or "", reverse=True)[:5]
    for j in recent:
        print(f"  * {j['title']}")
        print(f"    {j['location']} | {(j['posted_at'] or '')[:10]}")
        print(f"    {j['url']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Alert Scanner")
    parser.add_argument("--scan",    action="store_true")
    parser.add_argument("--demo",    action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.demo:       demo()
    elif args.scan:     scan(dry_run=args.dry_run)
    else:               parser.print_help()
