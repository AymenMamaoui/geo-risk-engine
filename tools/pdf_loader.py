import requests
import pdfplumber
import io

def extraire_texte_depuis_url(url):
    response = requests.get(url)
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        texte = ""
        for page in pdf.pages:
            texte += page.extract_text() + "\n"
    return texte