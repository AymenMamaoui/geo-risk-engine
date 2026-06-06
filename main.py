import sys
import os

# Ajout du répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports des agents et outils
from agents.meteo_agent import MeteoAgent
from agents.hydro_agent import HydroAgent
from tools.pdf_loader import extraire_texte_depuis_url


# Test de l'agent météorologique
def test_meteo_agent():
    print(f"\n--- Démarrage de la pipeline Météo ---")
    url_bulletin = "https://medias24.com/content/uploads/2026/02/02/Bulletin_meteo_alerte-2-fev.pdf"

    try:
        texte = extraire_texte_depuis_url(url_bulletin)
        agent = MeteoAgent()

        # 1. Extraction Brute
        print("[1/2] Structuration des données brutes...")
        donnees_brutes = agent.extraire_donnees(texte)

        # 2. Analyse et Prédiction (Génération du JSON final)
        print("[2/2] Aplatissement et prédiction des risques par province...")
        # Ajout de 'texte' comme second argument
        rapport_final = agent.predire_risques_meteo(donnees_brutes, texte)

        print("\n--- Analyse Météo Terminée ---")

        import json
        print(rapport_final.model_dump_json(indent=2))

    except Exception as e:
        print(f"Erreur Météo : {e}")

# Test de l'agent hydraulique
def test_hydro_agent():
    print(f"\n--- Démarrage de la pipeline Hydraulique ---")
    url_barrages = "https://lnt.ma/wp-content/uploads/2017/12/barrages.pdf"
    url_oueds = "https://pastebin.com/raw/w8USynG4"

    try:
        agent = HydroAgent()
        # Extraction
        data_b = agent.analyser_barrages(extraire_texte_depuis_url(url_barrages))
        data_o = agent.analyser_oueds(extraire_texte_depuis_url(url_oueds))

        # Prédiction des risques
        rapport = agent.predire_risques_hydrauliques(data_b, data_o)

        print("\n--- Analyse Hydraulique Terminée ---")
        for r in rapport.risques_hydrauliques:
            print(f"[{r.niveau_severite_agent}] {r.infrastructure_concernee}: {r.justification}")
    except Exception as e:
        print(f"Erreur Hydraulique : {e}")


    print(f"DEBUG - Nombre de barrages extraits : {len(data_b.barrages)}")


if __name__ == "__main__":
    # Il suffit de décommenter la fonction que je veux tester

    # test_meteo_agent()
     test_hydro_agent()