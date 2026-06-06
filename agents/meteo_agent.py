from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from schemas.data_models import MeteoRawExtraction, MeteoAnalysisReport, ZoneRisqueMeteo
from core.config import GROQ_API_KEY


class MeteoAgent:
    def __init__(self):
        # 1. SOLUTION TECHNIQUE : Augmenter max_tokens pour éviter les coupures JSON
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.3-70b-versatile",
            max_tokens=4096  # Permet au modèle de générer des listes très longues
        )

        self.struct_raw = self.llm.with_structured_output(MeteoRawExtraction)
        self.struct_analyse = self.llm.with_structured_output(MeteoAnalysisReport)

    def extraire_donnees(self, bulletin_texte: str):
        system_prompt = """
        Tu es un expert météorologique de haut niveau. 
        Ta mission est d'extraire les données des bulletins DGM Maroc.

        1. HIÉRARCHIE : Respecte l'imbrication Phénomène -> Alertes -> details_zones.
        2. TEMPORALITÉ : Formate les dates en "AAAA-MM-JJ HH:mm".
        3. ID BULLETIN : Extrais uniquement l'entier après "NR :".
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyse ce bulletin et extrait les données brutes : {bulletin}")
        ])

        return (prompt | self.struct_raw).invoke({"bulletin": bulletin_texte})

    def predire_risques_meteo(self, donnees_brutes, texte_original):
        toutes_les_zones_urgentes = []
        id_bul = donnees_brutes.id_bulletin

        # Typologie pour reproduire le meme schéma que n8n
        villes_cotieres = ["Tanger-Assilah", "MDiq-Fnideq", "Larache", "Kenitra", "Sale", "Rabat", "Al Hoceima"]
        villes_agricoles = ["Sidi Kacem", "Ouezzane", "Fes", "Meknes", "Sidi Slimane", "El Hajeb"]

        # 1. Le mini-prompt pour extraire la quantité (Hyper léger !)
        prompt_quantite = ChatPromptTemplate.from_messages([
            ("system",
             "Tu es un extracteur de données. Trouve la quantité exacte (mm, cm, km/h) associée au phénomène. Réponds UNIQUEMENT par la quantité (ex: '100 à 150 mm'). Ne fais pas de phrase. Si introuvable, réponds 'non spécifiée'."),
            ("human",
             "TEXTE:\n{texte}\n\nQuelle est la quantité attendue pour '{phenomene}' en vigilance '{vigilance}' ?")
        ])

        print("\n[Traitement Hybride] Extraction des quantités et génération du JSON...")

        for phenomene in donnees_brutes.phenomenes:
            nom_phen = phenomene.type_phenomene

            for alerte in phenomene.alertes:
                vigilance = alerte.niveau_vigilance.lower()
                severite = "CRITIQUE" if vigilance == "rouge" else "HAUT"

                # A. On demande à l'IA juste la quantité (rapide et sans risque de plantage)
                chain_quantite = prompt_quantite | self.llm
                reponse_ia = chain_quantite.invoke({
                    "texte": texte_original,
                    "phenomene": nom_phen,
                    "vigilance": vigilance
                })
                quantite = reponse_ia.content.strip()

                # B. Boucle Python pure pour générer les 80 objets JSON (Infaillible)
                for zone in alerte.details_zones:
                    for province in zone.provinces:

                        # Logique de typologie
                        if province in villes_cotieres:
                            typologie = "côtière"
                            risque = "d'inondations"
                        elif province in villes_agricoles:
                            typologie = "agricole"
                            risque = "d'inondations"
                        else:
                            typologie = "montagneuse"
                            risque = "de crues éclair et d'éboulements"

                        # Construction EXACTE de la meme phrase n8n
                        justification = f"Niveau de vigilance {vigilance}, {nom_phen.lower()} attendu(e)s de {quantite}, province {typologie} présentant un risque élevé {risque}."

                        # Création de l'objet
                        zone_risque = ZoneRisqueMeteo(
                            province=province,
                            niveau_vigilance_dgm=vigilance,
                            niveau_severite_agent=severite,
                            phenomene_declencheur=nom_phen,
                            date_debut=zone.date_debut,
                            date_fin=zone.date_fin,
                            justification=justification
                        )
                        toutes_les_zones_urgentes.append(zone_risque)

        return MeteoAnalysisReport(
            id_bulletin=id_bul,
            zones_urgentes=toutes_les_zones_urgentes
        )