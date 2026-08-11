import smtplib
from email.message import EmailMessage
from twilio.rest import Client
from core.config import (EMAIL_ADDRESS, EMAIL_PASSWORD, ALERT_EMAIL_TO, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ALERT_SMS_TO)


class NotifierAgent:
    def __init__(self):

        # 1. CONFIGURATION DES PASSERELLES (API)


        # Configuration Email (Destiné aux Autorités)
        self.email_address = EMAIL_ADDRESS
        self.email_password = EMAIL_PASSWORD

        # Configuration Twilio (SMS Destiné aux Citoyens)
        self.twilio_account_sid = TWILIO_ACCOUNT_SID
        self.twilio_auth_token = TWILIO_AUTH_TOKEN
        self.twilio_phone_number = TWILIO_PHONE_NUMBER  # Numéro virtuel Twilio
        self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)

    # ==========================================
    # 2. LOGIQUE PRINCIPALE D'ORCHESTRATION
    # ==========================================

    def process_notifications(self, rapport_json):
        """
        Point d'entrée de l'agent. Lit le JSON final et dispatche les alertes.
        """
        print("\n======================================================")
        print("  DÉMARRAGE DU MODULE DE NOTIFICATION (ACTION AGENT)")
        print("======================================================")

        for confluence in rapport_json.get("confluences_risques_majeurs", []):
            niveau = confluence["niveau_alerte_combine"]
            localisation = confluence["localisation_impactee"]
            synthese = confluence["synthese_decisionnelle"]
            reco_texte = confluence["recommandations_terrain"]

            # Extraction intelligente : On sépare les cibles
            reco_citoyens, reco_autorites = self._separer_recommandations(reco_texte)

            print(f"\n[Notificateur] Traitement de la zone : {localisation} ({niveau})")

            # Déclenchement asynchrone des envois
            self._envoyer_email_autorites(localisation, niveau, synthese, reco_autorites)
            self._envoyer_sms_citoyens(localisation, niveau, reco_citoyens)

    def _separer_recommandations(self, texte_complet):
        """
        Fonction utilitaire qui découpe la chaîne de l'Orchestrateur pour router
        le bon message à la bonne personne.
        """
        try:
            # On coupe le texte au niveau du marqueur "Pour les autorités :"
            parts = texte_complet.split("Pour les autorités :")

            # On nettoie la partie citoyenne
            citoyens = parts[0].replace("Pour les citoyens :", "").strip()

            # On récupère la partie autorité s'il y en a une
            autorites = parts[1].strip() if len(parts) > 1 else "Consultez le protocole de crise standard."

            return citoyens, autorites

        except Exception as e:
            # Fallback de sécurité robuste en cas de format inattendu
            print(f" Erreur de parsing des recommandations : {e}")
            return texte_complet, texte_complet

    # ==========================================
    # 3. MÉTHODES D'EXÉCUTION (OUTILS)
    # ==========================================

    def _envoyer_email_autorites(self, localisation, niveau, synthese, recommandations):
        """ Construit et envoie un mail HTML structuré au PC de crise. """

        # Définition des couleurs selon la gravité
        couleur_alerte = "#d32f2f" if "ROUGE" in niveau or "NOIRE" in niveau else "#ff9800"

        msg = EmailMessage()
        msg['Subject'] = f" GEO-RISK MAROC : {niveau} sur {localisation}"
        msg['From'] = self.email_address
        msg['To'] = ALERT_EMAIL_TO


        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border: 2px solid {couleur_alerte}; border-radius: 8px; overflow: hidden;">

                <div style="background-color: {couleur_alerte}; color: white; padding: 15px; text-align: center;">
                    <h2 style="margin: 0;"> GEO-RISK : ALERTE DÉCISIONNELLE</h2>
                </div>

                <div style="padding: 20px;">
                    <h3 style="color: {couleur_alerte}; border-bottom: 1px solid {couleur_alerte}; padding-bottom: 5px;"> ZONE IMPACTÉE : {localisation}</h3>

                    <p><strong>NIVEAU DE CRISE :</strong> <span style="background-color: #000; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{niveau}</span></p>

                    <div style="background-color: #fcfcfc; padding: 15px; border-left: 4px solid {couleur_alerte}; margin: 15px 0;">
                        <p style="margin: 0; font-weight: bold;">SYNTHÈSE DE LA CONFLUENCE :</p>
                        <p style="margin-top: 5px;">{synthese}</p>
                    </div>

                    <h4 style="color: {couleur_alerte};"> ACTIONS TACTIQUES REQUISES :</h4>
                    <p style="white-space: pre-line; line-height: 1.6;">{recommandations}</p>

                    <hr style="border: none; border-top: 1px solid #eee; margin-top: 25px;">
                    <p style="font-size: 11px; color: #888; text-align: center;">Ce bulletin est généré automatiquement par le moteur d'Intelligence Artificielle Geo-Risk Maroc.</p>
                </div>

            </div>
        </body>
        </html>
        """

        # On définit le contenu comme étant du HTML
        msg.set_content("Veuillez activer l'affichage HTML pour lire ce rapport de crise.")
        msg.add_alternative(html_content, subtype='html')


        try:
             with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                 smtp.login(self.email_address, self.email_password)
                 smtp.send_message(msg)
             print(f"   ->  Email HTML d'alerte envoyé aux autorités de {localisation}.")
        except Exception as e:
             print(f"   -> Échec de l'envoi de l'email : {e}")

        print(f"   ->  Simulation : Email d'alerte préparé pour les autorités de {localisation}.")

    def _envoyer_sms_citoyens(self, localisation, niveau, recommandations_citoyens):
        """ Formate et envoie un SMS d'urgence à la population cible. """

        # Nettoyage et formatage du SMS pour qu'il soit percutant
        reco_propre = recommandations_citoyens.replace("-", "").strip()

        sms_body = f" GEO-RISK : {niveau} \n {localisation}\n\n{reco_propre}\n\nNe prenez aucun risque."


        try:
             message = self.twilio_client.messages.create(
                 body=sms_body,
                 from_=self.twilio_phone_number,
                 to=ALERT_SMS_TO # Ton numéro de téléphone pour tester
             )
             print(f"   ->  SMS d'urgence expédié aux citoyens de {localisation} (ID: {message.sid}).")
        except Exception as e:
             print(f"   ->  Échec de l'envoi du SMS : {e}")

        print(f"   ->  Simulation : SMS d'urgence préparé pour les citoyens de {localisation}.")