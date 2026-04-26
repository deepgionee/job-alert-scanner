"""Sends new job alerts to Telegram, Slack, Discord, or any webhook."""
import os, json, urllib.request

def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
          headers={"Content-Type":"application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  [notifier] {e}")

def _msg(job):
    return (f"New Job Alert\n\n"
            f"Role: {job['title']}\n"
            f"Company: {job['company'].title()}\n"
            f"Location: {job['location']}\n"
            f"Apply: {job['url']}")

def dispatch(jobs):
    if not jobs: return
    tok  = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if tok and chat:
        for j in jobs:
            _post(f"https://api.telegram.org/bot{tok}/sendMessage",
                  {"chat_id": chat, "text": _msg(j)})
            print(f"  [telegram] {j['title']} @ {j['company']}")

    slack = os.getenv("SLACK_WEBHOOK_URL")
    if slack:
        for j in jobs:
            _post(slack, {"text": _msg(j)})

    discord = os.getenv("DISCORD_WEBHOOK_URL")
    if discord:
        for j in jobs:
            _post(discord, {"content": _msg(j)})

    webhook = os.getenv("WEBHOOK_URL")
    if webhook:
        _post(webhook, {"new_jobs": jobs})
