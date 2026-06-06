import requests
import pdfplumber
import io


def extraire_texte_depuis_url(url):
    response = requests.get(url)

    # On vérifie si l'URL se termine par .pdf ou si le type est PDF
    # C'est une sécurité supplémentaire au cas où le Content-Type serait mal configuré
    is_pdf = url.lower().endswith('.pdf') or 'application/pdf' in response.headers.get('Content-Type', '')

    if is_pdf:
        print(f"-> Traitement PDF : {url}")
        try:
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                texte = ""
                for page in pdf.pages:
                    texte += page.extract_text() + "\n"
                return texte
        except Exception as e:
            return f"Erreur lors de la lecture du PDF : {e}"

    else:
        print(f"-> Traitement Texte brut : {url}")
        # Pour le texte brut (Pastebin), on retourne simplement le contenu
        return response.text