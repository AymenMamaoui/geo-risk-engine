# LLM with prompts
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from core.config import GROQ_API_KEY
from schemas.data_models import GeoRiskReport, MeteoAnalysisReport, HydrauliqueAnalysisReport


class OrchestratorAgent:
    def __init__(self):
        # On utilise le modèle 70b car le croisement de données demande un fort niveau de raisonnement
        self.llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")

        # On force la sortie vers le schéma GeoRiskReport que j'ai déjà dans data_models.py
        self.struct_report = self.llm.with_structured_output(GeoRiskReport)

    def generer_synthese_globale(self, rapport_meteo: MeteoAnalysisReport, rapport_hydro: HydrauliqueAnalysisReport):
        # 1. DATA MINIMIZATION : On ne garde que les provinces utiles pour économiser des milliers de tokens !
        provinces_cibles = ["Chefchaouen", "Taounate", "Larache", "Ouezzane", "Taza", "Fes", "Sidi Said Maachou",
                            "Imfout", "MDiq-Fnideq", "Tetouan", "Tanger-Assilah", "Rabat", "Sale"]

        meteo_filtree = [
            zone for zone in rapport_meteo.zones_urgentes
            if any(cible.lower() in zone.province.lower() for cible in provinces_cibles)
        ]
        rapport_meteo.zones_urgentes = meteo_filtree  # On écrase avec la liste courte

        # On prépare le contexte en fusionnant les deux JSON parfaits qu'on a obtenus précédemment
        contexte = f"""
        --- ALERTES MÉTÉO (Filtre appliqué) ---
        {rapport_meteo.model_dump_json()}

        --- ALERTES HYDRAULIQUES (Filtre appliqué) ---
        {rapport_hydro.model_dump_json()}
        """

        # Le Prompt strict pour le rapport final
        system_prompt = """
                Tu es l'Intelligence Centrale Geo-Risk Maroc. Ton rôle est de croiser les deux rapports fournis pour identifier les zones où le danger est démultiplié.

                RÈGLES DE CORRÉLATION SPATIALE (CRITIQUES) :
                1. L'Oued Ouerrha et le Barrage Garde Sebou impactent directement les provinces de Chefchaouen, Taounate, Larache et Ouezzane.
                2. L'Oued Sebou et le Barrage Allal El Fassi impactent le Moyen Sebou (Taza, Taounate, Fès).
                3. Les barrages Imfout et Sidi Said Maachou concernent les zones du littoral centre.

                CALCUL DE SÉVÉRITÉ DU RISQUE COMBINÉ :
                - URGENCE NOIRE : Si Vigilance Météo ROUGE + Infrastructure CRITIQUE (ex: Oued Ouerrha à 1250 m3/s ou Barrage > 95%).
                - ALERTE ROUGE : Si Vigilance Météo ROUGE + Infrastructure HAUTE   --- OU ---   Vigilance Météo ORANGE + Infrastructure CRITIQUE.
                - VIGILANCE ORANGE : Si Vigilance Météo ORANGE + Infrastructure HAUTE.
                
                FORMAT DE SYNTHÈSE ET RECOMMANDATIONS :
                - synthese_decisionnelle : Produis une synthèse claire montrant que tu as compris le lien de cause à effet en citant les chiffres précis (ex: 'Les fortes pluies sur Chefchaouen vont aggraver la crue déjà rouge de l'Oued Ouerrha à 1250 m3/s et le barrage Garde Sebou à 96.8%').

                - recommandations_terrain : Tu DOIS copier EXACTEMENT le bloc de texte correspondant au niveau de sévérité calculé en respectant le format d'affichage, SANS RIEN INVENTER :

                  SI NIVEAU URGENCE NOIRE :
                  "Pour les citoyens :
                        1. Éloignez-vous immédiatement des lits d'oueds et des ravins.
                        2. Rejoignez les points hauts ou les étages supérieurs.
                        3. Coupez les réseaux de gaz et d'électricité de votre domicile.
                        4. N'allez pas chercher vos enfants à l'école, ils y sont en toute sécurité.
                   Pour les autorités :
                        1. Déclenchement du PC de crise provincial et évacuation préventive.
                        2. Fermeture immédiate des routes submersibles et interdiction stricte de circulation.
                        3. Diffusion immédiate d'une alerte SMS de masse via les opérateurs télécoms et mobilisation des FAR."
                  SI NIVEAU ALERTE ROUGE :
                  "Pour les citoyens :
                        1. Ne vous engagez sous aucun prétexte sur une route inondée.
                        2. Préparez un kit d'urgence et restez à l'écoute des autorités et montez vos objets de valeur aux étages..
                        3. Ne descendez en aucun cas dans les sous-sols ou parkings souterrains.
                   Pour les autorités :
                        1. Pré-positionnement des moyens de pompage et de sauvetage.
                        2. Alerte renforcée auprès des communes à risque.
                        3. Annulation préventive des rassemblements en plein air (ex: souks ruraux près des oueds).
          -             4. Pré-alerte des infrastructures hospitalières de la région."

                  SI NIVEAU VIGILANCE ORANGE :
                  "Pour les citoyens :
                        1. Soyez vigilants lors de vos déplacements près des cours d'eau et tenez-vous informés de l'évolution météo.
                        2. Mettez à l'abri vos biens susceptibles d'être inondés.
                        3. Maintenez vos téléphones chargés au maximum
                   Pour les autorités :
                        1. Activation de la cellule de veille hydrologique continue.
                        2. Anticipation de lâchers d'eau préventifs si barrages > 85% avec information préalable aux communes en aval.
                        3. Inspection et dégagement préventif des débris sous les ponts critiques."
                """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human",
             "Analyse ces rapports croisés et génère le bilan des confluences de risques majeurs :\n{contexte}")
        ])

        print("[Orchestrateur] Croisement des données Météo et Hydrauliques en cours...")
        return (prompt | self.struct_report).invoke({"contexte": contexte})