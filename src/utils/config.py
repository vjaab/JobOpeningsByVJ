
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')

# Job Filters
TARGET_LOCATIONS = os.getenv('TARGET_LOCATIONS', 'Bangalore,Remote,Hyderabad').split(',')
ROLES = os.getenv('ROLES', 'developer,engineer,devops,sre,tester').split(',')

# Scraper Settings
SCRAPER_DELAY_SECONDS = int(os.getenv('SCRAPER_DELAY_SECONDS', 3))
MAX_JOBS_PER_DAY = int(os.getenv('MAX_JOBS_PER_DAY', 30))
MAX_REMOTE_JOBS = int(os.getenv('MAX_REMOTE_JOBS', 15))
MAX_INDIA_JOBS = int(os.getenv('MAX_INDIA_JOBS', 15))
RUN_TIME_UTC = os.getenv('RUN_TIME_UTC', '10:30')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
