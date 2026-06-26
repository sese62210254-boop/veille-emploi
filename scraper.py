import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests



from bs4 import BeautifulSoup



import logging



import json



import concurrent.futures



from database import Database



from urllib.parse import urljoin







logger = logging.getLogger(__name__)







import os



def analyser_avec_gemini(titre: str, texte: str) -> dict:

    """Analyse le texte via l'API Gemini 1.5 Flash pour determiner s'il s'agit d'une opportunite et extraire les metadonnees."""

    api_key = os.environ.get('GEMINI_API_KEY')

    if not api_key:

        logger.error("GEMINI_API_KEY non definie. Filtrage IA desactive.")

        return {"est_opportunite": True, "categorie": "Emploi", "resume": texte[:200], "date_limite": "Voir sur le site"}

    

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    

    prompt = f"""

Tu es un assistant IA spécialisé dans le recrutement et les financements au Bénin et en Afrique.

Voici un texte extrait d'une page web (titre et contenu).

Ta mission est d'analyser ce texte et de déterminer si c'est une VÉRITABLE opportunité concrète (Offre d'emploi, Stage, Bourse, Concours, Webinaire de formation, Appel à projet/financement) OU si c'est du "Bruit" (une simple actualité, une tournée ministérielle, un article de presse, une newsletter, des résultats d'examen).



Si c'est du bruit, tu dois répondre avec un objet JSON strictement comme ceci :

{{"est_opportunite": false}}



Si c'est une véritable opportunité, tu dois extraire les informations et répondre avec un objet JSON strictement comme ceci (ne rajoute pas de blocs markdown) :

{{

  "est_opportunite": true,

  "categorie": "Emploi", // Peut être "Emploi", "Stage", "Bourse", "Concours", ou "Formation"

  "resume": "Un résumé professionnel de 2 à 3 lignes maximum décrivant l'opportunité et les critères clés.",

  "date_limite": "JJ/MM/AAAA" // Ou "Non précisée"

}}



Texte à analyser :

Titre : {titre}

Contenu : {texte[:4000]}

"""



    payload = {

        "contents": [{"parts": [{"text": prompt}]}],

        "generationConfig": {"response_mime_type": "application/json"}

    }

    

    try:

        resp = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=20)

        resp.raise_for_status()

        data = resp.json()

        

        text_response = data['candidates'][0]['content']['parts'][0]['text']

        result = json.loads(text_response)

        return result

    except Exception as e:

        logger.error(f"Erreur Gemini sur '{titre[:30]}': {e}")

        # En cas d'erreur API, on rejette par prudence pour eviter le spam

        return {"est_opportunite": False}















def scrape_generic(db: Database, source: dict) -> int:



    """Scrapeur universel parametrable pour n'importe quel site"""



    url = source['url']



    selectors = source['selectors']



    logger.info(f"Analyse de [{source['name']}] : {url}...")



    



    count = 0



    try:



        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}



        response = requests.get(url, headers=headers, timeout=15, verify=False)



        response.raise_for_status()



        



        soup = BeautifulSoup(response.text, 'html.parser')



        offres = soup.select(selectors['container'])



        



        for offre in offres:



            try:
                logger.info(f'Trouvé élément html dans {source["name"]}')




                # Titre



                titre_tag = offre.select_one(selectors['title'])



                if not titre_tag:
                    logger.info(f'Pas de titre trouvé dans {source["name"]}')
                    continue



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
                logger.info(f'Trouvé élément html dans {source["name"]}')




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



