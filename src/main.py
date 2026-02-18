
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


        # Since limits are removed, we just take all unique_jobs
        # But we still sort/split for display purposes
        
        # Combine everything (no capping logic needed anymore)
        all_candidates = india_candidates + remote_candidates
        
        # Priority and Company Capping Logic
        # 1. Sort by Priority (Developer > Others)
        def get_priority_score(job):
            role = job['role'].lower()
            if any(k in role for k in ["developer", "software engineer", "sde", "backend", "frontend", "full stack"]):
                return 0 # High priority
            return 1 # Lower priority
            
        all_candidates.sort(key=lambda x: (get_priority_score(x), x.get('company')))

        # 2. Cap per company (Max 5)
        company_counts = {}
        final_jobs = []
        for job in all_candidates:
            company = job['company']
            count = company_counts.get(company, 0)
            if count >= 5:
                continue
            company_counts[company] = count + 1
            final_jobs.append(job)
        
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
        
        # Build Messages (Multi-part)
        header = f"🚀 *Daily Tech Jobs Digest by VJ — {date_str}*\n\n"
        footer = f"\n🌍 {len(display_remote)} Remote | 🇮🇳 {len(display_india)} India | Total: {len(final_jobs)} jobs"

        
        messages = []
        current_message = header
        
        def format_job_entry(job):
            # Truncate title
            title = job['role']
            if len(title) > 60:
                title = title[:57] + "..."
            
            flag = "🌍" if "remote" in job['location'].lower() else "🇮🇳" # Or use job.get('flag')
            
            # Calculate posted time string
            posted_str = get_posted_time_str(job.get('posted_dt'))
            
            # Basic salary if missing
            salary = job.get('salary', 'Not disclosed')
            if not salary: salary = 'Not disclosed'

            return (
                f"*{title}*\n"
                f"🏢 {job['company']}\n"
                f"{flag} {job['location']}\n"
                f"🕐 {posted_str}\n"
                f"💰 {salary}\n"
                f"🔗 [Apply Now]({job['url']})\n"
                f"🏷️ {job['source']}\n\n"
            )

        def add_text_to_messages(new_text, section_title=None, is_footer=False, is_job=False):
            nonlocal current_message, messages
            
            # If section title provided
            if section_title:
                text_to_add = section_title
            else:
                text_to_add = new_text

            # Check length safety (Telegram limit ~4096)
            if len(current_message) + len(text_to_add) > 3800:
                messages.append(current_message)
                if is_footer:
                     # Footer should be on new message if doesn't fit
                     current_message = text_to_add
                elif section_title:
                     # New section starts on new message
                     current_message = text_to_add
                elif is_job:
                     # Continuation header for job liist
                     current_message = f"*(Continuation)*\n\n{text_to_add}"
                else:
                     current_message = text_to_add
            else:
                current_message += text_to_add

        if display_remote:
            add_text_to_messages("", section_title="🌍 *REMOTE ROLES*\n──────────────\n")
            for job in display_remote:
                add_text_to_messages(format_job_entry(job), is_job=True)

        if display_india:
            # Separator if needed
            if display_remote:
                add_text_to_messages("\n")
            
            add_text_to_messages("", section_title="🇮🇳 *INDIA ROLES*\n──────────────\n")
            for job in display_india:
                add_text_to_messages(format_job_entry(job), is_job=True)

        # Add footer
        add_text_to_messages(footer, is_footer=True)
        
        # Append final message
        if current_message:
            messages.append(current_message)
        
        # 6. Send All Messages
        for msg in messages:
            response = bot.send_message(msg)
            if not (response and response.get('ok')):
                 logging.error(f"Failed to send message part: {response}")
            import time
            time.sleep(1) # Rate limit

        logging.info("Job scrape cycle completed successfully.")

        # 7. WhatsApp Logic
        from src.utils.whatsapp_bot import send_whatsapp_message
        
        wa_messages = []
        wa_current_message = header 
        
        def format_job_entry_wa(job):
            # Truncate title
            title = job['role']
            if len(title) > 60:
                title = title[:57] + "..."
            
            flag = "🌍" if "remote" in job['location'].lower() else "🇮🇳"
            
            # Calculate posted time string
            posted_str = get_posted_time_str(job.get('posted_dt'))
            
            # Basic salary if missing
            salary = job.get('salary', 'Not disclosed')
            if not salary: salary = 'Not disclosed'

            # WhatsApp uses plain text URL
            return (
                f"*{title}*\n"
                f"🏢 {job['company']}\n"
                f"{flag} {job['location']}\n"
                f"🕐 {posted_str}\n"
                f"💰 {salary}\n"
                f"🔗 Apply: {job['url']}\n"
                f"🏷️ {job['source']}\n\n"
            )

        def add_text_wa(new_text, section_title=None, is_footer=False, is_job=False):
            nonlocal wa_current_message, wa_messages
            
            if section_title:
                text_to_add = section_title
            else:
                text_to_add = new_text

            # WhatsApp limit ~4000
            if len(wa_current_message) + len(text_to_add) > 3800:
                wa_messages.append(wa_current_message)
                if is_footer:
                     wa_current_message = text_to_add
                elif section_title:
                     wa_current_message = text_to_add
                elif is_job:
                     wa_current_message = f"*(Continuation)*\n\n{text_to_add}"
                else:
                     wa_current_message = text_to_add
            else:
                wa_current_message += text_to_add

        if display_remote:
            add_text_wa("", section_title="🌍 *REMOTE ROLES*\n──────────────\n")
            for job in display_remote:
                add_text_wa(format_job_entry_wa(job), is_job=True)

        if display_india:
            if display_remote:
                add_text_wa("\n")
            
            add_text_wa("", section_title="🇮🇳 *INDIA ROLES*\n──────────────\n")
            for job in display_india:
                add_text_wa(format_job_entry_wa(job), is_job=True)

        # Add footer
        add_text_wa(footer, is_footer=True)
        
        # Append final message
        if wa_current_message:
            wa_messages.append(wa_current_message)
        
        # Send All WhatsApp Messages
        for msg in wa_messages:
            send_whatsapp_message(msg)
            time.sleep(1) 

        logging.info("WhatsApp delivery cycle completed.")

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
