
import logging
import pytz
import os
import sys
import fcntl
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.utils.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, TELEGRAM_ADMIN_CHAT_ID,
    TARGET_LOCATIONS, ROLES, SCRAPER_DELAY_SECONDS,
    RUN_TIME_UTC, LOG_LEVEL
)
from src.utils.telegram_bot import TelegramBot
from src.utils.db import init_db, is_job_posted, mark_job_posted

# Import scrapers
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.weworkremotely import WeWorkRemotelyScraper
from src.scrapers.remotive import RemotiveScraper
from src.scrapers.workingnomads import WorkingNomadsScraper
from src.scrapers.google_jobs import GoogleJobsScraper
# Add more scrapers here when implemented

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_posted_time_str(posted_dt):
    """
    Returns relative string like '5 hours ago'
    """
    if not posted_dt:
        return "recently"
    # Ensure timezone aware
    if posted_dt.tzinfo is None:
        posted_dt = posted_dt.replace(tzinfo=timezone.utc)
    
    diff = datetime.now(timezone.utc) - posted_dt
    hours = int(diff.total_seconds() // 3600)
    if hours < 1:
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes} mins ago" if minutes > 0 else "Just now"
    elif hours < 24:
        return f"{hours} hours ago"
    else:
        days = int(diff.total_seconds() // 86400)
        return f"{days} days ago"

def run_job_scraping():
    # Lock file logic
    lock_file = '/tmp/job_scraper.lock'
    lock_fd = open(lock_file, 'w')
    try:
        fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logging.warning("Another instance is already running. Exiting.")
        return

    try:
        logging.info("Starting scheduled scrape job...")
        
        bot = TelegramBot()
        
        # 1. Scrape
        scrapers = [
            RemoteOKScraper(),
            WeWorkRemotelyScraper(),
            RemotiveScraper(),
            WorkingNomadsScraper(),
            GoogleJobsScraper()
        ]
        
        all_jobs = []
        
        import time
        for scraper in scrapers:
            try:
                jobs = scraper.scrape()
                all_jobs.extend(jobs)
                time.sleep(SCRAPER_DELAY_SECONDS)
            except Exception as e:
                logging.error(f"Scraper failed: {scraper.name} - {e}")

        if not all_jobs:
            logging.warning("No jobs found from any scraper.")
            bot.send_admin_alert("No jobs found today! Check scrapers.")
            return

        # 2. Deduplicate and Filter
        unique_jobs = []
        seen_ids = set()
        
        for job in all_jobs:
            if is_job_posted(job['id']):
                continue
            if job['id'] in seen_ids:
                continue
            
            # Simple keyword filtering if scraper didn't catch it
            # (Though scrapers should handle filtering)
            
            seen_ids.add(job['id'])
            unique_jobs.append(job)

        if not unique_jobs:
            logging.info("No new unique jobs found.")
            return

        # 3. Curation Logic (Cap at 30, Remote vs India balance)
        
        # Sort by posted time (most recent first) for trimming
        # Assuming 'posted_dt' is available in job dict (datetime object)
        # If not, we fall back to index/scrape order
        
        # We need to ensure scrapers return 'posted_dt'
        # For now, let's assume they might not, and rely on scrape order (which is usually recent first)
        # But let's try to add a 'created_at' timestamp if possible
        
        # unique_jobs.sort(key=lambda x: x.get('posted_dt', datetime.min).timestamp(), reverse=True)
        # Fix datetime.min timestamp issue
        unique_jobs.sort(key=lambda x: x.get('posted_dt', datetime(1970, 1, 1).replace(tzinfo=timezone.utc)).timestamp(), reverse=True)
        
        
        # Logic to split candidates
        def is_india_role(job):
            loc = job['location'].lower()
            return "india" in loc or any(city in loc for city in ["bangalore", "bengaluru", "hyderabad", "mumbai", "chennai", "delhi", "pune", "guegaon", "noida"])

        india_candidates = [j for j in unique_jobs if is_india_role(j)]
        remote_candidates = [j for j in unique_jobs if not is_india_role(j) and "remote" in j['location'].lower()]


        final_remote_jobs = []
        final_india_jobs = []
        
        # Logic: 
        # If remote > 15, take 15. If < 15, take all.
        num_remote_slots = min(len(remote_candidates), MAX_REMOTE_JOBS)
        final_remote_jobs = remote_candidates[:num_remote_slots]
        
        # Remaining slots for India
        remaining_slots = MAX_JOBS_PER_DAY - len(final_remote_jobs)
        num_india_slots = min(len(india_candidates), remaining_slots)
        final_india_jobs = india_candidates[:num_india_slots]
        
        # If we still have slots and more remote jobs, fill? 
        # User said: "If remote jobs available < 15, fill remaining slots with India roles"
        # Implies we favor filling slots with India if Remote is lacking.
        # But if Remote is overflowing (>15), we cap at 15.
        # What if India is overflowing? We cap at remaining.
        

        # Since limits are removed, we just take all unique_jobs
        final_jobs = unique_jobs
        
        # Mark as posted
        for job in final_jobs:
            mark_job_posted(job['id'], job['url'])

        # 4. Final Sort for Display
        # Remote First -> India Metro -> Role Type -> Company Name
        def sort_key_display(job):
            is_remote = "remote" in job['location'].lower()
            is_india = "india" in job['location'].lower() or any(c in job['location'].lower() for c in ["bangalore","delhi","mumbai","chennai","pune","hyderabad","gurgaon","noida"])
            return (
                0 if is_remote else 1,
                0 if is_india else 1,
                job['role'],
                job['company']
            )
        
        final_jobs.sort(key=sort_key_display)

        # 5. Format Output
        display_india = [j for j in final_jobs if is_india_role(j)]
        display_remote = [j for j in final_jobs if j not in display_india] # Remaining are remote
        
        date_str = datetime.now().strftime("%d %b %Y")
        
        # Build Message
        header = f"🚀 *Daily Tech Jobs Digest by VJ — {date_str}*\n\n"
        footer = f"\n🌍 {len(display_remote)} Remote | 🇮🇳 {len(display_india)} India | Total: {len(final_jobs)} jobs"

        message_body = ""
        
        def format_job_entry(job):
            # Truncate title
            title = job['role']
            if len(title) > 60:
                title = title[:57] + "..."
            
            flag = "🌍" if "remote" in job['location'].lower() else "🇮🇳" # Or use job.get('flag')
            
            # Calculate posted time string
            posted_str = get_posted_time_str(job.get('posted_dt'))
            
            return (
                f"*{title}*\n"
                f"🏢 {job['company']}\n"
                f"{flag} {job['location']}\n"
                f"🕐 {posted_str}\n"
                f"💰 {job['salary']}\n"
                f"🔗 [Apply Now]({job['url']})\n"
                f"🏷️ {job['source']}\n\n"
            )

        if display_remote:
            message_body += "🌍 *REMOTE ROLES*\n──────────────\n"
            for job in display_remote:
                message_body += format_job_entry(job)

        if display_india:
            if display_remote:
                message_body += "\n"
            message_body += "🇮🇳 *INDIA ROLES*\n──────────────\n"
            for job in display_india:
                message_body += format_job_entry(job)

        full_message = header + message_body + footer
        
        # 6. Send (with trimming if needed)
        # Telegram limit is 4096 chars.
        # If too long, we might need to cut jobs.
        if len(full_message) > 4000:
             # Trim jobs from end until it fits
             # This is a bit complex to do perfectly with markdown.
             # Simple approach: If > 4000, send multiple messages or just truncate the body.
             # User requested: "Single message only — trim content to fit Telegram's 4096 char limit"
             
             # We must fit it.
             while len(full_message) > 4000 and (display_remote or display_india):
                 # Remove last job from whichever list is at the bottom (India usually)
                 if display_india:
                     display_india.pop()
                 elif display_remote:
                     display_remote.pop()
                 
                 # Reconstruct
                 message_body = ""
                 if display_remote:
                     message_body += "🌍 *REMOTE ROLES*\n──────────────\n"
                     for job in display_remote:
                         message_body += format_job_entry(job)
                 if display_india:
                    if display_remote:
                        message_body += "\n"
                    message_body += "🇮🇳 *INDIA ROLES*\n──────────────\n"
                    for job in display_india:
                        message_body += format_job_entry(job)
                        
                 full_message = header + message_body + footer

        # Send
        response = bot.send_message(full_message)
        if response and response.get('ok'):
             # Pin
            pass # bot.pin_message(response['result']['message_id'])
            
        logging.info("Job scrape cycle completed successfully.")

    finally:
        fcntl.lockf(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

def main():
    init_db()
    logging.info("Job Scraper Service Started (APScheduler)")
    
    scheduler = BlockingScheduler(timezone=pytz.utc)
    
    # Parse Run Time
    hour, minute = map(int, RUN_TIME_UTC.split(':'))
    
    # Add job
    # "cron" trigger
    scheduler.add_job(run_job_scraping, CronTrigger(hour=hour, minute=minute, timezone=pytz.utc))
    
    # Run loop
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    main()
