import requests
import os

# On récupère les variables d'environnement définies dans le fichier YAML
API_KEY = os.getenv("RAPID_API_KEY")
SLACK_URL = os.getenv("SLACK_WEBHOOK_URL")

def fetch_jobs():
    """Va chercher les offres DevOps en France sur la dernière semaine"""
    url = "https://jsearch.p.rapidapi.com/search"
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    params = {
        "query": "DevOps, France",
        "date_posted": "week",
        "num_pages": "1"
    }
    
    print("📡 Recherche d'offres en cours...")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return []

def send_to_slack(jobs):
    """Envoie les résultats formatés sur Slack"""
    if not jobs:
        msg = "🔍 *Veille DevOps :* Aucune nouvelle offre trouvée cette semaine."
    else:
        msg = "🚀 *Nouvelles offres DevOps en France (7 derniers jours) :*\n\n"
        for job in jobs[:10]: # On limite à 10 pour la lisibilité
            title = job.get('job_title', 'Poste DevOps')
            company = job.get('employer_name', 'Entreprise')
            city = job.get('job_city', 'France')
            url = job.get('job_apply_link', '#')
            
            # Formatage spécifique Slack : <URL|Texte>
            msg += f"🔹 *{title}* - {company}\n📍 {city}\n🔗 <{url}|Postuler ici>\n\n"

    try:
        res = requests.post(SLACK_URL, json={"text": msg})
        if res.status_code == 200:
            print("✅ Succès ! Message envoyé sur Slack.")
        else:
            print(f"⚠️ Slack a répondu avec l'erreur : {res.status_code}")
    except Exception as e:
        print(f"❌ Erreur d'envoi : {e}")

if __name__ == "__main__":
    if not API_KEY or not SLACK_URL:
        print("❌ Manquant : Vérifie tes secrets RAPID_API_KEY ou DISCORD_WEBHOOK sur GitHub.")
    else:
        offres = fetch_jobs()
        send_to_slack(offres)
