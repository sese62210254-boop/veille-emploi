import logging
from main import job_scraping

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Lancement du scraping via GitHub Actions (Exécution unique)")
    try:
        job_scraping()
        logger.info("Exécution terminée avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution : {e}")
