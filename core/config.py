# Loading the api key (Groq in our case)
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("La clé API GROQ est manquante dans le fichier .env")