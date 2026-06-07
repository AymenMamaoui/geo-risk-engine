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
        # 1. FILTRAGE DÉTERMINISTE DES BARRAGES
        barrages_filtres = [
            b for b in data_barrages.barrages
            if b.taux_remplissage_pourcentage is not None and b.taux_remplissage_pourcentage >= 85.0
        ]
        data_barrages.barrages = barrages_filtres

        # 2. FILTRAGE DÉTERMINISTE DES OUEDS (Correction du nom de l'attribut : alertes_oueds)
        oueds_filtres = [
            o for o in data_oueds.alertes_oueds
            if o.niveau_vigilance is not None and o.niveau_vigilance.upper() in ["ROUGE", "ORANGE"]
        ]
        data_oueds.alertes_oueds = oueds_filtres

        # 3. PRÉPARATION DU CONTEXTE ÉPURÉ
        contexte = f"BARRAGES: {data_barrages.model_dump_json()}\nOUEDS: {data_oueds.model_dump_json()}"

        # 4. PROMPT DE FORMATAGE STRICT (Phrases exactes de n8n)
        system_prompt = """
        Tu es un formateur de données JSON strict.
        Toutes les données fournies sont déjà filtrées et nécessitent obligatoirement une alerte.

        RÈGLES DE FORMATAGE OBLIGATOIRES POUR LES BARRAGES :
        - infrastructure_concernee: "Barrage [Nom]" (ex: "Barrage ALLAL EL FASSI")
        - type_infrastructure: "BARRAGE"
        - indicateur_critique: "Remplissage: [X]%"
        - niveau_severite_agent: Si X >= 95.0 -> "CRITIQUE". Si X entre 85.0 et 94.9 -> "HAUT".
        - justification:
            Si CRITIQUE: "Le taux de remplissage du [Nom] est de [X]%, ce qui est considéré comme critique en raison de son dépassement du seuil de 95%."
            Si HAUT: "Le taux de remplissage du [Nom] est de [X]%, ce qui est considéré comme haut en raison de sa proximité avec le seuil critique de 85%."

        RÈGLES DE FORMATAGE OBLIGATOIRES POUR LES OUEDS :
        - infrastructure_concernee: "[Nom]" (ex: "Oued Ouerrha")
        - type_infrastructure: "OUED"
        - indicateur_critique: "Débit: [X] m3/s"
        - niveau_severite_agent: Si ROUGE -> "CRITIQUE". Si ORANGE -> "HAUT".
        - justification: 
            Si ROUGE: "Le débit de l'[Nom] est de [X] m3/s, ce qui est considéré comme critique en raison de son niveau de vigilance ROUGE."
            Si ORANGE: "Le débit de l'[Nom] est de [X] m3/s, ce qui est considéré comme haut en raison de son niveau de vigilance ORANGE."

        EXHAUSTIVITÉ : Génère un objet pour CHAQUE infrastructure présente dans le contexte.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Génère l'analyse avec les phrases exactes demandées : {contexte}")
        ])

        return (prompt | self.struct_risque).invoke({"contexte": contexte})