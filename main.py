import time
import schedule
import logging
from database import Database

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db = Database("opportunites.db")

def formatter_message(opp: dict) -> str:
    """Formate l'opportunité selon votre modèle."""
    msg = f"[{opp['type']}] {opp['titre']} \\ {opp['resume']}\n"
    msg += f"🔗 Lien : {opp['lien']}\n"
    msg += f"⏳ Date limite : {opp['date_limite']}"
    return msg

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
    
    for opp in nouvelles:
        message = formatter_message(opp)
        logger.info(f"Préparation de l'envoi :\n{message}")
        
        # Envoi des notifications (WhatsApp, Telegram, Gmail selon configuration)
        from notifications import notify_all
        notify_all(message=message, subject=f"Nouvelle offre : {opp['titre']}")
        
        # Marquer comme envoyé une fois que c'est fait
        db.mark_as_sent(opp['id'])

if __name__ == "__main__":
    logger.info("Lancement du système de veille en local...")
    
    # Pour tester immédiatement au lancement :
    job_scraping()
    
    # Planifier toutes les heures
    schedule.every(1).hours.do(job_scraping)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
