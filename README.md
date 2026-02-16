
# Job Openings Scraper (Daily Tech Jobs Digest)

A Python automation app that aggregates software job listings and posts a curated daily digest to Telegram.

## Features

- **Multi-Platform**: Scrapes RemoteOK, WeWorkRemotely, and is extensible.
- **Smart Curation**:
  - Max 30 jobs per day.
  - Balances Remote (15) and India (15) roles.
  - Filters for recent posts (last 24h).
  - Deduplicates listings.
- **Telegram Logic**:
  - Posts a single, tidy message within 4096 char limit.
  - Pins the latest digest.
  - Uses specific "🌍" and "🇮🇳" indicators.
- **Reliability**:
  - Uses `APScheduler` for precise timing (default 4:00 PM IST).
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
   - `RUN_TIME_UTC`: Default 10:30 (4:00 PM IST)

3. **Run**:
   
   **As a Service (APScheduler):**
   ```bash
   python run.py
   ```
   
   **One-off / Cron Mode:**
   ```bash
   python run.py --run-once
   ```

## Deployment

To run via system cron (if not using the internal scheduler):
```bash
30 10 * * * cd /path/to/project && /path/to/venv/bin/python run.py --run-once >> cron.log 2>&1
```

## Adding Scrapers
Implement `src.scrapers.base.JobScraper` and add to `src/main.py`.
