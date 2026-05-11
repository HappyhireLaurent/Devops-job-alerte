import os
import csv
import time
import requests
from datetime import datetime, timezone
from io import StringIO

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

FT_CLIENT_ID     = os.getenv("FT_CLIENT_ID")
FT_CLIENT_SECRET = os.getenv("FT_CLIENT_SECRET")
DISCORD_WEBHOOK  = os.getenv("DISCORD_WEBHOOK")

FT_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    "?realm=%2Fpartenaire"
)
FT_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

# Mots-clés recherchés (envoyés un par un à l'API)
SEARCH_QUERIES = [
    "DevOps",
    "SRE site reliability engineer",
    "Cloud engineer",
    "Ingénieur infrastructure cloud",
    "Platform engineer",
    "Développeur backend",
    "Développeur fullstack",
    "Kubernetes Terraform",
]

# Mots-clés pour filtrer les titres côté script (filet de sécurité)
TARGET_KEYWORDS = [
    "devops", "sre", "site reliability",
    "cloud", "infra", "infrastructure",
    "platform engineer", "platform engineering",
    "backend", "back-end",
    "fullstack", "full stack", "full-stack",
    "kubernetes", "k8s", "terraform", "ansible",
    "aws", "azure", "gcp",
]

# Blacklist ESN & cabinets
BLACKLIST = [
    "alten", "capgemini", "sopra steria", "sopra group", "cgi", "atos", "inetum",
    "akkodis", "michael page", "hays", "robert half", "expectra", "randstad",
    "talan", "devoteam", "manpower", "adecco", "accenture", "infosys",
    "aubay", "altran", "ippon", "groupe open", "astek",
    "davidson", "onepoint", "hardis", "sfeir", "klee", "takima",
    "valeuriad", "smile", "infotel", "neurones", "claranet",
    "computer futures", "lhh", "crit", "synergie",
    "gi group", "page personnel", "talent solutions",
]

# ──────────────────────────────────────────────
# AUTHENTIFICATION
# ──────────────────────────────────────────────

