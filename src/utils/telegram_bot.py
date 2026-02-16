
import os
import requests
import logging
import time
from dotenv import load_dotenv

load_dotenv()

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        self.admin_chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')

    def send_message(self, text, chat_id=None, parse_mode='Markdown', retries=3):
        if not chat_id:
            chat_id = self.channel_id
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        for attempt in range(retries):
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logging.warning(f"Failed to send message (attempt {attempt+1}/{retries}): {e}")
                time.sleep(2 ** attempt)
        
        logging.error(f"Failed to send Telegram message after {retries} attempts")
        return None

    def edit_message(self, message_id, text, chat_id=None, parse_mode='Markdown', retries=3):
        if not chat_id:
            chat_id = self.channel_id
            
        url = f"https://api.telegram.org/bot{self.token}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        for attempt in range(retries):
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logging.warning(f"Failed to edit message (attempt {attempt+1}/{retries}): {e}")
                time.sleep(2 ** attempt)

        logging.error(f"Failed to edit message after {retries} attempts")
        return None

    def pin_message(self, message_id, chat_id=None):
        if not chat_id:
            chat_id = self.channel_id
            
        url = f"https://api.telegram.org/bot{self.token}/pinChatMessage"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        try:
            requests.post(url, json=payload, timeout=10)
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to pin message: {e}")

    def send_admin_alert(self, message):
        if self.admin_chat_id:
            self.send_message(f"⚠️ ADMIN ALERT: {message}", chat_id=self.admin_chat_id)
