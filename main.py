import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY, 
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # REQUÊTE ULTRA-LARGE : On cherche juste "Informatique" en France
    params = {
        "query": "Informatique France",
        "date_posted": "all",
        "num_pages": "1"
    }
    
    print("📡 Tentative de connexion à l'API...")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"DEBUG: Status Code API = {response.status_code}")
        
        data = response.json().get('data', [])
        print(f"✅ L'API a renvoyé {len(data)} résultats bruts.")
        return data
    except Exception as e:
        print(f"❌ Erreur critique API : {e}")
        return []

def run():
    raw_jobs = fetch_jobs()
    
    if not raw_jobs:
        msg = "⚠️ L'API n'a renvoyé ABSOLUMENT RIEN. Vérifie tes crédits sur RapidAPI."
        requests.post(WEBHOOK_URL, json={"content": msg})
        return

    # ON NE FILTRE RIEN DU TOUT POUR CE TEST
    filtered_data = []
    for job in raw_jobs:
        filtered_data.append({
            "Poste": job.get('job_title'),
            "Entreprise": job.get('employer_name'),
            "Lien": job.get('job_apply_link')
        })

    # Création du CSV
    df = pd.DataFrame(filtered_data)
    filename = "test_complet.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Envoi
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🚨 TEST RÉUSSI : J'ai trouvé {len(filtered_data)} jobs informatiques sans filtres !"},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
