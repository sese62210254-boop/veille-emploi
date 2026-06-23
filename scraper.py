import requests
from bs4 import BeautifulSoup
import logging
import json
import concurrent.futures
from database import Database
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def scrape_generic(db: Database, source: dict) -> int:
    """Scrapeur universel parametrable pour n'importe quel site"""
    url = source['url']
    selectors = source['selectors']
    logger.info(f"Analyse de [{source['name']}] : {url}...")
    
    count = 0
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        offres = soup.select(selectors['container'])
        
        for offre in offres:
            try:
                # Titre
                titre_tag = offre.select_one(selectors['title'])
                if not titre_tag: continue
                titre = titre_tag.text.strip()
                
                # Lien
                lien_tag = offre.select_one(selectors['link'])
                lien = lien_tag['href'] if lien_tag else url
                lien = urljoin(url, lien)
                
                entreprise = "Non precisee"
                if selectors.get('company'):
                    emp_tag = offre.select_one(selectors['company'])
                    if emp_tag: entreprise = emp_tag.text.strip()
                
                # NETTOYAGE INTELLIGENT DU RÉSUMÉ
                # On essaie d'abord de prendre les paragraphes (souvent la vraie description)
                paragraphs = offre.find_all('p')
                if paragraphs:
                    resume_text = " ".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 20])
                else:
                    resume_text = offre.text.replace('\n', ' ').replace('\r', '').strip()
                
                # On nettoie les espaces multiples
                resume_text = ' '.join(resume_text.split())
                
                # On enlève le titre s'il est au début du résumé pour éviter la répétition
                if resume_text.startswith(titre):
                    resume_text = resume_text[len(titre):].strip()
                    
                resume = f"{resume_text[:200]}..." if len(resume_text) > 200 else resume_text
                
                # AUTO-CATÉGORISATION
                texte_complet = (titre + " " + resume).lower()
                type_opp = source['category']
                if 'stage' in texte_complet or 'stagiaire' in texte_complet:
                    type_opp = 'Stage'
                elif 'bourse' in texte_complet or 'scholarship' in texte_complet:
                    type_opp = 'Bourse'
                elif 'concours' in texte_complet:
                    type_opp = 'Concours'
                elif 'emploi' in texte_complet or 'recrute' in texte_complet:
                    type_opp = 'Emploi'
                
                added = db.add_opportunity(
                    titre=titre[:100],
                    lien=lien,
                    resume=resume,
                    source=source['name'],
                    type_opp=type_opp,
                    date_limite="Voir sur le site"
                )
                if added: count += 1
                
            except Exception as e:
                pass
                
    except Exception as e:
        logger.error(f"Erreur scraping {source['name']} : {e}")
        
    return count

def run_all_scrapers(db: Database):
    """Lance le moteur Multi-Thread sur toutes les sources configurees"""
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            sources = json.load(f)
    except FileNotFoundError:
        logger.error("Le fichier sources.json est introuvable.")
        return

    logger.info(f"Lancement du moteur asynchrone sur {len(sources)} sites en meme temps...")
    
    total_new = 0
    # Multi-Threading Magique : 10 requetes simultanees
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # On lance tous les scrapers en parallele
        futures = [executor.submit(scrape_generic, db, s) for s in sources]
        
        for future in concurrent.futures.as_completed(futures):
            total_new += future.result()
            
    logger.info(f"Scan termine. {total_new} nouvelles opportunites trouvees au total.")

