import time
import schedule
import logging
from database import Database
import os
import json

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db = Database("opportunites.db")

def formatter_message(opp: dict) -> str:
    """Formate l'opportunité selon votre modèle."""
    msg = f"[{opp['type']}] {opp['titre']} \\ {opp['resume']}\n"
    msg += f"🔗 Lien : {opp['lien']}\n"
    msg += f"📅 Date limite : {opp['date_limite']}"
    return msg

def send_push_notification(nouvelles_count):
    if not firebase_admin:
        logger.warning("Firebase Admin SDK non installé.")
        return
        
    service_account_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not service_account_str:
        logger.warning("Variable FIREBASE_SERVICE_ACCOUNT manquante.")
        return
        
    try:
        service_account_info = json.loads(service_account_str)
        cred = credentials.Certificate(service_account_info)
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            
        message = messaging.Message(
            notification=messaging.Notification(
                title='🚀 Lynha Opportunité',
                body=f'{nouvelles_count} nouvelle(s) opportunité(s) vous attendent !',
            ),
            topic='nouvelles_offres',
        )
        response = messaging.send(message)
        logger.info(f'Notification Push envoyée avec succès : {response}')
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la notification Push : {e}")

def job_scraping():
    logger.info("Démarrage du cycle de recherche...")
    from scraper import run_all_scrapers
    
    # Lancement du moteur de scraping asynchrone global
    run_all_scrapers(db)
    
    # Récupérer les nouvelles opportunités non envoyées
    nouvelles = db.get_unsent_opportunities()
    
    if not nouvelles:
        logger.info("Aucune nouvelle opportunité trouvée.")
        return

    logger.info(f"{len(nouvelles)} nouvelle(s) opportunité(s) à envoyer !")
    
    # Envoi de la notification Push sur les téléphones
    send_push_notification(len(nouvelles))
    
    for opp in nouvelles:
        message = formatter_message(opp)
        logger.info(f"Préparation de l'envoi :\n{message}")
        
        # Envoi des autres notifications (WhatsApp, Telegram, Gmail)
        from notifications import notify_all
        notify_all(message=message, subject=f"Nouvelle offre : {opp['titre']}")
        
        # Marquer comme envoyé une fois que c'est fait
        db.mark_as_sent(opp['id'])

if __name__ == "__main__":
    logger.info("Lancement du système de veille sur GitHub Actions...")
    job_scraping()
