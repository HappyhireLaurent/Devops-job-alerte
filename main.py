import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Blacklist ESN / Cabinets (Tu peux l'allonger ici)
BLACKLIST = ["Alten", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra"]

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # REQUÊTE : Juste "DevOps", aucune localisation
    params = {
        "query": "DevOps",
        "date_posted": "all",
        "num_pages": "3" # On scanne 3 pages pour avoir un maximum d'offres
    }
    
    print("📡 Recherche globale DevOps en cours...")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get('data', [])
        print(f"✅ Offres brutes trouvées par l'API : {len(data)}")
        return data
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return []

def run():
    raw_jobs = fetch_jobs()
    filtered_data = []
    seen_links = set()

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        link = job.get('job_apply_link')

        if not link:
            continue

        # FILTRAGE
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        # On garde tout ce qui contient "devops" et qui n'est pas une ESN
        if "devops" in title and not is_esn:
            if link not in seen_links:
                seen_links.add(link)
                # STRUCTURE : Entreprise | Lien URL
                filtered_data.append({
                    "Entreprise": company,
                    "Lien URL": link
                })

    if not filtered_data:
        # Message de secours si le filtre est trop fort
        msg = f"⚠️ 0 offre filtrée. L'API a pourtant trouvé {len(raw_jobs)} offres brutes."
        requests.post(WEBHOOK_URL, json={"content": msg})
        return

    # Création du CSV avec 2 colonnes
    df = pd.DataFrame(filtered_data)[["Entreprise", "Lien URL"]]
    
    filename = "offres_devops_mondial.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Envoi vers Discord
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🌍 **Rapport DevOps Global** : {len(filtered_data)} offres trouvées (Sans localisation)."},
            files={"file": (filename, f)}
        )
    print("✨ Envoi terminé.")

if __name__ == "__main__":
    run()
