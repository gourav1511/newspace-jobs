import csv, re, sys, os, time
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from ruamel.yaml import YAML

# ---- Config
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_CSV = os.path.join(REPO_ROOT, "jobs.csv")

yaml = YAML(typ="safe")
with open(os.path.join(os.path.dirname(__file__), "companies.yaml"), "r", encoding="utf-8") as f:
    cfg = yaml.load(f)

ROLE_INCLUDE = [re.compile(pat, re.I) for pat in cfg["roles"]["include"]]
ROLE_EXCLUDE = [re.compile(pat, re.I) for pat in cfg["roles"]["exclude"]]
EXP_PATTERNS  = [re.compile(pat, re.I) for pat in cfg["experience"]["patterns"]]
MIN_YEARS = cfg["experience"]["min_years"]
MAX_YEARS = cfg["experience"]["max_years"]
LOC_PRIORITY = cfg["locations_priority"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (job-scraper; +https://github.com/)"
}

def text_ok(text: str) -> bool:
    if not any(p.search(text) for p in ROLE_INCLUDE):
        return False
    if any(p.search(text) for p in ROLE_EXCLUDE):
        return False
    # experience (soft filter; not all postings state years explicitly)
    # You can tighten this to reject outside 2-5 yrs if you wish.
    exp_hit = any(p.search(text) for p in EXP_PATTERNS)
    return True

def extract_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(base_url, a["href"])
        if not title:
            continue
        if any(p.search(title) for p in ROLE_INCLUDE) and not any(p.search(title) for p in ROLE_EXCLUDE):
            links.append((title, href))
    # also capture job-card like elements
    for el in soup.select("[class*='job'], [class*='career'], [class*='position']"):
        t = " ".join(el.get_text(" ", strip=True).split())
        if t and text_ok(t):
            link = el.find("a", href=True)
            href = urljoin(base_url, link["href"]) if link else base_url
            links.append((t, href))
    # de-dup
    seen = set()
    out = []
    for t, h in links:
        key = (t.lower(), h)
        if key not in seen:
            seen.add(key)
            out.append((t, h))
    return out

def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text

def pick_country(text: str, company_countries):
    # simple heuristic: if any priority location word appears in title, keep it; else accept and rely on company_countries
    for country in LOC_PRIORITY:
        if re.search(country, text, re.I):
            return country
    # fallback: if company has a country in priority list, pick the first that is in priority
    for country in LOC_PRIORITY:
        if country in (company_countries or []):
            return country
    return ""

def main():
    rows = []
    for c in cfg["companies"]:
        name = c["name"]
        url  = c["careers_url"]
        countries = c.get("countries", [])

        if not url:
            continue

        try:
            html = fetch(url)
        except Exception as e:
            print(f"[warn] {name}: fetch failed: {e}", file=sys.stderr)
            continue

        for title, href in extract_links(url, html):
            text = f"{title} {href}"
            if not text_ok(text):
                continue
            country_guess = pick_country(text, countries)

            # location gating: keep only if in priority set (if we can guess)
            if country_guess and country_guess not in LOC_PRIORITY:
                continue

            rows.append({
                "Company": name,
                "Role": title,
                "Experience": "",     # often not explicit; left blank unless you want to parse details
                "Location": country_guess,
                "Link": href
            })

        time.sleep(0.5)  # be polite

    # Sort by location priority then company
    def loc_rank(loc):
        try:
            return LOC_PRIORITY.index(loc)
        except ValueError:
            return 999

    rows.sort(key=lambda r: (loc_rank(r["Location"]), r["Company"].lower(), r["Role"].lower()))

    # Write CSV (headers must match your site’s table)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Company", "Role", "Experience", "Location", "Link"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} rows to jobs.csv")

if __name__ == "__main__":
    main()
