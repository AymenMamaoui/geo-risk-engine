"""
chat_agent.py — Assistant conversationnel Geo-Risk Maroc
─────────────────────────────────────────────────────────
Répond aux questions sur :
  1. la SITUATION COURANTE (le dernier rapport de l'orchestrateur, _state)
  2. les BULLETINS UPLOADÉS par l'utilisateur (météo et/ou hydraulique)

Toujours pas de vector store : on injecte le texte dans le contexte.
Multi-session : l'agent est SANS ÉTAT. Historique ET bulletins sont
fournis à chaque appel par le frontend, jamais stockés côté serveur.

Modèle : llama-3.1-8b-instant.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.config import GROQ_API_KEY


class ChatAgent:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=800,
        )


    # Contexte : situation courante (_state)


    def _construire_contexte_situation(self, state: Dict[str, Any]) -> str:
        if not state or not state.get("zones"):
            return "AUCUN RAPPORT SYSTÈME DISPONIBLE. Le moteur Geo-Risk n'a pas encore produit d'analyse."

        lignes = [
            f"NIVEAU GLOBAL D'ALERTE : {state.get('niveau_global', 'INCONNU')}",
            f"DATE DU RAPPORT : {state.get('date_rapport', '—')}",
            f"NOMBRE DE ZONES ANALYSÉES : {state.get('nb_zones', 0)}",
            "",
            "DÉTAIL DES ZONES À RISQUE :",
        ]
        for i, z in enumerate(state.get("zones", []), start=1):
            lignes.append(f"\n[Zone {i}] {z.get('province', '—')}")
            lignes.append(f"  • Niveau d'alerte : {z.get('niveau_label', z.get('niveau', '—'))}")
            lignes.append(f"  • Synthèse : {z.get('synthese', '—')}")
            recos = z.get("recos", [])
            if recos:
                for role, items in recos:
                    lignes.append(f"  • Recommandations {role} :")
                    for item in items:
                        lignes.append(f"      - {item}")

        if state.get("synthese_globale"):
            lignes.append(f"\nSYNTHÈSE GLOBALE :\n{state['synthese_globale']}")

        return "\n".join(lignes)


    # Contexte : bulletins uploadés par l'utilisateur


    def _construire_contexte_bulletins(self, bulletins: Optional[Dict[str, str]]) -> str:
        """
        bulletins : dict optionnel {"meteo": "texte...", "hydro": "texte..."}
        Chaque clé est présente seulement si l'utilisateur a uploadé ce type.
        """
        if not bulletins:
            return ""

        blocs = []
        if bulletins.get("meteo"):
            blocs.append(
                "═══ BULLETIN MÉTÉOROLOGIQUE (uploadé par l'utilisateur) ═══\n"
                + bulletins["meteo"][:6000]   # borne de sécurité tokens
            )
        if bulletins.get("hydro"):
            blocs.append(
                "═══ BULLETIN HYDRAULIQUE (uploadé par l'utilisateur) ═══\n"
                + bulletins["hydro"][:6000]
            )

        if not blocs:
            return ""

        return "\n\n".join(blocs)


    # Prompt système

    def _system_prompt(self, contexte_situation: str, contexte_bulletins: str) -> str:
        bloc_bulletins = ""
        if contexte_bulletins:
            bloc_bulletins = f"""

═══════════════════════════════════════════════
DOCUMENTS UPLOADÉS PAR L'UTILISATEUR
(bulletins bruts, à analyser à la demande)
═══════════════════════════════════════════════
{contexte_bulletins}
═══════════════════════════════════════════════
"""

        return f"""Tu es l'Assistant Geo-Risk Maroc, un copilote d'aide à la décision pour la surveillance des risques d'inondation au Maroc.

RÈGLES STRICTES :
1. Tu réponds UNIQUEMENT à partir des données fournies ci-dessous (situation système et/ou bulletins uploadés). Tu n'inventes JAMAIS de chiffres, de zones ou de recommandations.
2. Distingue toujours clairement TROIS sources possibles :
   - la SITUATION COURANTE produite par le moteur (rapport officiel) ;
   - le BULLETIN MÉTÉOROLOGIQUE uploadé par l'utilisateur, s'il existe ;
   - le BULLETIN HYDRAULIQUE uploadé par l'utilisateur, s'il existe.
   Quand tu réponds, précise sur quelle source tu t'appuies.
3. Si l'information demandée n'est dans aucune source, dis-le : « Cette information n'est pas disponible dans les données actuelles. »
4. Les bulletins uploadés sont du texte BRUT extrait de PDF : ils peuvent être mal formatés. Fais de ton mieux pour en extraire l'information pertinente (zones, niveaux de vigilance, précipitations, débits, taux de remplissage) sans jamais inventer.
5. Tu réponds en français, de façon claire, concise et opérationnelle.
6. Quand tu cites un niveau, un débit ou un pourcentage, reprends exactement la valeur de la source.

═══════════════════════════════════════════════
SITUATION COURANTE (moteur Geo-Risk)
═══════════════════════════════════════════════
{contexte_situation}
═══════════════════════════════════════════════{bloc_bulletins}
"""

    # Point d'entrée principal
    def repondre(
        self,
        question: str,
        state: Dict[str, Any],
        historique: Optional[List[Dict[str, str]]] = None,
        bulletins: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Paramètres :
          - question   : question courante
          - state      : _state du dashboard (situation courante)
          - historique : messages précédents [{"role","content"}], fourni par le client
          - bulletins  : dict optionnel {"meteo": "...", "hydro": "..."} fourni par le client
        """
        contexte_situation = self._construire_contexte_situation(state)
        contexte_bulletins = self._construire_contexte_bulletins(bulletins)

        messages = [SystemMessage(content=self._system_prompt(contexte_situation, contexte_bulletins))]

        if historique:
            for msg in historique[-10:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=question))

        try:
            reponse = self.llm.invoke(messages)
            return reponse.content.strip()
        except Exception as e:
            print(f"[ChatAgent] Erreur LLM : {e}")
            return (
                "Désolé, une erreur est survenue lors du traitement de votre question. "
                "Veuillez réessayer dans quelques instants."
            )