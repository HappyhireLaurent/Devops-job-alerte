import feedparser
import os
import csv
import requests
import re
from datetime import datetime, timezone
from io import StringIO

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Mots-clés pour filtrer les titres d'offres
TARGET_KEYWORDS = [
    "devops", "sre", "site reliability",
    "cloud", "infra", "infrastructure",
    "platform engineer", "platform engineering",
    "backend", "back-end", "back end",
    "fullstack", "full stack", "full-stack",
    "kubernetes", "k8s", "terraform", "ansible",
    "aws", "azure", "gcp",
]

# Blacklist ESN & cabinets de recrutement (insensible à la casse)
BLACKLIST = [
    "alten", "capgemini", "sopra steria", "sopra group", "cgi", "atos", "inetum",
    "akkodis", "michael page", "hays", "robert half", "expectra", "randstad",
    "talan", "devoteam", "manpower", "adecco", "accenture", "infosys",
    "aubay", "altran", "ippon", "squad", "groupe open", "astek",
    "davidson", "onepoint", "hardis", "sfeir", "klee", "takima",
    "valeuriad", "smile", "infotel", "neurones", "claranet",
    "computer futures", "spring professional", "lhh", "crit", "synergie",
    "gi group", "page personnel", "talent solutions", "apec recrutement",
    "recrutement", "cabinet", "chasseur de têtes",
]

# ──────────────────────────────────────────────
# FLUX RSS
# ──────────────────────────────────────────────
# Indeed FR génère des RSS dynamiques selon la query + localisation
# On multiplie les requêtes pour couvrir tous les postes ciblés

INDEED_BASE = "https://fr.indeed.com/rss"

RSS_FEEDS = [
    # DevOps / SRE
    f"{INDEED_BASE}?q=devops&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=SRE+%22site+reliability%22&l=France&sort=date&fromage=7",
    # Cloud / Infra
    f"{INDEED_BASE}?q=cloud+infrastructure&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=ingenieur+cloud&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=platform+engineer&l=France&sort=date&fromage=7",
    # Développeur Backend
    f"{INDEED_BASE}?q=developpeur+backend&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=backend+developer&l=France&sort=date&fromage=7",
    # Développeur Fullstack
    f"{INDEED_BASE}?q=developpeur+fullstack&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=fullstack+developer&l=France&sort=date&fromage=7",
    # Kubernetes / Terraform (postes très ciblés)
    f"{INDEED_BASE}?q=kubernetes+terraform&l=France&sort=date&fromage=7",
]

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def is_blacklisted(text: str) -> bool:
    """Retourne True si le texte contient un nom d'ESN ou cabinet."""
    text_lower = text.lower()
    return any(esn in text_lower for esn in BLACKLIST)


def matches_target(title: str) -> bool:
    """Retourne True si le titre correspond à un poste recherché."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in TARGET_KEYWORDS)


def clean_company(name: str) -> str:
    """Nettoie le nom de l'entreprise (retire les suffixes parasites)."""
    # Indeed ajoute parfois des suffixes comme " - Paris" dans employer_name
    name = re.sub(r"\s*[-–]\s*\w+$", "", name).strip()
    return name or "Inconnu"


# ──────────────────────────────────────────────
# SCRAPING
# ──────────────────────────────────────────────

def scrape_feed(url: str) -> list[dict]:
    """Parse un flux RSS Indeed et retourne les offres brutes."""
    results = []
    try:
        feed = feedparser.parse(url)
        print(f"  → {len(feed.entries)} entrées dans {url[:80]}...")
        for entry in feed.entries:
            title = entry.get("title", "")
            link  = entry.get("link", "")
            # Indeed met l'entreprise dans le titre sous la forme "Titre - Entreprise"
            # ex: "Ingénieur DevOps - Société XYZ"
            parts = title.rsplit(" - ", 1)
            job_title = parts[0].strip() if len(parts) == 2 else title
            company   = parts[1].strip() if len(parts) == 2 else "Inconnu"

            if link:
                results.append({
                    "title":   job_title,
                    "company": company,
                    "link":    link,
                })
    except Exception as e:
        print(f"  ❌ Erreur sur {url[:60]}: {e}")
    return results


