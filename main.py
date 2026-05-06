import requests
import os

# CONFIGURATION
API_KEY = os.getenv("RAPID_API_KEY")
SLACK_URL = os.getenv("SLACK_URL")

# --- VOTRE BLACKLIST ESN / CABINETS ---
# Ajoutez ici tous les noms que vous souhaitez ignorer
BLACKLIST = [
    "Alten", "Altran", "Capgemini", "Sopra Steria", "CGI", "Atos", 
    "Inetum", "Akkodis", "Michael Page", "Hays", "Robert Half", 
    "Expectra", "Webhelp", "Talan", "Devoteam", "Orange Business",
    "Manpower", "Adecco", "Randstad", "Viveris", "Econocom"
]

def fetch_devops_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # On cherche les jobs postés dans les dernières 24h
    params = {
        "query": "DevOps France",
        "date_posted": "today",
        "num_pages": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('data', [])
    except:
        return []

def send_to_slack(jobs):
    if not jobs:
        print("Aucune offre trouvée aujourd'hui.")
        return

    count = 0
    for job in jobs:
        company = job.get('employer_name', 'N/A')
        title = job.get('job_title', '')
        
        # FILTRES : 
        # 1. Le titre doit contenir "DevOps"
        # 2. L'entreprise ne doit pas être dans la Blacklist
        is_esn = any(esn.lower() in company.lower() for esn in BLACKLIST)
        is_devops = "devops" in title.lower()

        if is_devops and not is_esn:
            # Extraction des infos demandées
            link = job.get('job_apply_link', '#')
            # Note: Le nom de la personne est rarement disponible via API, 
            # on affiche le site d'origine (LinkedIn, Indeed...) à la place.
            publisher = job.get('job_publisher', 'Direct') 
            
            message = (
                f"🎯 *Nouvelle opportunité DevOps*\n"
                f"• *Poste :* {title}\n"
                f"• *Entreprise :* {company}\n"
                f"• *Source/Contact :* {publisher}\n"
                f"• *Lien :* <{link}|Cliquer ici pour voir l'offre>"
            )
            
            requests.post(SLACK_URL, json={"text": message})
            count += 1
    
    print(f"{count} offres envoyées sur Slack.")

if __name__ == "__main__":
    if not API_KEY or not SLACK_URL:
        print("Erreur : Secrets manquants.")
    else:
        all_jobs = fetch_devops_jobs()
        send_to_slack(all_jobs)
