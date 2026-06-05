import sys
import os

# Ajout du répertoire racine au PYTHONPATH pour permettre les imports depuis 'agents' et 'schemas'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.meteo_agent import MeteoAgent
from tools.pdf_loader import extraire_texte_depuis_url


def run_meteo_pipeline():
    # URL du bulletin PDF
    url_bulletin = "https://medias24.com/content/uploads/2026/02/02/Bulletin_meteo_alerte-2-fev.pdf"

    print(f"--- Démarrage de la pipeline Météo ---")

    try:
        # 1. Extraction du texte depuis le PDF
        print(f"[1/2] Extraction du texte depuis : {url_bulletin}...")
        texte_bulletin = extraire_texte_depuis_url(url_bulletin)

        if not texte_bulletin.strip():
            print("Erreur : Le texte extrait est vide.")
            return

        # 2. Analyse par l'Agent IA
        print(f"[2/2] Analyse par l'Agent Météorologique...")
        agent = MeteoAgent()
        resultat = agent.extraire_donnees(texte_bulletin)

        # 3. Affichage du résultat structuré
        print("\n--- Analyse Terminée ---")
        print(f"Bulletin ID: {resultat.id_bulletin}")
        for phenomene in resultat.phenomenes:
            print(f"\nPhénomène détecté : {phenomene.type_phenomene}")
            for alerte in phenomene.alertes:
                print(f" - Niveau vigilance : {alerte.niveau_vigilance}")
                print(f" - Zones : {[zone.provinces for zone in alerte.details_zones]}")

    except Exception as e:
        print(f"\nUne erreur est survenue lors de l'exécution : {e}")


if __name__ == "__main__":
    run_meteo_pipeline()