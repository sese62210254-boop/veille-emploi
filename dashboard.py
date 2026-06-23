import streamlit as st
import pandas as pd
import sqlite3
import os
import subprocess
from database import Database
from scraper import run_all_scrapers

# ... (les autres imports sont déjà en haut, on met à jour la ligne d'import du scraper)
# Attention, je vais plutôt chercher exactement la ligne import et l'appel.

# --- Configuration de la Page ---
st.set_page_config(page_title="Dashboard Veille", page_icon="🕵️", layout="wide")

# --- Styles Premium (CSS Personnalisé) ---
st.markdown("""
<style>
    /* Thème Sombre & Glassmorphism */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Titre Principal avec Dégradé */
    h1 {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    /* Cartes de KPI */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-title {
        font-size: 14px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #fff;
    }
    
    /* Boutons personnalisés */
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #4f46e5);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #1d4ed8, #4338ca);
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- Initialisation Base de Données ---
@st.cache_resource
def get_db():
    return Database("opportunites.db")

db = get_db()

# --- HEADER ---
st.title("Système de Veille Automatisée")
st.markdown("<p style='color: #94a3b8; margin-bottom: 2rem;'>Surveillance en temps réel des offres d'emploi et concours au Bénin.</p>", unsafe_allow_html=True)

# --- Fonctionnalités ---
def load_data():
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT id, titre, resume, source, date_decouverte, envoye, lien FROM opportunite ORDER BY id DESC", conn)
    conn.close()
    return df

df = load_data()

# --- KPIs ---
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-title'>Total des Offres</div>
        <div class='metric-value'>{len(df)}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-title'>Nouvelles (Non envoyées)</div>
        <div class='metric-value'>{len(df[df['envoye'] == 0])}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-title'>Sources actives</div>
        <div class='metric-value'>{df['source'].nunique() if not df.empty else 0}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# --- Onglets ---
tab1, tab2, tab3 = st.tabs(["📋 Base de données des Offres", "⚙️ Contrôle Manuel", "🔧 Configuration API"])

with tab1:
    st.subheader("Dernières Opportunités Extraites")
    
    # Filtres
    recherche = st.text_input("Rechercher un mot-clé (ex: Comptable, Développeur)...")
    
    # Affichage du DataFrame
    if not df.empty:
        df_display = df.copy()
        
        # Formatage de l'affichage
        df_display['Statut'] = df_display['envoye'].apply(lambda x: "✅ Envoyé" if x else "⏳ En attente")
        df_display['Date'] = pd.to_datetime(df_display['date_decouverte']).dt.strftime('%d/%m/%Y %H:%M')
        
        if recherche:
            df_display = df_display[df_display['titre'].str.contains(recherche, case=False, na=False) | df_display['resume'].str.contains(recherche, case=False, na=False)]
            
        st.dataframe(
            df_display[['Date', 'titre', 'resume', 'source', 'Statut', 'lien']],
            column_config={
                "lien": st.column_config.LinkColumn("Lien vers l'offre"),
                "titre": st.column_config.TextColumn("Poste / Titre", width="medium"),
                "resume": st.column_config.TextColumn("Résumé / Entreprise", width="large")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Aucune offre n'a encore été trouvée.")

with tab2:
    st.subheader("Forcer la recherche immédiatement")
    st.write("Le robot scanne les sites automatiquement toutes les heures en arrière-plan. Vous pouvez utiliser ce bouton pour déclencher une recherche manuelle instantanément.")
    
    if st.button("🚀 Lancer le Scraping Maintenant"):
        with st.spinner("Scraping en cours sur tous les sites..."):
            run_all_scrapers(db)
            st.success("Scraping terminé ! Les nouvelles offres vont être envoyées par e-mail et WhatsApp si le robot principal tourne.")
            st.rerun()

    st.markdown("---")
    st.subheader("🧠 Ajouter une Source avec l'I.A.")
    st.write("Collez le lien d'un site d'emploi. L'I.A. va l'analyser et trouver comment extraire les offres toute seule !")
    
    col_url, col_nom, col_cat = st.columns([3, 2, 2])
    with col_url:
        new_url = st.text_input("URL du site (ex: https://site.com/jobs)")
    with col_nom:
        new_nom = st.text_input("Nom du site (Optionnel)")
    with col_cat:
        new_cat = st.selectbox("Catégorie", ["Emploi", "Bourse", "Concours"])
        
    if st.button("✨ Analyser et Ajouter"):
        if new_url:
            with st.spinner("L'Intelligence Artificielle analyse le site... Cela peut prendre 10 à 20 secondes."):
                cmd = ["python", "ai_trainer.py", new_url, new_nom, new_cat]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                
                if "Succès" in result.stdout:
                    st.success(f"Le site a été compris et ajouté avec succès !\n\n{result.stdout.split('✅')[-1]}")
                else:
                    st.error("L'I.A. n'a pas pu analyser ce site de façon fiable.")
                    with st.expander("Voir les détails techniques"):
                        st.code(result.stdout + result.stderr)
        else:
            st.warning("Veuillez entrer une URL.")

with tab3:
    st.subheader("Statut des Connexions")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    def check_env(var_name):
        val = os.getenv(var_name)
        return "🟢 Configuré" if val and val.strip() != "" else "🔴 Manquant"
        
    colA, colB = st.columns(2)
    with colA:
        st.markdown(f"**WhatsApp CallMeBot Phone:** {check_env('WHATSAPP_PHONE')}")
        st.markdown(f"**WhatsApp API Key:** {check_env('WHATSAPP_API_KEY')}")
        
    with colB:
        st.markdown(f"**Gmail Sender:** {check_env('GMAIL_SENDER')}")
        st.markdown(f"**Gmail Password:** {check_env('GMAIL_APP_PASSWORD')}")
