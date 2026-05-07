import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Blacklist réduite pour ne pas tout bloquer au début
BLACKLIST = ["Alten", "Capgemini", "Sopra Steria"] 

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    # REQUÊTE ÉLARGIE
    params = {
        "query": "DevOps", # On cherche juste DevOps
        "location": "France", # On précise le lieu ici
        "date_posted": "all",
        "num_pages": "2" # On demande 2 pages (plus de résultats)
    }
    
    print("📡 Recherche en cours...")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get('data', [])
        print(f"✅ L'API a trouvé {len(data)} offres brutes.")
        return data
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return []

def run():
    raw_jobs = fetch_jobs()
    filtered_data = []

    for job in raw_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '')
        
        # On ignore la casse (MAJ/min) pour ne rien rater
        title_lower = title.lower()
        company_lower = company.lower()
        
        is_esn = any(esn.lower() in company_lower for esn in BLACKLIST)
        
        # Filtre souple : si "devops" est dans le titre OU le métier
        if "devops" in title_lower and not is_esn:
            filtered_data.append({
                "Poste": title,
                "Entreprise": company,
                "Lien": job.get('job_apply_link'),
                "Source": job.get('job_publisher', 'N/A'),
                "Date": job.get('job_posted_at_datetime_utc', 'N/A')[:10]
            })

    if not filtered_data:
        print("⚠️ Toujours 0 après filtrage.")
        requests.post(WEBHOOK_URL, json={"content": "🤖 Toujours rien. Je vais élargir encore plus la recherche."})
        return

    # Création du CSV
    df = pd.DataFrame(filtered_data)
    filename = "offres_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"📤 Envoi de {len(filtered_data)} offres...")
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"✅ Succès ! J'ai trouvé {len(filtered_data)} offres DevOps en France."},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
