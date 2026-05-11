import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Blacklist ESN / Cabinets (on garde la liste pour la qualité)
BLACKLIST = ["Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", "Talan", "Devoteam"]

def fetch_devops_global():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    # On cherche "DevOps" sur les boards français sans limiter à une ville
    params = {
        "query": "DevOps",
        "location": "France",
        "date_posted": "all",
        "num_pages": "3" # On augmente le volume de recherche
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('data', [])
    except:
        return []

def run():
    raw_jobs = fetch_devops_global()
    filtered_data = []
    seen_links = set()

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        link = job.get('job_apply_link')

        # Sécurité : On vérifie qu'on a bien un lien et une entreprise
        if not link or not company:
            continue
            
        # Filtre 1 : Le titre doit contenir DevOps
        # Filtre 2 : L'entreprise ne doit pas être dans la Blacklist
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        if "devops" in title and not is_esn:
            if link not in seen_links:
                seen_links.add(link)
                # STRUCTURE DEMANDÉE : Uniquement 2 colonnes
                filtered_data.append({
                    "Entreprise": company,
                    "Lien URL": link
                })

    if not filtered_data:
        requests.post(WEBHOOK_URL, json={"content": "⚠️ Aucune offre trouvée avec les filtres DevOps actuels."})
        return

    # Création du CSV avec uniquement les deux colonnes
    df = pd.DataFrame(filtered_data)
    
    # On s'assure que l'ordre est bien celui demandé : Entreprise | Lien URL
    df = df[["Entreprise", "Lien URL"]]
    
    filename = "veille_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🚀 **Veille DevOps France** : {len(filtered_data)} opportunités trouvées."},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
