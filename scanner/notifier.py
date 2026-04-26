"""
Notification dispatcher — sends new job alerts to configured channels.
Set env vars to enable each channel:
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
  SLACK_WEBHOOK_URL
  DISCORD_WEBHOOK_URL
  WEBHOOK_URL  (generic)
"""

import os
import json
import urllib.request


def _post_json(url: str, payload: dict):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except Exception as e:
        print(f"  [notifier] POST failed to {url}: {e}")
        return None


def format_job_message(job: dict) -> str:
    return (
        f"New Job: {job['title']}\n"
        f"Company: {job['company'].title()}\n"
        f"Location: {job['location']}\n"
        f"Apply: {job['url']}"
    )


def send_telegram(jobs: list[dict], bot_token: str, chat_id: str):
    base = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for job in jobs:
        _post_json(base, {
            "chat_id": chat_id,
            "text": format_job_message(job),
            "parse_mode": "Markdown",
        })
        print(f"  [telegram] Sent: {job['title']} @ {job['company']}")


def send_slack(jobs: list[dict], webhook_url: str):
    for job in jobs:
        _post_json(webhook_url, {
            "text": format_job_message(job),
        })
        print(f"  [slack] Sent: {job['title']} @ {job['company']}")


def send_discord(jobs: list[dict], webhook_url: str):
    for job in jobs:
        _post_json(webhook_url, {"content": format_job_message(job)})
        print(f"  [discord] Sent: {job['title']} @ {job['company']}")


def dispatch(jobs: list[dict]):
    if not jobs:
        return
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat  = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        send_telegram(jobs, tg_token, tg_chat)
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_url:
        send_slack(jobs, slack_url)
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        send_discord(jobs, discord_url)
    generic_url = os.getenv("WEBHOOK_URL")
    if generic_url:
        _post_json(generic_url, {"new_jobs": jobs})
        print(f"  [webhook] Posted {len(jobs)} new jobs")
