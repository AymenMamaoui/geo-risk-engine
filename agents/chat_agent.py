"""
chat_agent.py — Assistant conversationnel Geo-Risk Maroc

Répond aux questions de l'utilisateur sur la SITUATION COURANTE
(le dernier rapport de l'orchestrateur, conservé dans _state).

Ce n'est pas encore du RAG documentaire : il n'y a pas de vector store.
L'agent injecte simplement l'état courant dans le prompt (grounding).
La base documentaire DGM + l'upload de bulletins viendront ensuite.

Modèle : llama-3.1-8b-instant (léger, rapide, cohérent avec l'orchestrateur).
Multi-session : l'agent est SANS ÉTAT — l'historique est fourni à chaque
appel par le frontend, jamais stocké côté serveur.
"""
from __future__ import annotations

from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.config import GROQ_API_KEY


class ChatAgent:
    def __init__(self):
        # Modèle léger pour la conversation temps réel
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.1-8b-instant",
            temperature=0.3,   # bas : on veut des réponses factuelles, ancrées
            max_tokens=800,
        )

    # Construction du contexte à partir du state courant

    def _construire_contexte(self, state: Dict[str, Any]) -> str:
        """
        Transforme le _state du dashboard en un bloc texte lisible
        que le LLM utilisera comme unique source de vérité.
        """
        if not state or not state.get("zones"):
            return "AUCUN RAPPORT DISPONIBLE. Le moteur Geo-Risk n'a pas encore produit d'analyse."

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

            # Recommandations (structure : liste de tuples (role, [lignes]))
            recos = z.get("recos", [])
            if recos:
                for role, items in recos:
                    lignes.append(f"  • Recommandations {role} :")
                    for item in items:
                        lignes.append(f"      - {item}")

        # Synthèse globale si présente
        if state.get("synthese_globale"):
            lignes.append(f"\nSYNTHÈSE GLOBALE :\n{state['synthese_globale']}")

        return "\n".join(lignes)


    # Prompt système
    def _system_prompt(self, contexte: str) -> str:
        return f"""Tu es l'Assistant Geo-Risk Maroc, un copilote d'aide à la décision pour la surveillance des risques d'inondation au Maroc.

RÈGLES STRICTES :
1. Tu réponds UNIQUEMENT à partir des données de situation ci-dessous. Tu n'inventes JAMAIS de chiffres, de zones ou de recommandations.
2. Si l'information demandée n'est pas dans les données, dis-le clairement : « Cette information n'est pas disponible dans le rapport actuel. »
3. Tu réponds en français, de manière claire et concise, adaptée à un contexte de gestion de crise.
4. Quand tu cites un niveau d'alerte, un débit ou un pourcentage, reprends exactement la valeur des données.
5. Tu ne donnes pas de conseils médicaux ou juridiques ; tu relaies les recommandations officielles présentes dans le rapport.
6. Reste factuel et opérationnel. Pas de spéculation sur l'évolution future non documentée.

═══════════════════════════════════════════════
DONNÉES DE SITUATION COURANTE (source unique de vérité)
═══════════════════════════════════════════════
{contexte}
═══════════════════════════════════════════════
"""


    # Point d'entrée principal

    def repondre(
        self,
        question: str,
        state: Dict[str, Any],
        historique: List[Dict[str, str]] | None = None,
    ) -> str:
        """
        Génère une réponse à la question de l'utilisateur.

        Paramètres :
          - question   : la question courante (str)
          - state      : le _state du dashboard (situation courante)
          - historique : liste de messages précédents, format
                         [{"role": "user"|"assistant", "content": "..."}]
                         fournie par le FRONTEND (multi-session sans état)

        Retour : la réponse textuelle de l'assistant.
        """
        contexte = self._construire_contexte(state)

        # On reconstruit la conversation pour le LLM
        messages = [SystemMessage(content=self._system_prompt(contexte))]

        # Historique fourni par le client (limité aux 10 derniers échanges pour rester sous la limite de tokens du tier gratuit)
        if historique:
            for msg in historique[-10:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # Question courante
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