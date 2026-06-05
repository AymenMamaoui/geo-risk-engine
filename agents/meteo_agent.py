from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from schemas.data_models import MeteoRawExtraction
from core.config import GROQ_API_KEY

# Test de l'agent Météorologique

class MeteoAgent:
    def __init__(self):
        # Initialisation du LLM
        self.llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")

        # Le "Structured Output" force le LLM à respecter le modèle Pydantic
        self.structured_llm = self.llm.with_structured_output(MeteoRawExtraction)

    def extraire_donnees(self, bulletin_texte: str):
        system_prompt = """
        Tu es un expert météorologique de haut niveau, spécialisé dans l'extraction de données structurées pour la protection civile. 
        Ta mission est d'extraire les données des bulletins DGM Maroc en respectant scrupuleusement le schéma JSON.

        Règles strictes :
        1. HIÉRARCHIE : Tu DOIS respecter l'imbrication : Phénomène -> Alertes -> details_zones. 
           - 'niveau_vigilance' et 'seuil_global' appartiennent à l'objet 'Alertes'.
           - 'provinces' et 'dates' appartiennent à l'objet 'details_zones'. 
           - Ne sors JAMAIS ces champs de leur hiérarchie.
        2. TEMPORALITÉ : Formate IMPÉRATIVEMENT les dates en "AAAA-MM-JJ HH:mm". 
           - Si une période couvre plusieurs jours, crée un objet distinct dans 'details_zones' pour chaque segment.
        3. ID BULLETIN : Extrais uniquement l'entier après "NR :".
        4. COMPLÉTUDE : Si une donnée est manquante, utilise null, ne laisse jamais un champ vide.
        5. FORMAT : Renvoie uniquement le JSON, aucun texte avant ou après.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyse ce bulletin et extrait les données : {bulletin}")
        ])

        chain = prompt | self.structured_llm
        return chain.invoke({"bulletin": bulletin_texte})