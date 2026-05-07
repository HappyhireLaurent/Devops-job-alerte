import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def run_diagnostic():
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # On utilise une requête dont on est SÛR qu'elle a des résultats mondiaux
    params = {"query": "Developer", "num_pages": "1"}
    
    try:
        print("📡 Test de connexion...")
        response = requests.get(url, headers=headers, params=params)
        
        # Si l'API répond une erreur (401, 403, 429...)
        if response.status_code != 200:
            error_msg = f"❌ Erreur API {response.status_code}: {response.text}"
            print(error_msg)
            requests.post(WEBHOOK_URL, json={"content": error_msg})
            return

        data = response.json().get('data', [])
        
        if not data:
            msg = "❓ L'API a répondu 200 (OK) mais la liste de jobs est vide. Étrange."
            requests.post(WEBHOOK_URL, json={"content": msg})
            return

        # Si on arrive ici, on a des données ! On filtre pour DevOps France
        print(f"✅ Reçu {len(data)} jobs de test. Passage à la recherche réelle...")
        
        # Recherche réelle
        params_real = {"query": "DevOps France", "date_posted": "all"}
        res_real = requests.get(url, headers=headers, params=params_real)
        jobs = res_real.json().get('data', [])

        df = pd.DataFrame(jobs)
        filename = "offres_devops.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        with open(filename, "rb") as f:
            requests.post(
                WEBHOOK_URL,
                data={"content": f"🎉 CA MARCHE ! {len(jobs)} offres trouvées."},
                files={"file": (filename, f)}
            )

    except Exception as e:
        requests.post(WEBHOOK_URL, json={"content": f"💥 Crash du script : {str(e)}"})

if __name__ == "__main__":
    run_diagnostic()
