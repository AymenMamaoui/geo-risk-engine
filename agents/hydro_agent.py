# LLM with prompts

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from core.config import GROQ_API_KEY
from schemas.data_models import (
    HydrauliqueAnalysisReport,
    HydrauliqueRawExtraction,
    HydrauliqueOuedsExtraction
)


class HydroAgent:
    def __init__(self):
        # Utilisation du modèle 70b pour la précision
        self.llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")

        # Définit les outils de structuration
        self.struct_barrages = self.llm.with_structured_output(HydrauliqueRawExtraction)
        self.struct_oueds = self.llm.with_structured_output(HydrauliqueOuedsExtraction)
        self.struct_risque = self.llm.with_structured_output(HydrauliqueAnalysisReport)

    def analyser_barrages(self, texte: str):
        prompt = ChatPromptTemplate.from_template(
            "Extrais les données des barrages de ce texte : {texte}"
        )
        return (prompt | self.struct_barrages).invoke({"texte": texte})

    def analyser_oueds(self, texte: str):
        prompt = ChatPromptTemplate.from_template(
            "Extrais les données de vigilance des oueds de ce texte : {texte}"
        )
        return (prompt | self.struct_oueds).invoke({"texte": texte})

    def predire_risques_hydrauliques(self, data_barrages, data_oueds):
        # 1. FILTRAGE DÉTERMINISTE (Code Python infaillible)
        # On ne garde que les barrages >= 85.0% avant même de parler à l'IA
        barrages_filtres = [
            b for b in data_barrages.barrages
            if b.taux_remplissage_pourcentage is not None and b.taux_remplissage_pourcentage >= 85.0
        ]
        # On remplace la liste complète par la liste filtrée
        data_barrages.barrages = barrages_filtres

        # 2. PRÉPARATION DU CONTEXTE ÉPURÉ
        contexte = f"Barrages (>85% uniquement): {data_barrages.model_dump_json()}, Oueds: {data_oueds.model_dump_json()}"

        # 3. PROMPT SIMPLIFIÉ (L'IA fait ce qu'elle fait de mieux : du texte)
        system_prompt = """
        Tu es l'Agent Prédicteur des risques hydrologiques.
        Toutes les données que tu reçois sont DÉJÀ filtrées et nécessitent obligatoirement une alerte.

        1. RÈGLES DE CLASSIFICATION :
           - BARRAGES : Si taux >= 95% -> "CRITIQUE". Si taux entre 85% et 94.9% -> "HAUT".
           - OUEDS : Vigilance ROUGE -> "CRITIQUE". Vigilance ORANGE -> "HAUT".

        2. MAPPAGE DES NOMS :
           - Écris le nom complet. Ex: "Barrage ALLAL EL FASSI" ou "Oued Ouerrha".

        3. FORMAT DE JUSTIFICATION :
           - BARRAGES : "Le taux de remplissage du [Nom] est de [X]%, ce qui est [supérieur à 95% / compris entre 85% et 94.9%], donc un niveau de sévérité [Niveau]."
           - OUEDS : "Le débit de l'[Nom] est de [X] m3/s, ce qui indique un niveau de vigilance [Couleur], donc un niveau de sévérité [Niveau]."

        4. EXHAUSTIVITÉ :
           - Tu DOIS générer un objet pour CHAQUE infrastructure présente dans le contexte fourni.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyse ces données et génère le rapport structuré : {contexte}")
        ])

        return (prompt | self.struct_risque).invoke({"contexte": contexte})