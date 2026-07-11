
import requests
import logging
from src.utils.config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_RECIPIENT

logger = logging.getLogger(__name__)

def send_whatsapp_message(message):
    """
    Sends a message to WhatsApp via Facebook Graph API.
    Splits messages if they exceed the limit.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID or not WHATSAPP_RECIPIENT:
        logger.error("WhatsApp config missing. Skipping send.")
        return False

    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }

    # WhatsApp character limit ~4096 (safe limit 4000)
    max_length = 4000
    messages = []
    
    if len(message) > max_length:
        logger.warning(f"Message length {len(message)} exceeds limit. Splitting...")
        parts = message.split('\n\n')
        current_chunk = ""
        for part in parts:
             if len(current_chunk) + len(part) + 2 > max_length:
                 messages.append(current_chunk)
                 current_chunk = part + "\n\n"
             else:
                 current_chunk += part + "\n\n"
        if current_chunk:
            messages.append(current_chunk)
    else:
        messages = [message]

    success = True
    for i, msg_part in enumerate(messages):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": WHATSAPP_RECIPIENT,
            "type": "text",
            "text": {
                "body": msg_part,
                "preview_url": False # Disabled to improve delivery reliability
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp message part {i+1}/{len(messages)} sent successfully")
            else:
                logger.error(f"WhatsApp Send Failed: {response.status_code} - {response.text}")
                success = False
        except Exception as e:
            logger.error(f"WhatsApp Connection Error: {e}")
            success = False
            
    return success

def upload_media(file_path):
    """
    Uploads a local file to WhatsApp/Facebook Graph API and returns its media_id.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("WhatsApp config missing. Skipping upload.")
        return None

    # Note that WhatsApp media upload endpoint uses the phone ID
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/media"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}'
    }
    
    import os
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, 'application/pdf')
            }
            data = {
                'messaging_product': 'whatsapp'
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            if response.status_code in [200, 201]:
                media_id = response.json().get('id')
                logger.info(f"WhatsApp media upload successful. ID: {media_id}")
                return media_id
            else:
                logger.error(f"WhatsApp Media Upload Failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"WhatsApp Media Upload Error: {e}")
        return None

def send_whatsapp_document(media_id, filename):
    """
    Sends a document message using a WhatsApp media ID.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID or not WHATSAPP_RECIPIENT:
        logger.error("WhatsApp config missing. Skipping send.")
        return False

    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": WHATSAPP_RECIPIENT,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code in [200, 201]:
            logger.info("WhatsApp document sent successfully")
            return True
        else:
            logger.error(f"WhatsApp Document Send Failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"WhatsApp Document Send Error: {e}")
        return False

def send_whatsapp_file(file_path):
    """
    Uploads and sends a file via WhatsApp.
    """
    import os
    media_id = upload_media(file_path)
    if media_id:
        return send_whatsapp_document(media_id, os.path.basename(file_path))
    return False

