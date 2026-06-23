from notifications import notify_all
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

message_test = """[Emploi] Développeur Web Junior \ Ceci est une offre de test.
🔗 Lien : https://example.com/offre
⏳ Date limite : 31/12/2026"""

print("Envoi du message de test...")
notify_all(message_test, subject="Message de Test - Veille")
print("Test terminé ! Vérifiez vos emails et WhatsApp.")
