import sqlite3
from typing import List, Dict, Any
import logging
import os
import threading

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = "opportunites.db"):
        self.db_name = db_name
        self.known_links = set()
        self.known_fingerprints = set()
        self.lock = threading.Lock()
        
        self.init_db()
        self.supabase = self.init_supabase()
        self.load_known_data()

    def get_fingerprint(self, titre: str, source: str, resume: str) -> str:
        t = titre.lower().strip() if titre else ""
        s = source.lower().strip() if source else ""
        r = resume.lower().strip()[:50] if resume else ""
        return f"{t}|{s}|{r}"

    def load_known_data(self):
        if self.supabase:
            try:
                response = self.supabase.table("opportunites").select("lien, titre, source, resume").execute()
                if hasattr(response, "data"):
                    for row in response.data:
                        if "lien" in row:
                            self.known_links.add(row["lien"])
                        if "titre" in row and "source" in row:
                            fp = self.get_fingerprint(row.get("titre", ""), row.get("source", ""), row.get("resume", ""))
                            self.known_fingerprints.add(fp)
                logger.info(f"{len(self.known_links)} liens et empreintes uniques chargés depuis Supabase.")
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
            cursor.execute("""
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
            """)
            conn.commit()

    def is_opportunity_known(self, lien: str, titre: str = "", source: str = "", resume: str = "") -> bool:
        with self.lock:
            if lien in self.known_links:
                return True
            fp = self.get_fingerprint(titre, source, resume)
            if fp in self.known_fingerprints:
                return True
            return False

    def add_opportunity(self, titre: str, lien: str, resume: str, source: str, type_opp: str, date_limite: str) -> bool:
        with self.lock:
            fp = self.get_fingerprint(titre, source, resume)
            if lien in self.known_links or fp in self.known_fingerprints:
                return False
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO opportunite (titre, lien, resume, source, type, date_limite)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (titre, lien, resume, source, type_opp, date_limite))
                    conn.commit()
                    
                    self.known_links.add(lien)
                    self.known_fingerprints.add(fp)
                    
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
            cursor.execute("UPDATE opportunite SET envoye = 1 WHERE id = ?", (opp_id,))
            conn.commit()

    def get_unsent_opportunities(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM opportunite WHERE envoye = 0")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
