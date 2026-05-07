import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# --- BLACKLIST ---
BLACKLIST = ["Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", "Talan", "Devoteam", "Orange Business", "Manpower", "Adecco", "Randstad", "Econocom"]

def fetch_devops_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    params = {
        "query": "DevOps France",
        "date_posted": "week", # On prend toutes les offres de la semaine passée
        "num_pages": "3"      # On augmente à 3 pages (environ 120 offres analysées)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('data', [])
    except:
        return []

def run():
    raw_jobs = fetch_devops_jobs()
    filtered_data = []

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        if "devops" in title and not is_esn:
            filtered_data.append({
                "Nom du Poste": job.get('job_title'),
                "Entreprise": company,
                "Lien Postuler": job.get('job_apply_link'),
                "Source": job.get('job_publisher', 'N/A'),
                "Ville": job.get('job_city', 'France'),
                "Date": job.get('job_posted_at_datetime_utc', 'N/A')[:10]
            })

    if not filtered_data:
        requests.post(WEBHOOK_URL, json={"content": "✅ Veille Hebdo : Aucune offre trouvée cette semaine."})
        return

    df = pd.DataFrame(filtered_data)
    filename = "veille_hebdo_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"📅 **Rapport Hebdomadaire DevOps**\nVoici les {len(filtered_data)} offres détectées cette semaine (Hors ESN)."},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
