
# Job Openings Scraper (Daily Tech Jobs Digest)

A Python automation app that aggregates software job listings and posts a curated daily digest to Telegram.

## Features

- **Multi-Platform**: Scrapes Google Jobs (via SerpApi), RemoteOK, WeWorkRemotely, Remotive, and Working Nomads.
- **Smart Curation**:
  - NO LIMIT on jobs per day (posts all relevant recent jobs).
  - Categorizes into "Remote" vs "India".
  - Filters for recent posts (last 24h).
  - Deduplicates listings.
- **Telegram Logic**:
  - Posts a single message (trimmed if needed) or multiple.
  - No pinning, clean footer.
  - Uses specific "🌍" and "🇮🇳" indicators.
- **Reliability**:
  - Uses `APScheduler` for precise timing.
  - Lock file prevents overlapping runs.
  - Automatic retries and error logging.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```
   
   - `TELEGRAM_BOT_TOKEN`: From @BotFather
   - `TELEGRAM_CHANNEL_ID`: Channel ID
   - `SERPAPI_KEY`: API Key from serpapi.com (crucial for India jobs)

3. **Run**:
   
   **As a Service (APScheduler):**
   ```bash
   python run.py
   ```
   
   **One-off / Cron Mode:**
   ```bash
   python run.py --run-once
   ```

## Deployment with GitHub Actions

1. Create a repo `JobOpeningsByVJ`.
2. Push this code.
3. Add Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_ADMIN_CHAT_ID`, `SERPAPI_KEY`.
4. It will run automatically at 10:30 UTC every day.
