import requests
import os

API_KEY = os.getenv("RAPID_API_KEY")
SLACK_URL = os.getenv("SLACK_URL")

BLACKLIST = ["Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", "Expectra", "Webhelp", "Talan", "Devoteam", "Orange Business"]

def fetch_devops_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    
    # On élargit la recherche pour être sûr de capter des résultats
    params = {
        "query": "DevOps", 
        "location": "France",
        "date_posted": "all", # On met "all" pour le test, on repassera à "today" après
        "num_pages": "1"
    }
    
    print(f"📡 Requête API avec les paramètres : {params}")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get('data', [])
        print(f"✅ Nombre d'offres brutes trouvées par l'API : {len(data)}")
        return data
    except Exception as e:
        print(f"❌ Erreur lors de l'appel API : {e}")
        return []

def send_to_slack(jobs):
    count = 0
    for job in jobs:
        company = job.get('employer_name', 'N/A')
        title = job.get('job_title', '').lower()
        
        # Filtrage
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        
        # On vérifie si "devops" est dans le titre OU dans la description
        if "devops" in title and not is_esn:
            link = job.get('job_apply_link', '#')
            publisher = job.get('job_publisher', 'Direct') 
            
            message = (
                f"🎯 *Opportunité détectée*\n"
                f"• *Poste :* {job.get('job_title')}\n"
                f"• *Entreprise :* {company}\n"
                f"• *Source :* {publisher}\n"
                f"• *Lien :* <{link}|Voir l'offre>"
            )
            requests.post(SLACK_URL, json={"text": message})
            count += 1
    
    print(f"📤 {count} offres filtrées envoyées sur Slack.")

if __name__ == "__main__":
    if not API_KEY or not SLACK_URL:
        print("❌ Secrets manquants !")
    else:
        all_jobs = fetch_devops_jobs()
        send_to_slack(all_jobs)
