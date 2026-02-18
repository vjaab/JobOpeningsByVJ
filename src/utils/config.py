
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

# WhatsApp Settings
WHATSAPP_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_RECIPIENT = os.getenv('WHATSAPP_RECIPIENT_PHONE_NUMBER')

# Job Filters (Hardcoded)
TARGET_LOCATIONS = ["Bangalore", "Remote", "Hyderabad", "Mumbai", "Chennai", "Pune", "Delhi"]
ROLES = ["developer", "tester", "devops"]

# Scraper Settings (Hardcoded)
SCRAPER_DELAY_SECONDS = 3
RUN_TIME_UTC = "10:30"
LOG_LEVEL = "INFO"
