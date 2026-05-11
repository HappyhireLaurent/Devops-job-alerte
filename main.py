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

# User-Agent navigateur réaliste — CRUCIAL pour ne pas être bloqué par Indeed
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

TARGET_KEYWORDS = [
    "devops", "sre", "site reliability",
    "cloud", "infra", "infrastructure",
    "platform engineer", "platform engineering",
    "backend", "back-end", "back end",
    "fullstack", "full stack", "full-stack",
    "kubernetes", "k8s", "terraform", "ansible",
    "aws", "azure", "gcp",
]

BLACKLIST = [
    "alten", "capgemini", "sopra steria", "sopra group", "cgi", "atos", "inetum",
    "akkodis", "michael page", "hays", "robert half", "expectra", "randstad",
    "talan", "devoteam", "manpower", "adecco", "accenture", "infosys",
    "aubay", "altran", "ippon", "squad", "groupe open", "astek",
    "davidson", "onepoint", "hardis", "sfeir", "klee", "takima",
    "valeuriad", "smile", "infotel", "neurones", "claranet",
    "computer futures", "spring professional", "lhh", "crit", "synergie",
    "gi group", "page personnel", "talent solutions",
    "recrutement", "cabinet", "chasseur de têtes",
]

# ──────────────────────────────────────────────
# FLUX RSS — Indeed FR + Welcome to the Jungle
# ──────────────────────────────────────────────

INDEED_BASE = "https://fr.indeed.com/rss"
WTTJ_BASE   = "https://www.welcometothejungle.com/fr/jobs.rss"

RSS_FEEDS = [
    # Indeed FR
    f"{INDEED_BASE}?q=devops&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=SRE+site+reliability&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=cloud+infrastructure&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=ingenieur+cloud&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=platform+engineer&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=developpeur+backend&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=backend+developer&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=developpeur+fullstack&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=fullstack+developer&l=France&sort=date&fromage=7",
    f"{INDEED_BASE}?q=kubernetes+terraform&l=France&sort=date&fromage=7",
    # Welcome to the Jungle
    f"{WTTJ_BASE}?query=devops&department[]=tech",
    f"{WTTJ_BASE}?query=cloud+engineer&department[]=tech",
    f"{WTTJ_BASE}?query=backend+developer&department[]=tech",
    f"{WTTJ_BASE}?query=fullstack&department[]=tech",
    f"{WTTJ_BASE}?query=platform+engineer&department[]=tech",
]

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(esn in t for esn in BLACKLIST)

def matches_target(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TARGET_KEYWORDS)

def clean_company(name: str) -> str:
    name = re.sub(r"\s*[-–]\s*\w+$", "", name).strip()
    return name or "Inconnu"

# ──────────────────────────────────────────────
# SCRAPING
# ──────────────────────────────────────────────

def fetch_rss(url: str) -> str | None:
    """Télécharge le RSS en se faisant passer pour un navigateur."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  HTTP {resp.status_code} — {url[:80]}")
        if resp.status_code == 200:
            return resp.text
        print(f"  ⚠️  Réponse inattendue : {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ Erreur réseau : {e}")
        return None

def parse_feed(xml_content: str, source: str) -> list[dict]:
    """Parse le XML RSS et retourne les offres brutes."""
    results = []
    try:
        feed = feedparser.parse(xml_content)
        print(f"  → {len(feed.entries)} entrées ({source})")
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()
            parts     = title.rsplit(" - ", 1)
            job_title = parts[0].strip() if len(parts) == 2 else title
            company   = parts[1].strip() if len(parts) == 2 else entry.get("author", "Inconnu")
            if link:
                results.append({"title": job_title, "company": company, "link": link, "source": source})
    except Exception as e:
        print(f"  ❌ Erreur parsing : {e}")
    return results

def collect_all_jobs() -> list[dict]:
    all_jobs = []
    for url in RSS_FEEDS:
        source = "WTTJ" if "welcometothejungle" in url else "Indeed"
        print(f"\n📡 [{source}] {url[:80]}")
        xml = fetch_rss(url)
        if xml:
            all_jobs.extend(parse_feed(xml, source))
        else:
            print("  ⏭️  Flux ignoré")
    print(f"\n📊 Total brut : {len(all_jobs)} offres récupérées")
    return all_jobs

# ──────────────────────────────────────────────
# FILTRAGE
# ──────────────────────────────────────────────

def filter_jobs(raw_jobs: list[dict]) -> list[dict]:
    filtered   = []
    seen_links = set()
    stats = {"blacklist": 0, "no_keyword": 0, "duplicate": 0, "kept": 0}

    for job in raw_jobs:
        title   = job["title"]
        company = clean_company(job["company"])
        link    = job["link"]

        if link in seen_links:
            stats["duplicate"] += 1
            continue
        if is_blacklisted(company) or is_blacklisted(title):
            stats["blacklist"] += 1
            print(f"  ❌ Blacklisté : {company} | {title}")
            continue
        if not matches_target(title):
            stats["no_keyword"] += 1
            print(f"  ⚪ Hors scope  : {title}")
            continue

        seen_links.add(link)
        filtered.append({"Entreprise": company, "Lien URL": link})
        stats["kept"] += 1
        print(f"  ✅ Retenu      : {company} | {title}")

    print(f"\n📈 Stats : {stats['kept']} retenus | {stats['blacklist']} blacklist | {stats['no_keyword']} hors scope | {stats['duplicate']} doublons")
    return filtered

# ──────────────────────────────────────────────
# ENVOI DISCORD
# ──────────────────────────────────────────────

def send_to_discord(jobs: list[dict], total_raw: int):
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK non défini.")
        return

    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    if not jobs:
        msg = (
            f"⚠️ **Veille DevOps France — {date_str}**\n"
            f"0 offre retenue sur {total_raw} brutes scrapées.\n"
            f"Vérifie les logs GitHub Actions pour le détail."
        )
        requests.post(WEBHOOK_URL, json={"content": msg})
        return

    output    = StringIO()
    writer    = csv.DictWriter(output, fieldnames=["Entreprise", "Lien URL"])
    writer.writeheader()
    writer.writerows(jobs)
    csv_bytes = output.getvalue().encode("utf-8-sig")

    filename = f"veille_devops_{datetime.now().strftime('%Y-%m-%d')}.csv"
    content  = (
        f"📍 **Veille DevOps France — {date_str}**\n"
        f"✅ **{len(jobs)} offres** retenues (hors ESN/cabinets)\n"
        f"Sources : Indeed.fr + Welcome to the Jungle"
    )
    resp = requests.post(
        WEBHOOK_URL,
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
    raw_jobs      = collect_all_jobs()
    filtered_jobs = filter_jobs(raw_jobs)
    send_to_discord(filtered_jobs, total_raw=len(raw_jobs))
    print("=" * 60)
    print("🏁 Terminé.")
    print("=" * 60)

if __name__ == "__main__":
    run()
