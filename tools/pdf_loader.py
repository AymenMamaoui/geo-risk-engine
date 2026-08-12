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


def extraire_texte_depuis_bytes(contenu_bytes: bytes, filename: str = "") -> str:
    """
    Extrait le texte d'un PDF fourni sous forme de bytes (upload utilisateur).

    Paramètres :
      - contenu_bytes : le contenu binaire du fichier (upload)
      - filename      : nom du fichier, utilisé pour détecter si c'est un PDF

    Retour : le texte extrait, ou un message d'erreur.
    """
    is_pdf = filename.lower().endswith('.pdf')

    if is_pdf:
        print(f"-> [Upload] Traitement PDF : {filename}")
        try:
            with pdfplumber.open(io.BytesIO(contenu_bytes)) as pdf:
                texte = ""
                for page in pdf.pages:
                    contenu_page = page.extract_text()
                    if contenu_page:
                        texte += contenu_page + "\n"
                return texte.strip()
        except Exception as e:
            return f"Erreur lors de la lecture du PDF : {e}"
    else:
        # Fichier texte brut (.txt) — on décode directement
        print(f"-> [Upload] Traitement texte brut : {filename}")
        try:
            return contenu_bytes.decode("utf-8", errors="replace").strip()
        except Exception as e:
            return f"Erreur lors de la lecture du fichier : {e}"