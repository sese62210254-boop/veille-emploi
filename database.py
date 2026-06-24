import sqlite3
from typing import List, Dict, Any
import logging
import os

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = "opportunites.db"):
        self.db_name = db_name
        self.known_links = set()
        self.init_db()
        self.supabase = self.init_supabase()
        self.load_known_links_from_supabase()


    def load_known_links_from_supabase(self):
        if self.supabase:
            try:
                response = self.supabase.table("opportunites").select("lien").execute()
                if hasattr(response, "data"):
                    for row in response.data:
                        if "lien" in row:
                            self.known_links.add(row["lien"])
                logger.info(f"{len(self.known_links)} liens connus charges depuis Supabase.")
            except Exception as e:
                logger.error(f"Erreur lors du chargement depuis Supabase: {e}")

    def init_supabase(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key and create_client:
            try:
                return create_client(url, key)
            except Exception as e:
                logger.error(f"Erreur d'initialisation Supabase: {e}")
                return None
        return None

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS opportunite (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titre TEXT NOT NULL,
                    lien TEXT UNIQUE NOT NULL,
                    resume TEXT,
                    source TEXT,
                    type TEXT,
                    date_limite TEXT,
                    date_decouverte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    envoye BOOLEAN DEFAULT 0
                )
            ''')
            conn.commit()

    def is_opportunity_known(self, lien: str) -> bool:
        if lien in self.known_links:
            return True
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM opportunite WHERE lien = ?', (lien,))
            return cursor.fetchone() is not None

    def add_opportunity(self, titre: str, lien: str, resume: str, source: str, type_opp: str, date_limite: str) -> bool:
        if self.is_opportunity_known(lien):
            return False
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO opportunite (titre, lien, resume, source, type, date_limite)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (titre, lien, resume, source, type_opp, date_limite))
                conn.commit()
                self.known_links.add(lien)
                
                # Double-enregistrement dans Supabase Cloud
                if self.supabase:
                    try:
                        self.supabase.table("opportunites").insert({
                            "titre": titre,
                            "lien": lien,
                            "resume": resume,
                            "source": source,
                            "type": type_opp,
                            "date_limite": date_limite
                        }).execute()
                    except Exception as e:
                        logger.error(f"Erreur lors de l'envoi vers Supabase: {e}")
                        
                return True
            except sqlite3.IntegrityError:
                return False

    def mark_as_sent(self, opp_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE opportunite SET envoye = 1 WHERE id = ?', (opp_id,))
            conn.commit()

    def get_unsent_opportunities(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM opportunite WHERE envoye = 0')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
