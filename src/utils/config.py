
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

# Job Filters (Hardcoded)
TARGET_LOCATIONS = ["Bangalore", "Remote", "Hyderabad", "Mumbai", "Chennai", "Pune", "Delhi"]
ROLES = ["developer", "tester", "devops"]

# Scraper Settings (Hardcoded)
SCRAPER_DELAY_SECONDS = 3
# Limits removed as requested by user
LOG_LEVEL = "INFO"
