import time
import subprocess
import re

def run_massive_import():
    file_path = r"C:\Users\Fred\.gemini\antigravity\brain\4f758af4-a9d1-441b-b690-ae2aef1f9a10\sources_a_ajouter.md"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extraire toutes les URLs du fichier markdown
    urls = re.findall(r'https?://[^\s]+', content)
    
    print(f"Demarrage de l'import massif de {len(urls)} sites par l'I.A. Gemini !")
    print("----------------------------------------------------------------------")
    
    success_count = 0
    for i, url in enumerate(urls):
        print(f"\n[{i+1}/{len(urls)}] Analyse de : {url}")
        
        # Par défaut, on classe dans "Emploi" mais on pourrait raffiner
        cat = "Bourse" if "bourse" in url.lower() or "scholarship" in url.lower() else "Emploi"
        
        try:
            result = subprocess.run(["python", "ai_trainer.py", url, "", cat], capture_output=True, text=True, encoding='utf-8', errors='replace')
            if "Succès" in result.stdout:
                print("Integre avec succes !")
                success_count += 1
            else:
                print("Echec (Site probablement protege par securite anti-bot ou structure trop complexe).")
        except Exception as e:
            print(f"Erreur d'exécution : {e}")
            
        # Pause de 4 secondes pour respecter les limites de l'API gratuite Gemini (15 requêtes / minute)
        time.sleep(4)
        
    print("\n=======================================================")
    print(f"IMPORT TERMINE ! {success_count} nouveaux sites configures avec succes.")
    
    # Lancement du scraper pour tout récupérer
    print("Mise à jour de la base de données avec toutes les nouvelles offres...")
    subprocess.run(["python", "-c", "from database import Database; from scraper import run_all_scrapers; db = Database(); run_all_scrapers(db)"])
    print("Tout est pret !")

if __name__ == "__main__":
    run_massive_import()
