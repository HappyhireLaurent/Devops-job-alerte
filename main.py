import requests
import os
import pandas as pd

API_KEY = os.getenv("RAPID_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

BLACKLIST = [
    "alten", "capgemini", "sopra steria", "cgi", "atos", "inetum",
    "akkodis", "michael page", "hays", "robert half", "expectra",
    "talan", "devoteam", "manpower", "adecco", "accenture", "infosys",
    "aubay", "altran", "ippon", "squad", "groupe open", "astek",
    "davidson", "onepoint", "hardis", "sfeir", "klee", "takima",
    "valeuriad", "smile", "infotel", "neurones", "claranet"
]

# Plusieurs requêtes ciblées pour couvrir plus de postes
SEARCH_QUERIES = [
    "DevOps ingénieur France",
    "Cloud engineer France",
    "Infrastructure cloud France",
    "SRE site reliability engineer France",
    "Platform engineer France",
    "développeur backend France",
    "Kubernetes Terraform France",
]

TARGET_KEYWORDS = [
    "devops", "cloud", "infrastructure", "infra", "sre",
    "platform", "kubernetes", "k8s", "terraform", "ansible",
    "développeur", "developpeur", "developer", "backend", "fullstack"
]

def fetch_jobs_for_query(query):
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": query,
        "date_posted": "week",
        "num_pages": "3",
        "country": "fr",
        "language": "fr"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"  Status HTTP: {response.status_code}")
        if response.status_code != 200:
            print(f"  Réponse: {response.text[:300]}")
            return []
        data = response.json().get('data', [])
        print(f"  ✅ {len(data)} offres brutes pour '{query}'")
        return data
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return []

def is_blacklisted(company):
    company_lower = company.lower()
    return any(esn in company_lower for esn in BLACKLIST)

def matches_keywords(title):
    title_lower = title.lower()
    return any(kw in title_lower for kw in TARGET_KEYWORDS)

def run():
    all_jobs = []
    for query in SEARCH_QUERIES:
        print(f"📡 Recherche: {query}")
        jobs = fetch_jobs_for_query(query)
        all_jobs.extend(jobs)

    print(f"\n📊 Total offres brutes: {len(all_jobs)}")

    filtered_data = []
    seen_links = set()

    for job in all_jobs:
        company = job.get('employer_name', 'Inconnu')
        title = job.get('job_title', '')
        link = job.get('job_apply_link') or job.get('job_google_link')
        country = job.get('job_country', '')

        if not link or link in seen_links:
            continue

        # Log pour debug
        print(f"  Offre: '{title}' @ {company} [{country}]")

        if is_blacklisted(company):
            print(f"    ❌ Blacklisté")
            continue
        if not matches_keywords(title):
            print(f"    ❌ Pas de mot-clé trouvé")
            continue

        seen_links.add(link)
        filtered_data.append({"Entreprise": company, "Lien URL": link})
        print(f"    ✅ Retenu")

    print(f"\n✨ {len(filtered_data)} offres retenues après filtrage")

    if not filtered_data:
        msg = (
            f"⚠️ **Veille DevOps** : 0 offre retenue sur {len(all_jobs)} brutes.\n"
            f"Vérifie les logs GitHub Actions pour le détail."
        )
        requests.post(WEBHOOK_URL, json={"content": msg})
        return

    df = pd.DataFrame(filtered_data)[["Entreprise", "Lien URL"]]
    filename = "veille_devops.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    with open(filename, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={"content": f"📍 **Veille DevOps France** : {len(filtered_data)} offres cette semaine."},
            files={"file": (filename, f)}
        )

if __name__ == "__main__":
    run()
