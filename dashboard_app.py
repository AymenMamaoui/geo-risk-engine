"""
dashboard_app.py — Serveur FastAPI du Centre de Crise Geo-Risk Maroc
Lancer : python dashboard_app.py  →  http://localhost:8000
"""

import os
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict
from agents.chat_agent import ChatAgent
from tools.pdf_loader import extraire_texte_depuis_bytes
from demo_data import DEMO_REPORT

app = FastAPI(title="Geo-Risk Maroc Dashboard")

chat_agent = ChatAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")),
    autoescape=False,
    auto_reload=False,
)

def render(template_name: str, **ctx) -> HTMLResponse:
    tmpl = jinja_env.get_template(template_name)
    return HTMLResponse(content=tmpl.render(**ctx))


# ─── Schéma entrant (structure réelle de l'orchestrateur) ────────────────────

class ConfluenceRisque(BaseModel):
    localisation_impactee:   str
    niveau_alerte_combine:   str
    synthese_decisionnelle:  str
    recommandations_terrain: str

class GeoRiskReportIn(BaseModel):
    confluences_risques_majeurs: List[ConfluenceRisque]


class ChatMessage(BaseModel):
    role: str      # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    historique: Optional[List[ChatMessage]] = []
    # bulletins fournis par le client : {"meteo": "...", "hydro": "..."}
    bulletins: Optional[Dict[str, str]] = None


# ─── Normalisation niveau ─────────────────────────────────────────────────────

NIVEAU_MAP = {
    "urgence noire":    "URGENCE_NOIRE",
    "alerte rouge":     "ALERTE_ROUGE",
    "vigilance orange": "VIGILANCE_ORANGE",
    "normal":           "NORMAL",
}

def normaliser(texte: str) -> str:
    return NIVEAU_MAP.get(texte.lower().strip(), "VIGILANCE_ORANGE")

def niveau_global(confluences: List[ConfluenceRisque]) -> str:
    for p in ["URGENCE_NOIRE", "ALERTE_ROUGE", "VIGILANCE_ORANGE", "NORMAL"]:
        if any(normaliser(c.niveau_alerte_combine) == p for c in confluences):
            return p
    return "NORMAL"


# ─── Parsing recommandations → liste de tuples (role, [lignes]) ──────────────
# On utilise des TUPLES et des LISTES, jamais des dicts,
# pour éviter tout conflit avec les méthodes Python dans Jinja2.

def parse_recommandations(texte: str):
    """Retourne une liste de tuples : (role_str, [ligne1, ligne2, ...])"""
    sections = []
    for bloc in texte.split("Pour les "):
        bloc = bloc.strip()
        if not bloc:
            continue
        colon_idx = bloc.find(":")
        if colon_idx == -1:
            continue
        role = bloc[:colon_idx].strip()
        contenu = bloc[colon_idx + 1:]
        lignes = []
        for line in contenu.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            # Retire "1." ou "1)" en début
            rest = line[1:].lstrip(". )").strip()
            if rest:
                lignes.append(rest)
        if role and lignes:
            sections.append((role, lignes))   # TUPLE, pas dict
    return sections


# ─── État global : tout en types primitifs Python (str, list, tuple) ─────────

_state = {
    "date_rapport":     "—",
    "niveau_global":    "NORMAL",
    "synthese_globale": "En attente du premier rapport du moteur Geo-Risk...",
    "nb_zones":         0,
    "zones":            [],   # liste de dicts avec uniquement str/list/tuple
}