def collect_all_jobs() -> list[dict]:
    """Parcourt tous les flux RSS et agrège les offres."""
    all_jobs = []
    for feed_url in RSS_FEEDS:
        print(f"📡 Scraping: {feed_url[:80]}")
        jobs = scrape_feed(feed_url)
        all_jobs.extend(jobs)
    print(f"\n📊 Total brut : {len(all_jobs)} offres récupérées")
    return all_jobs


# ──────────────────────────────────────────────
# FILTRAGE
# ──────────────────────────────────────────────

def filter_jobs(raw_jobs: list[dict]) -> list[dict]:
    """Applique les filtres mots-clés + blacklist + dédoublonnage."""
    filtered = []
    seen_links = set()
    stats = {"blacklist": 0, "no_keyword": 0, "duplicate": 0, "kept": 0}

    for job in raw_jobs:
        title   = job["title"]
        company = clean_company(job["company"])
        link    = job["link"]

        # Dédoublonnage
        if link in seen_links:
            stats["duplicate"] += 1
            continue

        # Filtre blacklist (titre + entreprise)
        if is_blacklisted(company) or is_blacklisted(title):
            stats["blacklist"] += 1
            print(f"  ❌ Blacklisté : {company} | {title}")
            continue

        # Filtre mots-clés
        if not matches_target(title):
            stats["no_keyword"] += 1
            print(f"  ⚪ Hors scope  : {title}")
            continue

        seen_links.add(link)
        filtered.append({"Entreprise": company, "Lien URL": link})
        stats["kept"] += 1
        print(f"  ✅ Retenu      : {company} | {title}")

    print(f"\n📈 Stats filtrage :")
    print(f"   Retenus    : {stats['kept']}")
    print(f"   Blacklist  : {stats['blacklist']}")
    print(f"   Hors scope : {stats['no_keyword']}")
    print(f"   Doublons   : {stats['duplicate']}")
    return filtered


# ──────────────────────────────────────────────
# ENVOI DISCORD
# ──────────────────────────────────────────────

def send_to_discord(jobs: list[dict], total_raw: int):
    """Génère le CSV en mémoire et l'envoie sur Discord via webhook."""
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK non défini dans les variables d'environnement.")
        return

    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    if not jobs:
        msg = (
            f"⚠️ **Veille DevOps France — {date_str}**\n"
            f"0 offre retenue sur {total_raw} brutes scrapées.\n"
            f"Vérifie les logs GitHub Actions pour le détail."
        )
        requests.post(WEBHOOK_URL, json={"content": msg})
        print("⚠️ Aucune offre — message d'alerte envoyé.")
        return

    # Construction du CSV en mémoire (évite d'écrire sur disque)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["Entreprise", "Lien URL"])
    writer.writeheader()
    writer.writerows(jobs)
    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM pour Excel FR

    filename = f"veille_devops_{datetime.now().strftime('%Y-%m-%d')}.csv"
    content  = (
        f"📍 **Veille DevOps France — {date_str}**\n"
        f"✅ {len(jobs)} offres retenues (hors ESN/cabinets)\n"
        f"Sources : Indeed.fr (RSS)"
    )

    response = requests.post(
        WEBHOOK_URL,
        data={"content": content},
        files={"file": (filename, csv_bytes, "text/csv")},
    )

    if response.status_code in (200, 204):
        print(f"✨ CSV envoyé sur Discord ({len(jobs)} offres).")
    else:
        print(f"❌ Erreur Discord : {response.status_code} — {response.text[:200]}")


# ──────────────────────────────────────────────
# POINT D'ENTRÉE
# ──────────────────────────────────────────────

def run():
    print("=" * 60)
    print("🔍 Veille DevOps France — démarrage")
    print("=" * 60)

    raw_jobs      = collect_all_jobs()
    filtered_jobs = filter_jobs(raw_jobs)
    send_to_discord(filtered_jobs, total_raw=len(raw_jobs))

    print("=" * 60)
    print("🏁 Terminé.")
    print("=" * 60)


if __name__ == "__main__":
    run()
