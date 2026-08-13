import sys
import os
import json
import time
import httpx

# Ajout du répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports des agents et outils
from agents.meteo_agent import MeteoAgent
from agents.hydro_agent import HydroAgent
from agents.orchestrator import OrchestratorAgent
from agents.notifier_agent import NotifierAgent
from tools.pdf_loader import extraire_texte_depuis_url

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000/api/report")


def push_to_dashboard(rapport) -> bool:
    """
    Envoie le rapport final au dashboard FastAPI.
    Retourne True si l'envoi a réussi, False sinon (sans lever d'exception).
    """
    try:
        response = httpx.post(
            DASHBOARD_URL,
            content=rapport.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        response.raise_for_status()
        print(f" Dashboard mis à jour → {DASHBOARD_URL}  [HTTP {response.status_code}]")
        return True
    except httpx.ConnectError:
        print(f" Dashboard injoignable ({DASHBOARD_URL}) — ignoré.")
    except httpx.HTTPStatusError as e:
        print(f" Erreur HTTP dashboard : {e.response.status_code} — {e.response.text[:120]}")
    except Exception as e:
        print(f" Erreur inattendue lors du push dashboard : {e}")
    return False


def run_geo_risk_engine():
    print("======================================================")
    print(" DÉMARRAGE DU GEO-RISK ENGINE MAROC")
    print("======================================================\n")

    url_meteo    = "https://medias24.com/content/uploads/2026/02/02/Bulletin_meteo_alerte-2-fev.pdf"
    url_barrages = "https://lnt.ma/wp-content/uploads/2017/12/barrages.pdf"
    url_oueds    = "https://pastebin.com/raw/w8USynG4"

    try:
        # ---------------------------------------------------------
        # ÉTAPE 1 : PIPELINE MÉTÉO
        # ---------------------------------------------------------
        print("--- [1/5] Pipeline Météo ---")
        texte_meteo = extraire_texte_depuis_url(url_meteo)
        agent_meteo = MeteoAgent()
        donnees_brutes_meteo = agent_meteo.extraire_donnees(texte_meteo)
        rapport_meteo = agent_meteo.predire_risques_meteo(donnees_brutes_meteo, texte_meteo)
        print(" Alertes Météo générées avec succès.\n")

        # ---------------------------------------------------------
        # ÉTAPE 2 : PIPELINE HYDRAULIQUE
        # ---------------------------------------------------------
        print("--- [2/5] Pipeline Hydraulique ---")
        texte_barrages = extraire_texte_depuis_url(url_barrages)
        texte_oueds    = extraire_texte_depuis_url(url_oueds)

        agent_hydro  = HydroAgent()
        data_barrages = agent_hydro.analyser_barrages(texte_barrages)
        data_oueds    = agent_hydro.analyser_oueds(texte_oueds)
        rapport_hydro = agent_hydro.predire_risques_hydrauliques(data_barrages, data_oueds)
        print(" Alertes Hydrauliques générées avec succès.\n")

        # ---------------------------------------------------------
        # ÉTAPE 3 : ORCHESTRATEUR (CROISEMENT DES RISQUES)
        # ---------------------------------------------------------
        print("--- [3/5] Intelligence Centrale (Orchestrateur) ---")
        print(" Pause de 65 secondes pour respecter le quota Groq (TPM)...")
        time.sleep(65)

        orchestrator = OrchestratorAgent()
        rapport_final = orchestrator.generer_synthese_globale(rapport_meteo, rapport_hydro)

        print("\n======================================================")
        print(" RAPPORT FINAL DE CONFLUENCE DES RISQUES")
        print("======================================================")
        print(rapport_final.model_dump_json(indent=2))

        # ---------------------------------------------------------
        # ÉTAPE 4 : PUSH VERS LE DASHBOARD
        # ---------------------------------------------------------
        print("\n--- [4/5] Dashboard FastAPI ---")
        push_to_dashboard(rapport_final)

        # ---------------------------------------------------------
        # ÉTAPE 5 : NOTIFICATIONS (SMS & EMAIL)
        # ---------------------------------------------------------
        print("\n--- [5/5] Agent Notificateur (Diffusion des Alertes) ---")
        notifier = NotifierAgent()
        notifier.process_notifications(rapport_final.model_dump())

    except Exception as e:
        print(f"\n ERREUR CRITIQUE DANS LE MOTEUR : {e}")
        raise  # re-raise pour avoir la traceback complète en dev


if __name__ == "__main__":
    run_geo_risk_engine()