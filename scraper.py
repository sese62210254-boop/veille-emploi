import requests
from bs4 import BeautifulSoup
import logging
import json
import concurrent.futures
from database import Database
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def est_vraie_opportunite(titre: str, resume: str) -> bool:
    """Filtre ultra-strict : Analyse structurelle et semantique de l'annonce."""
    texte = (titre + " " + resume).lower()
    
    titre_bas = titre.lower()
    
    # 1. Filtre Négatif ÉTENDU (Principalement sur le titre pour éviter les faux rejets)
    mots_bannis_titre = [
        "tournée", "visite", "atelier", "séminaire", "lancement officiel", 
        "rencontre", "audience", "conseil des ministres", "déploiement", 
        "célébration", "inauguration", "journée mondiale", "journée internationale", 
        "compte rendu", "adoption de", "remise de", "cérémonie", 
        "festival", "discours", "hommage", "journée nationale", "prise de contact", 
        "sensibilisation", "campagne", "examens", "bepc", "baccalauréat", "cep", "bac", "épreuves", "résultats"
    ]
    for mot in mots_bannis_titre:
        if mot in titre_bas:
            return False
            
    mots_bannis_absolus = ["décès", "nécrologie", "condoléances"]
    for mot in mots_bannis_absolus:
        if mot in texte:
            return False
            
    # 2. Mots-clés directs ULTRA-STRICTS (Phrases exactes, 0 ambiguïté)
    mots_directs_stricts = [
        # Emploi / Concours
        "appel à candidature", "appel à candidatures", "appel d'offre", "appels d'offres",
        "avis de recrutement", "termes de référence", "manifestation d'intérêt",
        "recrutement de", "recrutement d'un", "offre d'emploi", "job opening", 
        "job vacancy", "postes vacants",
        
        # NOUVEAU : Financement & Projets (Les vraies formules pour les subventions)
        "appel à projets", "appel à propositions", "fonds compétitif", 
        "guichet de financement", "soumission de projets", "pitch deck", 
        "soutien aux startups", "soutien aux pme", "financement des tpe"
    ]
    for mot in mots_directs_stricts:
        if mot in texte:
            return True
            
    # 3. Score Structurel : Analyse de la présence des marqueurs
    score = 0
    
    # Marqueurs de Délai (Commun à tous)
    if any(m in texte for m in ["délai", "date limite", "au plus tard", "jusqu'au", "clôture", "deadline"]):
        score += 3
        
    # Marqueurs d'Action (Commun à tous)
    if any(m in texte for m in ["postuler", "soumettre", "candidature", "dossier", "envoyer", "cv", "lettre de motivation", "tdr"]):
        score += 3
        
    # Marqueurs de Profil (Emploi/Bourse)
    if any(m in texte for m in ["profil", "expérience", "diplôme", "bac+", "compétences", "exigences", "qualification"]):
        score += 2
        
    # NOUVEAU : Marqueurs spécifiques au Financement / Projets
    if any(m in texte for m in ["critères d'éligibilité", "éligibles", "lignes directrices", "plan d'affaires", "business plan", "montant de la subvention", "enveloppe financière"]):
        score += 2
        
    # NOUVEAU : Marqueurs de Formation / Webinaire (Points Max)
    if any(m in texte for m in ["webinaire", "masterclass", "formation en ligne", "certificat", "séminaire de formation"]):
        score += 5
        
    return score >= 5


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
                
                # Nettoyage des liens pour eviter les doublons de session
                lien = lien.split('?session')[0]
                
                # Entreprise
                entreprise = "Non precisee"
                if selectors.get('company'):
                    emp_tag = offre.select_one(selectors['company'])
                    if emp_tag: entreprise = emp_tag.text.strip()
                
                # PRE-FILTRE : Empreinte connue ? (Titre + Source + Lien)
                if db.is_opportunity_known(lien, titre, source['name'], ""):
                    continue
                
                # EXTRACTION DE LA VRAIE DESCRIPTION
                resume_text = ""
                texte_complet_page = ""
                try:
                    detail_resp = requests.get(lien, headers=headers, timeout=10)
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    detail_elements = detail_soup.find_all(['p', 'li'])
                    bons_paragraphes = []
                    for element in detail_elements:
                        texte_p = element.text.replace('\n', ' ').strip()
                        if len(texte_p) > 60 and '{' not in texte_p and '<' not in texte_p:
                            if not texte_p.lower().startswith(titre.lower()[:30]):
                                bons_paragraphes.append(texte_p)
                    if bons_paragraphes:
                        texte_complet_page = " ".join(bons_paragraphes[:12])
                        resume_text = " ".join(bons_paragraphes[:4])
                except Exception as e:
                    pass
                
                if not texte_complet_page:
                    paragraphs = offre.find_all('p')
                    if paragraphs:
                        texte_complet_page = " ".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 20][:12])
                        resume_text = " ".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 20][:4])
                    else:
                        texte_complet_page = offre.text.replace('\n', ' ').replace('\r', '').strip()
                        resume_text = texte_complet_page
                
                if not resume_text:
                    resume_text = texte_complet_page

                texte_complet_page = ' '.join(texte_complet_page.split())
                resume_text = ' '.join(resume_text.split())
                
                # INTEGRATION DE L'INTELLIGENCE : Le robot juge l'opportunité sur 100% du texte
                if not est_vraie_opportunite(titre, texte_complet_page):
                    logger.debug(f"Annonce rejetée (Bruit) : {titre[:50]}")
                    continue
                
                resume = f"{resume_text[:250]}..." if len(resume_text) > 250 else resume_text
                
                # AUTO-CATÉGORISATION
                texte_complet = (titre + " " + resume_text).lower()
                type_opp = source['category']
                if 'stage' in texte_complet or 'stagiaire' in texte_complet:
                    type_opp = 'Stage'
                elif any(m in texte_complet for m in ['webinaire', 'formation', 'masterclass']):
                    type_opp = 'Formation'
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_generic, db, s) for s in sources]
        for future in concurrent.futures.as_completed(futures):
            total_new += future.result()
            
    logger.info(f"Scan termine. {total_new} nouvelles opportunites trouvees au total.")
