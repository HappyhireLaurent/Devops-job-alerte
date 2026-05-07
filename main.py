import requests
import os
import pandas as pd

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Liste noire (ESN/Cabinets)
BLACKLIST = ["Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", "Talan", "Devoteam"]

def fetch_jobs_multi():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    # On définit plusieurs recherches pour ratisser large
    queries = [
        "DevOps Nantes", # Pour capter des offres comme AVEM
        "DevOps Paris",
        "DevOps Lyon",
        "DevOps Télétravail France"
    ]
    
    all_raw_jobs = []
    
    for q in queries:
        print(f"📡 Recherche pour : {q}...")
        params = {
            "query": q,
            "date_posted": "all",
            "num_pages": "1"
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json().get('data', [])
            all_raw_jobs.extend(data)
        except:
            continue
            
    return all_raw_jobs

def run():
    raw_jobs = fetch_jobs_multi()
    filtered_data = []
    seen_ids = set() # Pour éviter les doublons entre les différentes recherches

    for job in raw_jobs:
        job_id = job.get('job_id')
        if job_id in seen_ids:
            continue
            
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '').lower()
        
        # Filtre ESN
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        # Filtre de mots-clés : on accepte DevOps ou SRE ou Cloud Engineer
        keywords = ["devops", "sre", "cloud engineer", "plateform engineer"]
        match_keyword = any(kw in title for kw in keywords)

        if match_keyword and not is_esn:
            seen_ids.add(job_id)
            filtered_data.append({
                "Poste": job.get('job_title'),
                "Entreprise": company,
                "Localisation": f"{job.get('job_city', '')}, {job.get('job_country', 'FR')}",
                "Lien": job.get('job_apply_link'),
                "Source": job.get('job_publisher', 'N/A'),
                "Date": job.get('job_posted_at_datetime_utc', 'N/A')[:10]
            })

    if not filtered_data:
        requests.post(WEBHOOK_URL, json={"content": "✅ Veille : Aucune offre trouvée avec les nouveaux paramètres."})
        return

    # Tri par date (la plus récente en haut)
    df = pd.DataFrame(filtered_data).sort_values(by="Date", ascending=False)
    filename = "veille_devops_france.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"🎯 **Rapport Hebdo : {len(filtered_data)} offres trouvées !**\nJ'ai scanné Nantes, Paris, Lyon et le Remote."},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
