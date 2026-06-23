import sqlite3
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = "opportunites.db"):
        self.db_name = db_name
        self.init_db()

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