def get_token() -> str:
    """Récupère un token OAuth2 France Travail."""
    print("🔑 Récupération du token OAuth2...")
    resp = requests.post(
        FT_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "client_credentials",
            "client_id":     FT_CLIENT_ID,
            "client_secret": FT_CLIENT_SECRET,
            "scope":         "api_offresdemploiv2",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Échec authentification : {resp.status_code} — {resp.text[:300]}")

    token = resp.json().get("access_token")
    print("  ✅ Token obtenu")
    return token

# ──────────────────────────────────────────────
# RECHERCHE D'OFFRES
# ──────────────────────────────────────────────

def search_jobs(token: str, query: str) -> list[dict]:
    """Appelle l'API France Travail pour une requête donnée."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    params = {
        "motsCles":        query,
        "typeContrat":     "CDI,CDD",   # CDI et CDD uniquement
        "publieeDepuis":   7,            # Offres des 7 derniers jours
        "range":           "0-149",      # Max 150 résultats par appel
    }

    try:
        resp = requests.get(FT_SEARCH_URL, headers=headers, params=params, timeout=15)
        print(f"  HTTP {resp.status_code} pour '{query}'")

        if resp.status_code == 206 or resp.status_code == 200:
            data = resp.json()
            offres = data.get("resultats", [])
            print(f"  → {len(offres)} offres brutes")
            return offres
        elif resp.status_code == 204:
            print("  → Aucune offre (204 No Content)")
            return []
        else:
            print(f"  ⚠️  Erreur : {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"  ❌ Exception : {e}")
        return []

def collect_all_jobs(token: str) -> list[dict]:
    """Lance toutes les requêtes et agrège les résultats."""
    all_jobs = []
    for query in SEARCH_QUERIES:
        print(f"\n📡 Recherche : {query}")
        jobs = search_jobs(token, query)
        all_jobs.extend(jobs)
        time.sleep(1)  # Pause pour respecter le rate limit de l'API

    print(f"\n📊 Total brut : {len(all_jobs)} offres récupérées")
    return all_jobs

# ──────────────────────────────────────────────
# FILTRAGE
# ──────────────────────────────────────────────

def is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(esn in t for esn in BLACKLIST)

def matches_target(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TARGET_KEYWORDS)

def filter_jobs(raw_jobs: list[dict]) -> list[dict]:
    filtered   = []
    seen_ids   = set()
    stats = {"blacklist": 0, "no_keyword": 0, "duplicate": 0, "kept": 0}

    for job in raw_jobs:
        job_id    = job.get("id", "")
        title     = job.get("intitule", "")
        company   = job.get("entreprise", {}).get("nom", "Inconnu")
        # L'API France Travail fournit l'URL de l'offre directement
        url       = job.get("origineOffre", {}).get("urlOrigine", "")
        if not url:
            url = f"https://candidat.francetravail.fr/offres/recherche/detail/{job_id}"

        # Dédoublonnage par ID
        if job_id in seen_ids:
            stats["duplicate"] += 1
            continue

        # Filtre blacklist
        if is_blacklisted(company) or is_blacklisted(title):
            stats["blacklist"] += 1
            print(f"  ❌ Blacklisté : {company} | {title}")
            continue

        # Filtre mots-clés (filet de sécurité)
        if not matches_target(title):
            stats["no_keyword"] += 1
            print(f"  ⚪ Hors scope  : {title}")
            continue

        seen_ids.add(job_id)
        filtered.append({"Entreprise": company, "Lien URL": url})
        stats["kept"] += 1
        print(f"  ✅ Retenu      : {company} | {title}")

    print(
        f"\n📈 Stats : {stats['kept']} retenus | "
        f"{stats['blacklist']} blacklist | "
        f"{stats['no_keyword']} hors scope | "
        f"{stats['duplicate']} doublons"
    )
    return filtered

# ──────────────────────────────────────────────
# ENVOI DISCORD
# ──────────────────────────────────────────────

def send_to_discord(jobs: list[dict], total_raw: int):
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK non défini.")
        return

    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    if not jobs:
        msg = (
            f"⚠️ **Veille DevOps France — {date_str}**\n"
            f"0 offre retenue sur {total_raw} offres brutes.\n"
            f"Vérifie les logs GitHub Actions pour le détail."
        )
        requests.post(DISCORD_WEBHOOK, json={"content": msg})
        return

    # CSV en mémoire
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["Entreprise", "Lien URL"])
    writer.writeheader()
    writer.writerows(jobs)
    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM pour Excel FR

    filename = f"veille_devops_{datetime.now().strftime('%Y-%m-%d')}.csv"
    content  = (
        f"📍 **Veille DevOps France — {date_str}**\n"
        f"✅ **{len(jobs)} offres** retenues (hors ESN/cabinets)\n"
        f"Source : France Travail (officiel)"
    )

    resp = requests.post(
        DISCORD_WEBHOOK,
        data={"content": content},
        files={"file": (filename, csv_bytes, "text/csv")},
    )
    if resp.status_code in (200, 204):
        print(f"✨ CSV envoyé sur Discord ({len(jobs)} offres).")
    else:
        print(f"❌ Erreur Discord : {resp.status_code} — {resp.text[:200]}")

# ──────────────────────────────────────────────
# POINT D'ENTRÉE
# ──────────────────────────────────────────────

def run():
    print("=" * 60)
    print("🔍 Veille DevOps France — démarrage")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not FT_CLIENT_ID or not FT_CLIENT_SECRET:
        print("❌ FT_CLIENT_ID ou FT_CLIENT_SECRET manquant dans les secrets.")
        return

    token         = get_token()
    raw_jobs      = collect_all_jobs(token)
    filtered_jobs = filter_jobs(raw_jobs)
    send_to_discord(filtered_jobs, total_raw=len(raw_jobs))

    print("=" * 60)
    print("🏁 Terminé.")
    print("=" * 60)

if __name__ == "__main__":
    run()
