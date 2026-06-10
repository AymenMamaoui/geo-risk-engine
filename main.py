import sys
import os
import json
import time

# Ajout du répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports des agents et outils
from agents.meteo_agent import MeteoAgent
from agents.hydro_agent import HydroAgent
from agents.orchestrator import OrchestratorAgent
from tools.pdf_loader import extraire_texte_depuis_url


def run_geo_risk_engine():
    print("======================================================")
    print(" DÉMARRAGE DU GEO-RISK ENGINE MAROC")
    print("======================================================\n")

    # URLs des sources de données
    url_meteo = "https://medias24.com/content/uploads/2026/02/02/Bulletin_meteo_alerte-2-fev.pdf"
    url_barrages = "https://lnt.ma/wp-content/uploads/2017/12/barrages.pdf"
    url_oueds = "https://pastebin.com/raw/w8USynG4"

    try:
        # ---------------------------------------------------------
        # ÉTAPE 1 : PIPELINE MÉTÉO
        # ---------------------------------------------------------
        print("--- [1/3] Pipeline Météo ---")
        texte_meteo = extraire_texte_depuis_url(url_meteo)
        agent_meteo = MeteoAgent()
        donnees_brutes_meteo = agent_meteo.extraire_donnees(texte_meteo)
        rapport_meteo = agent_meteo.predire_risques_meteo(donnees_brutes_meteo, texte_meteo)
        print(" Alertes Météo générées avec succès.\n")

        # ---------------------------------------------------------
        # ÉTAPE 2 : PIPELINE HYDRAULIQUE
        # ---------------------------------------------------------
        print("--- [2/3] Pipeline Hydraulique ---")
        texte_barrages = extraire_texte_depuis_url(url_barrages)
        texte_oueds = extraire_texte_depuis_url(url_oueds)

        agent_hydro = HydroAgent()
        data_barrages = agent_hydro.analyser_barrages(texte_barrages)
        data_oueds = agent_hydro.analyser_oueds(texte_oueds)
        rapport_hydro = agent_hydro.predire_risques_hydrauliques(data_barrages, data_oueds)
        print(" Alertes Hydrauliques générées avec succès.\n")

        # ---------------------------------------------------------
        # ÉTAPE 3 : L'ORCHESTRATEUR (CROISEMENT DES RISQUES)
        # ---------------------------------------------------------
        print("--- [3/3] Intelligence Centrale (Orchestrateur) ---")
        print("⏳ Pause de 60 secondes pour respecter le quota de l'API Groq (TPM)...")
        time.sleep(65)
        orchestrator = OrchestratorAgent()
        rapport_final = orchestrator.generer_synthese_globale(rapport_meteo, rapport_hydro)

        print("\n======================================================")
        print(" RAPPORT FINAL DE CONFLUENCE DES RISQUES")
        print("======================================================")

        # Affichage du JSON final combiné
        print(rapport_final.model_dump_json(indent=2))

    except Exception as e:
        print(f"\n ERREUR CRITIQUE DANS LE MOTEUR : {e}")


if __name__ == "__main__":
    run_geo_risk_engine()