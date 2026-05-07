import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Liste noire des ESN et cabinets (à compléter)
BLACKLIST = [
    "Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", 
    "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", "Talan", 
    "Devoteam", "Orange Business", "Manpower", "Adecco", "Randstad", "Econocom"
]

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    # On ratisse large pour avoir du résultat
    params = {
        "query": "DevOps France",
        "date_posted": "all", # Pas de limite de temps
        "num_pages": "2"      # On prend environ 80 offres
    }
    
    print("📡 Recherche des offres sur les jobboards...")
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('data', [])
    except:
        return []

def run():
    raw_jobs = fetch_jobs()
    filtered_data = []

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        
        # Filtres : Titre contient DevOps + Pas une ESN
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        if "devops" in title and not is_esn:
            filtered_data.append({
                "Poste": job.get('job_title'),
                "Entreprise": company,
                "Lien": job.get('job_apply_link'),
                "Source": job.get('job_publisher', 'N/A'),
                "Date": job.get('job_posted_at_datetime_utc', 'N/A')[:10]
            })

    if not filtered_data:
        print("⚠️ Aucune offre trouvée.")
        return

    # Création du fichier CSV
    df = pd.DataFrame(filtered_data)
    filename = "offres_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Envoi vers Discord
    print(f"📤 Envoi du fichier ({len(filtered_data)} offres) vers Discord...")
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🚀 Voici ton rapport DevOps quotidien ! ({len(filtered_data)} offres trouvées)"},
            files={"file": (filename, f)}
        )
    print("✨ Terminé !")

if __name__ == "__main__":
    if not API_KEY or not WEBHOOK_URL:
        print("❌ Secrets manquants.")
    else:
        run()
