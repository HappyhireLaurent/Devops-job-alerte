import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Blacklist ESN / Cabinets étendue
BLACKLIST = [
    "Alten", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", 
    "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", 
    "Talan", "Devoteam", "Manpower", "Adecco"
]

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # On construit une requête qui inclut tes mots-clés et tes villes cibles
    # L'API performe mieux quand on lui donne une intention claire
    search_query = "DevOps Cloud Infrastructure Développeur France Paris Rennes Lyon Nantes"
    
    params = {
        "query": search_query,
        "date_posted": "all",
        "num_pages": "3" 
    }
    
    print(f"📡 Recherche en cours pour : {search_query}")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get('data', [])
        print(f"✅ Offres brutes trouvées : {len(data)}")
        return data
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return []

def run():
    raw_jobs = fetch_jobs()
    filtered_data = []
    seen_links = set()

    # Mots-clés pour le filtrage du titre
    target_keywords = ["devops", "cloud", "infrastructure", "développeur", "developpeur", "developer", "infra"]

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        link = job.get('job_apply_link')

        if not link:
            continue

        # FILTRAGE
        # 1. On ignore si c'est une ESN
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        # 2. On vérifie si un des mots-clés est dans le titre
        match_keyword = any(kw in title for kw in target_keywords)
        
        if match_keyword and not is_esn:
            if link not in seen_links:
                seen_links.add(link)
                # STRUCTURE : Colonne A (Entreprise), Colonne B (Lien URL)
                filtered_data.append({
                    "Entreprise": company,
                    "Lien URL": link
                })

    if not filtered_data:
        msg = f"⚠️ Filtre trop strict : {len(raw_jobs)} offres brutes mais 0 retenues."
        requests.post(WEBHOOK_URL, json={"content": msg})
        return

    # Création du CSV (A: Entreprise, B: Lien)
    df = pd.DataFrame(filtered_data)
    df = df[["Entreprise", "Lien URL"]]
    
    filename = "veille_tech_ciblee.csv"
    # utf-8-sig est crucial pour que Rennes et Développeur s'affichent bien dans Excel
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Envoi vers Discord
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"📍 **Veille Tech (France/Villes Clés)** : {len(filtered_data)} offres trouvées."},
            files={"file": (filename, f)}
        )
    print(f"✨ Terminé : {len(filtered_data)} offres envoyées.")

if __name__ == "__main__":
    run()
