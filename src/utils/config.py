
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')

# Job Filters (Hardcoded)
TARGET_LOCATIONS = ["Bangalore", "Remote", "Hyderabad", "Mumbai", "Chennai", "Pune", "Delhi"]
ROLES = ["developer", "tester", "devops"]

# Scraper Settings (Hardcoded)
SCRAPER_DELAY_SECONDS = 3
MAX_JOBS_PER_DAY = 30
MAX_REMOTE_JOBS = 15
MAX_INDIA_JOBS = 15
RUN_TIME_UTC = "10:30"
LOG_LEVEL = "INFO"
