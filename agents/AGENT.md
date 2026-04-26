# OpenCLI Custom Adapter — Job Alert Scanner

## Purpose
This adapter teaches OpenCLI how to scrape job postings from company career pages
that do NOT use a standard ATS (Greenhouse/Lever/Workday).

OpenCLI controls your real, logged-in Chrome browser — so it looks like a human visitor
and is far less likely to be blocked than headless bots.

## How to use
```bash
npm install -g @jackwener/opencli
opencli run jobs --url "https://www.anthropic.com/careers" --output json
```

## Target schema (all adapters must output this)
```json
{
  "id": "<unique string>",
  "title": "<job title>",
  "company": "<company slug>",
  "source": "opencli",
  "location": "<city / remote>",
  "url": "<direct apply link>",
  "posted_at": "<ISO 8601 or empty>",
  "departments": ["<dept>"]
}
```

## Recon steps (run once per new site)
1. Open Chrome DevTools -> Network tab -> filter XHR/Fetch
2. Load the careers page and look for a JSON endpoint
3. If a clean endpoint exists -> build a direct HTTP client
4. If no API -> use OpenCLI browser primitives to extract from rendered DOM

## DOM extraction template
```javascript
const jobs = document.querySelectorAll('[data-job-listing], .job-card, .opening');
return Array.from(jobs).map(el => ({
  id:       el.dataset.jobId || el.querySelector('a')?.href?.split('/').pop(),
  title:    el.querySelector('h3, h2, .title')?.innerText?.trim(),
  location: el.querySelector('.location, [data-location]')?.innerText?.trim() || 'Unknown',
  url:      el.querySelector('a')?.href,
  posted_at: el.querySelector('time')?.getAttribute('datetime') || '',
}));
```

## Anti-block strategy
- OpenCLI reuses your real Chrome session (cookies, fingerprint) -> not a bot
- Add random 2-5s delay between page loads
- Never run more than 1 concurrent request per domain

## Adding a new company
1. Recon the site (see above)
2. Add entry in config/companies.yml with ats: opencli
3. Write adapter: agents/adapters/{company_slug}.js
4. Test: python cli.py --scan --dry-run
