import requests
import os
from datetime import datetime, timedelta

# Configuration (Les secrets seront stockés dans GitHub)
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def fetch_devops_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    query = "DevOps, France, Last Week"
    
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    params = {"query": query, "date_posted": "week", "num_pages": "1"}
    
    response = requests.get(url, headers=headers, params=params)
    return response.json().get('data', [])

def send_to_discord(jobs):
    if not jobs:
        return
    
    message = "🚀 **Nouvelles offres DevOps de la semaine :**\n\n"
    for job in jobs[:10]:  # On prend les 10 plus pertinentes
        message += f"🔹 **{job['job_title']}** - {job['employer_name']}\n📍 {job['job_city']}, {job['job_country']}\n🔗 [Postuler ici]({job['job_apply_link']})\n\n"
    
    requests.post(WEBHOOK_URL, json={"content": message})

if __name__ == "__main__":
    jobs_list = fetch_devops_jobs()
    send_to_discord(jobs_list)
