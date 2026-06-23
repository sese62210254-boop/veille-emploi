import os
import sys
import json
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Configuration Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Erreur : Clé API Gemini manquante dans le fichier .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def clean_html_for_ai(html_content):
    """
    Nettoie le HTML pour ne garder que la structure sémantique essentielle
    afin de ne pas saturer l'IA avec du code inutile (CSS, JS, SVG...).
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Supprimer les balises inutiles
    for tag in soup(["script", "style", "svg", "path", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()
        
    # Nettoyer les attributs inutiles mais garder id, class et href
    for tag in soup.find_all(True):
        attrs_to_keep = {}
        for attr in ['id', 'class', 'href']:
            if tag.has_attr(attr):
                attrs_to_keep[attr] = tag[attr]
        tag.attrs = attrs_to_keep
        
    # Extraire une portion représentative (le corps de la page, souvent le main)
    main_content = soup.find('main') or soup.find('body') or soup
    
    # Limiter la taille pour l'IA (garder les 20000 premiers caractères)
    cleaned_html = str(main_content)
    return cleaned_html[:20000]

def analyze_site_with_ai(url, name=None, category="Emploi"):
    """
    Demande à Gemini de trouver les sélecteurs CSS pour extraire les offres.
    """
    print(f"Analyse du site {url} en cours par l'I.A...")
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur lors du téléchargement de la page : {e}")
        return False
        
    print("Nettoyage du code HTML...")
    cleaned_html = clean_html_for_ai(response.text)
    
    prompt = f"""
    Tu es un expert en Web Scraping et BeautifulSoup.
    Voici le code HTML nettoyé d'une page qui liste des offres d'emploi ou des bourses d'études.
    Ton but est de me donner les sélecteurs CSS EXACTS pour extraire les informations.
    
    HTML:
    ```html
    {cleaned_html}
    ```
    
    Trouve les sélecteurs CSS pour :
    1. "container" : Le conteneur parent qui englobe UNE offre (ex: 'article.job', '.card', '.job-bx').
    2. "title" : Le sélecteur pour le titre de l'offre, RELATIF au container (ex: 'h3 a', '.job-title'). Doit pointer vers l'élément contenant le texte du titre.
    3. "company" : Le sélecteur pour le nom de l'entreprise, RELATIF au container (ex: '.company-name'). S'il n'y en a pas, met une chaîne vide "".
    4. "link" : Le sélecteur pour le lien (balise <a>) de l'offre, RELATIF au container (ex: 'h3 a', 'a.read-more').
    
    Réponds UNIQUEMENT avec un objet JSON valide, sans aucun formatage Markdown ni commentaire.
    Exemple de réponse attendue :
    {{
        "container": "div.job-item",
        "title": "h2.title a",
        "company": "span.company-name",
        "link": "h2.title a"
    }}
    """
    
    print("Demande de réflexion à Google Gemini...")
    try:
        ai_response = model.generate_content(prompt)
        result_text = ai_response.text.strip()
        
        # Nettoyer si Gemini renvoie des backticks markdown
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        selectors = json.loads(result_text.strip())
        print(f"L'I.A. a trouvé les sélecteurs : {selectors}")
        
        # Enregistrement dans sources.json
        if not name:
            domain = urlparse(url).netloc.replace('www.', '')
            name = domain.split('.')[0].capitalize()
            
        new_source = {
            "name": name,
            "url": url,
            "category": category,
            "selectors": selectors
        }
        
        sources_file = "sources.json"
        sources = []
        if os.path.exists(sources_file):
            with open(sources_file, 'r', encoding='utf-8') as f:
                sources = json.load(f)
                
        # Remplacer si existe déjà
        sources = [s for s in sources if s['url'] != url]
        sources.append(new_source)
        
        with open(sources_file, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=4, ensure_ascii=False)
            
        print(f"Succès ! Le site {name} a été configuré automatiquement et ajouté à sources.json.")
        return True
        
    except Exception as e:
        print(f"L'I.A. a échoué : {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_trainer.py <URL> [Nom] [Categorie]")
    else:
        url = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else None
        cat = sys.argv[3] if len(sys.argv) > 3 else "Emploi"
        analyze_site_with_ai(url, name, cat)
