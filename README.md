# job-alert-scanner

Real-time job alert system — notifies your audience the moment a new position is posted,
so they can be among the first 100 applicants.

Built on two pillars:
- **Path A (preferred):** Direct JSON APIs exposed by ATS platforms (Greenhouse, Lever, Workday) — zero scraping, zero blocking risk, free to call
- **Path B (custom pages):** [jackwener/OpenCLI](https://github.com/jackwener/opencli) — transforms any career page into a CLI tool by controlling your real Chrome session, so it looks like a human visitor

## Quick start

```bash
git clone https://github.com/deepgionee/job-alert-scanner
cd job-alert-scanner
pip install pyyaml

# Demo: fetch today's jobs from Notion (no config needed)
python cli.py --demo

# Full scan with new-job detection
python cli.py --scan --dry-run    # preview only
python cli.py --scan              # scan + send notifications
```

## Configuration

### 1. Add companies to watch

Edit `config/companies.yml`:
```yaml
companies:
  - slug: notion       # greenhouse slug
    ats: greenhouse
  - slug: linear       # lever slug
    ats: lever
  - slug: anthropic    # custom page via OpenCLI
    ats: opencli
    url: https://www.anthropic.com/careers
```

**Finding the right slug:**
- Greenhouse: check if `boards-api.greenhouse.io/v1/boards/SLUG/jobs` returns JSON
- Lever: check if `jobs.lever.co/SLUG` exists

### 2. Set notification channels (env vars)

```bash
# Telegram (most popular for real-time alerts)
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_channel_id"

# Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Generic webhook (Zapier, Make, n8n, etc.)
export WEBHOOK_URL="https://your-server.com/jobs"
```

### 3. Run on a schedule

**Linux/Mac (cron — every 3 minutes):**
```bash
crontab -e
# Add:
*/3 * * * * cd /path/to/job-alert-scanner && python cli.py --scan >> logs/cron.log 2>&1
```

**Windows (Task Scheduler):**
- Program: `python`
- Arguments: `C:\path\to\job-alert-scanner\cli.py --scan`
- Trigger: repeat every 3 minutes

**GitHub Actions (every 5 minutes, free tier):**
```yaml
# .github/workflows/scan.yml
on:
  schedule:
    - cron: '*/5 * * * *'
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - run: python cli.py --scan
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
```

## For custom career pages (OpenCLI — Path B)

Install OpenCLI:
```bash
npm install -g @jackwener/opencli
```

Then read `agents/AGENT.md` for instructions on writing a custom adapter for any career page.

The key insight: OpenCLI reuses your real Chrome browser session — not a headless bot —
so it is extremely hard to detect or block.

## Why this beats batch scraping

| Approach | Latency | Block risk | Cost |
|---|---|---|---|
| Daily batch scraper | Hours | High | Low |
| This tool (3-min cron) | ~3 min | None (API) / Low (OpenCLI) | Free |
| AI agent browsing loop | Variable | High | High (LLM tokens) |
| Official webhooks | Instant | None | Free (if available) |

## Repo structure

```
job-alert-scanner/
├── cli.py                 # main entry point
├── config/
│   └── companies.yml      # companies to watch
├── scanner/
│   ├── greenhouse.py      # Greenhouse API client
│   ├── lever.py           # Lever API client
│   ├── store.py           # seen-jobs state (data/seen_jobs.json)
│   └── notifier.py        # Telegram / Slack / Discord / webhook
├── agents/
│   └── AGENT.md           # OpenCLI adapter guide for custom pages
└── data/
    └── seen_jobs.json      # auto-created, tracks all seen job IDs
```
