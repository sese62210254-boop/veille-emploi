import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, messaging

load_dotenv()
logger = logging.getLogger(__name__)

def send_whatsapp_callmebot(phone_number: str, api_key: str, message: str):
    """Envoie un message WhatsApp via CallMeBot."""
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={requests.utils.quote(message)}&apikey={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("Message WhatsApp envoyé avec succès.")
        else:
            logger.error(f"Erreur CallMeBot WhatsApp: {response.text}")
    except Exception as e:
        logger.error(f"Erreur d'envoi WhatsApp: {e}")

def send_telegram_message(bot_token: str, chat_id: str, message: str):
    """Envoie un message Telegram via l'API officielle."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info("Message Telegram envoyé avec succès.")
        else:
            logger.error(f"Erreur Telegram: {response.text}")
    except Exception as e:
        logger.error(f"Erreur d'envoi Telegram: {e}")

def send_email_gmail(sender_email: str, app_password: str, receiver_email: str, subject: str, message_body: str):
    """Envoie un e-mail via le serveur SMTP de Gmail."""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message_body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        logger.info("E-mail envoyé avec succès.")
    except Exception as e:
        logger.error(f"Erreur d'envoi d'e-mail: {e}")


# Initialisation de Firebase
def init_firebase():
    if not firebase_admin._apps:
        # Essayer de lire depuis la variable d'environnement (Secret GitHub)
        service_account_info = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if service_account_info:
            try:
                import json
                cred_dict = json.loads(service_account_info)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialisé avec succès depuis la variable d'environnement.")
                return True
            except Exception as e:
                logger.error(f"Erreur lors du parsing du JSON Firebase : {e}")
        else:
            logger.warning("Aucune configuration Firebase trouvée. Les notifications Push sont désactivées.")
    return len(firebase_admin._apps) > 0

def send_firebase_push(title: str, body: str):
    """Envoie une notification Push Firebase à tous les utilisateurs abonnés au topic 'nouvelles_offres'."""
    if not init_firebase():
        return
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            topic='nouvelles_offres',
        )
        response = messaging.send(message)
        logger.info(f"Notification Firebase envoyée avec succès : {response}")
    except Exception as e:
        logger.error(f"Erreur d'envoi de notification Firebase : {e}")

def notify_all(message: str, subject: str = "Nouvelle Opportunité !"):
    """Fonction principale pour envoyer les notifications sur tous les canaux configurés."""
    
    # --- WhatsApp ---
    wa_phone = os.getenv("WHATSAPP_PHONE")
    wa_apikey = os.getenv("WHATSAPP_API_KEY")
    if wa_phone and wa_apikey:
        send_whatsapp_callmebot(wa_phone, wa_apikey, message)
        
    # --- Telegram ---
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat_id:
        send_telegram_message(tg_token, tg_chat_id, message)
        
    # --- Gmail ---
    gmail_sender = os.getenv("GMAIL_SENDER")
    gmail_pwd = os.getenv("GMAIL_APP_PASSWORD")
    gmail_receiver = os.getenv("GMAIL_RECEIVER")
    if gmail_sender and gmail_pwd and gmail_receiver:
        send_email_gmail(gmail_sender, gmail_pwd, gmail_receiver, subject, message)
    
    # --- Firebase Push Notifications (Mobile App) ---
    send_firebase_push(title=subject, body=message[:200] + ("..." if len(message) > 200 else ""))