def _construire_state_depuis_rapport(rapport: dict) -> dict:
    """
    Transforme un rapport brut (format /api/report) en _state,
    en réutilisant EXACTEMENT la même logique que la vraie route.
    """
    confluences = rapport.get("confluences_risques_majeurs", [])

    # niveau global : on réutilise la logique, mais sur des dicts bruts
    ng = "NORMAL"
    for p in ["URGENCE_NOIRE", "ALERTE_ROUGE", "VIGILANCE_ORANGE", "NORMAL"]:
        if any(normaliser(c["niveau_alerte_combine"]) == p for c in confluences):
            ng = p
            break

    zones = []
    for c in confluences:
        recos = parse_recommandations(c["recommandations_terrain"])
        zones.append({
            "province": c["localisation_impactee"],
            "niveau": normaliser(c["niveau_alerte_combine"]),
            "niveau_label": c["niveau_alerte_combine"].upper(),
            "synthese": c["synthese_decisionnelle"],
            "recos": recos,
        })

    return {
        "date_rapport": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "niveau_global": ng,
        "synthese_globale": " — ".join(c["synthese_decisionnelle"] for c in confluences),
        "nb_zones": len(zones),
        "zones": zones,
    }


USE_DEMO_DATA = os.getenv("USE_DEMO_DATA", "true").lower() == "true"

if USE_DEMO_DATA:
    _state = _construire_state_depuis_rapport(DEMO_REPORT)
    print("[Dashboard] State initialisé avec les données de démonstration.")

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return render("dashboard.jinja", **_state)

@app.post("/api/report")
async def update_report(report: GeoRiskReportIn):
    global _state
    confluences = report.confluences_risques_majeurs
    ng = niveau_global(confluences)

    zones = []
    for c in confluences:
        recos = parse_recommandations(c.recommandations_terrain)
        zones.append({
            "province":        c.localisation_impactee,
            "niveau":          normaliser(c.niveau_alerte_combine),
            "niveau_label":    c.niveau_alerte_combine.upper(),
            "synthese":        c.synthese_decisionnelle,
            "recos":           recos,   # list of (role, [lignes])
        })

    _state = {
        "date_rapport":     datetime.now().strftime("%d/%m/%Y %H:%M"),
        "niveau_global":    ng,
        "synthese_globale": " — ".join(c.synthese_decisionnelle for c in confluences),
        "nb_zones":         len(zones),
        "zones":            zones,
    }
    print(f"[Dashboard]  Rapport reçu — niveau: {ng} | {len(zones)} zones")
    return {"status": "ok", "niveau_global": ng, "zones": len(zones)}

@app.get("/api/report")
async def get_report():
    return {"niveau_global": _state["niveau_global"], "zones": _state["nb_zones"]}

@app.get("/health")
async def health():
    return {"status": "running", "last_update": _state["date_rapport"]}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    historique = [{"role": m.role, "content": m.content} for m in (req.historique or [])]

    reponse = chat_agent.repondre(
        question=req.question,
        state=_state,
        historique=historique,
        bulletins=req.bulletins,  # <- transmis au LLM comme contexte
    )
    return {"reponse": reponse}


@app.post("/api/chat/upload")
async def upload_bulletin(
        fichier: UploadFile = File(...),
        type_bulletin: str = Form(...),  # "meteo" ou "hydro"
):
    # Validation du type
    if type_bulletin not in ("meteo", "hydro"):
        return {"ok": False, "erreur": "Type invalide. Attendu : 'meteo' ou 'hydro'."}

    # Lecture des bytes du fichier uploadé
    contenu = await fichier.read()

    # Garde-fou taille (ex : 10 Mo max)
    if len(contenu) > 10 * 1024 * 1024:
        return {"ok": False, "erreur": "Fichier trop volumineux (max 10 Mo)."}

    # Extraction via la brique pdf_loader
    texte = extraire_texte_depuis_bytes(contenu, filename=fichier.filename or "")

    if not texte or texte.startswith("Erreur"):
        return {"ok": False, "erreur": texte or "Extraction impossible."}

    # On renvoie le texte au frontend, qui le renverra avec les prochaines questions
    return {
        "ok": True,
        "type": type_bulletin,
        "filename": fichier.filename,
        "texte": texte,
        "apercu": texte[:200] + ("..." if len(texte) > 200 else ""),
    }
if __name__ == "__main__":
    print("=" * 54)
    print("  GEO-RISK DASHBOARD — http://localhost:8000")
    print("=" * 54)
    uvicorn.run("dashboard_app:app", host="0.0.0.0", port=8000, reload=False)