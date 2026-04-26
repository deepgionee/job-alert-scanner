# job-alert-scanner

Real-time job alert system — notifies your audience within minutes of a new job posting,
helping them be among the first 100 applicants.

## How it works

1. GitHub Actions runs this scanner every 5 minutes (free, 24/7, no server needed)
2. Fetches jobs from Greenhouse, Lever, and Ashby ATS public APIs
3. Compares against previously seen jobs (`data/seen_jobs.json`)
4. Sends Telegram (or Slack/Discord) alerts for new postings only

## Quick start (local test)

```bash
git clone https://github.com/deepgionee/job-alert-scanner
cd job-alert-scanner
pip install pyyaml

python cli.py --demo            # live demo against Notion careers
python cli.py --scan --dry-run  # scan all companies, no notifications
```

## Production setup (GitHub Actions + Telegram)

### Step 1 — Create a Telegram Bot
1. Open Telegram → search **@BotFather** → send `/newbot`
2. Follow prompts, get a token like `7123456789:ABCdef...`

### Step 2 — Create a Telegram Channel
1. Create a new channel (e.g. "Job Alerts")
2. Add your bot as **Admin** of the channel
3. Send any message to the channel
4. Find your channel's chat ID:
   - Go to `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id": -100XXXXXXXXXX}` — that's your TELEGRAM_CHAT_ID

### Step 3 — Add secrets to GitHub
Go to your repo → **Settings → Secrets → Actions → New repository secret**
- `TELEGRAM_BOT_TOKEN` → your bot token
- `TELEGRAM_CHAT_ID`   → your channel chat ID (negative number, e.g. -1001234567890)

### Step 4 — Enable the workflow
Go to **Actions tab** in GitHub → click "Job Alert Scanner" → click **"Run workflow"**

That's it. It now runs every 5 minutes automatically.

## Adding companies

Edit `config/companies.yml`. To find the right slug:
- **Greenhouse**: try `boards-api.greenhouse.io/v1/boards/SLUG/jobs`
- **Lever**: try `jobs.lever.co/SLUG`
- **Ashby**: try `jobs.ashbyhq.com/SLUG`

## Notification channels

Set these as environment variables or GitHub Secrets:

| Secret | Channel |
|---|---|
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram (recommended) |
| `SLACK_WEBHOOK_URL` | Slack |
| `DISCORD_WEBHOOK_URL` | Discord |
| `WEBHOOK_URL` | Any custom endpoint |

## Repo structure

```
job-alert-scanner/
├── cli.py                    # entry point
├── config/companies.yml      # companies to watch
├── scanner/
│   ├── greenhouse.py         # Greenhouse API
│   ├── lever.py              # Lever API
│   ├── ashby.py              # Ashby API (Perplexity, ElevenLabs, Harvey...)
│   ├── store.py              # seen-jobs state
│   └── notifier.py           # Telegram / Slack / Discord
├── data/seen_jobs.json       # auto-created, committed after each run
└── .github/workflows/scan.yml
```
