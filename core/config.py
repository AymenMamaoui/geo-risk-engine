# Loading the api key (Groq in our case)
import os
from dotenv import load_dotenv

load_dotenv()

# Chargement avec exception de l'API Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("La clé API GROQ est manquante dans le fichier .env")

# Email
EMAIL_ADDRESS   = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD")
ALERT_EMAIL_TO  = os.getenv("ALERT_EMAIL_TO")

# Twilio
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER  = os.getenv("TWILIO_PHONE_NUMBER")
ALERT_SMS_TO         = os.getenv("ALERT_SMS_TO")