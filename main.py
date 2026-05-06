import requests
import os

# Récupération des secrets configurés dans GitHub Actions
# Note : On garde "DISCORD_WEBHOOK" car c'est le nom que tu as donné à ton secret GitHub
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def fetch_devops_jobs():
    """Interroge l'API JSearch pour trouver les postes DevOps en France"""
    url = "https://jsearch.p.rapidapi.com/search"
    
    # Requête ciblée : DevOps, France, publiés la semaine dernière
    query = "DevOps, France"
    
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    params = {
        "query": query,
        "date_posted": "week", # Filtre sur la dernière semaine
        "num_pages": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Vérifie si la requête a réussi
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Erreur lors de la récupération des jobs : {e}")
        return []

def send_to_slack(jobs):
    """Formate et envoie la liste des jobs vers le Webhook Slack"""
    if not jobs:
        message = "🔍 *Veille DevOps :* Aucune nouvelle offre trouvée cette semaine en France."
    else:
        message = "🚀 *Nouvelles offres DevOps de la semaine en France :*\n\n"
        
        # On limite aux 10 premières offres pour ne pas saturer Slack
        for job in jobs[:10]:
            title = job.get('job_title', 'Poste DevOps')
            company = job.get('employer_name', 'Entreprise inconnue')
            city = job.get('job_city', 'France')
            link = job.get('job_apply_link', '#')
            
            # Formatage Slack : *Gras*, _Italique_, <URL|Texte> pour les liens
            message += f"🔹 *{title}* - {company}\n📍 {city}\n🔗 <{link}|Voir l'offre et postuler>\n\n"

    # Envoi de la requête POST à Slack
    try:
        payload = {"text": message}
        response = requests.post(WEBHOOK_URL, json=payload)
        
        if response.status_code == 200:
            print("✅ Message envoyé avec succès sur Slack !")
        else:
            print(f"❌ Échec de l'envoi (Code {response.status_code}) : {response.text}")
            
    except Exception as e:
        print(f"Erreur lors de l'envoi vers Slack : {e}")

if __name__ == "__main__":
    # Vérification que les clés sont présentes
    if not RAPID_API_KEY or not WEBHOOK_URL:
        print("❌ Erreur : Les secrets RAPID_API_KEY ou DISCORD_WEBHOOK sont manquants dans GitHub.")
    else:
        print("🛰️ Recherche des offres en cours...")
        jobs_list = fetch_devops_jobs()
        send_to_slack(jobs_list)
