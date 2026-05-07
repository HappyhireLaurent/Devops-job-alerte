import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# On réduit la blacklist au strict minimum pour le test
BLACKLIST = ["Alten", "Capgemini", "Sopra Steria"] 

def fetch_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    params = {
        "query": "DevOps France", # Requête simple
        "date_posted": "all",
        "num_pages": "1"
    }
    
    print("📡 Connexion à l'API...")
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
        
        # Nettoyage pour la comparaison
        title_lower = title.lower()
        company_lower = company.lower()
        
        # Logique de filtrage
        is_esn = any(esn.lower() in company_lower for esn in BLACKLIST)
        is_devops = "devops" in title_lower
        
        if is_devops and not is_esn:
            filtered_data.append({
                "Poste": title,
                "Entreprise": company,
                "Lien": job.get('job_apply_link'),
                "Source": job.get('job_publisher', 'N/A'),
                "Date": job.get('job_posted_at_datetime_utc', 'N/A')[:10]
            })
        else:
            # On affiche dans les logs pourquoi on rejette l'offre
            reason = "Pas DevOps" if not is_devops else "C'est une ESN"
            print(f"Skipped: {title} chez {company} ({reason})")

    if not filtered_data:
        print("⚠️ Toujours aucune offre après filtrage.")
        # On envoie quand même un message à Discord pour dire que le bot est vivant
        requests.post(WEBHOOK_URL, json={"content": "🤖 Bot actif, mais 0 offre trouvée avec les filtres actuels."})
        return

    df = pd.DataFrame(filtered_data)
    filename = "offres_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"📤 Envoi de {len(filtered_data)} offres vers Discord...")
    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🚀 Rapport DevOps : {len(filtered_data)} offres trouvées !"},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
