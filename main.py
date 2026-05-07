import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def run():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # TEST 1 : On cherche un terme universel (Python) pour voir si l'API répond
    params = {"query": "Python", "num_pages": "1"}
    
    print("📡 Tentative de connexion à l'API...")
    try:
        response = requests.get(url, headers=headers, params=params)
        
        # On envoie le code de réponse à Discord pour savoir ce qui se passe
        requests.post(WEBHOOK_URL, json={"content": f"📡 Status Code API : {response.status_code}"})
        
        data = response.json().get('data', [])
        
        if not data:
            # Si c'est vide, on essaie une recherche encore plus simple
            requests.post(WEBHOOK_URL, json={"content": "⚠️ L'API a répondu mais la liste est VIDE. Je tente une recherche mondiale..."})
            params = {"query": "Developer", "num_pages": "1"}
            response = requests.get(url, headers=headers, params=params)
            data = response.json().get('data', [])

        if data:
            # Si on a des données, on crée le fichier SANS AUCUN FILTRE
            df = pd.DataFrame(data)
            filename = "offres_test.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            with open(filename, "rb") as f:
                requests.post(
                    WEBHOOK_URL, 
                    data={"content": f"✅ SUCCÈS ! J'ai trouvé {len(data)} offres sans aucun filtre."},
                    files={"file": (filename, f)}
                )
        else:
            requests.post(WEBHOOK_URL, json={"content": "❌ Même avec 'Developer', l'API ne renvoie rien. Ta clé API a un problème d'activation chez RapidAPI."})

    except Exception as e:
        requests.post(WEBHOOK_URL, json={"content": f"💥 Erreur fatale : {str(e)}"})

if __name__ == "__main__":
    run()
