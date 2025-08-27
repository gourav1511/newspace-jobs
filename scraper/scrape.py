import csv
import re
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode, parse_qsl
import requests
from bs4 import BeautifulSoup

# --- your existing regex filters (kept as-is) ---
ROLE_INCLUDE = [
    re.compile(r"manager", re.I),
    re.compile(r"project", re.I),
    re.compile(r"solutions engineer", re.I),
    re.compile(r"customer success", re.I),
    re.compile(r"manager", re.I),
    re.compile(r"sales", re.I),
]
ROLE_EXCLUDE = [
    re.compile(r"marketing", re.I),
    re.compile(r"finance", re.I),
]

LOC_PRIORITY = {
    "Germany": 1,
    "Luxembourg": 2,
    "UK": 3,
    "United Kingdom": 3,
    "Sweden": 4,
    "USA": 5,
    "United States": 5,
}

# --- helpers ---
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign",
                   "utm_term", "utm_content", "gclid", "fbclid"}

def normalize_url(u: str) -> str:
    """Strip hash + common tracking params + trailing slash for consistent de-dup keys."""
    try:
        s = urlsplit(u)
        q = [(k, v) for (k, v) in parse_qsl(s.query, keep_blank_values=True)
             if k not in TRACKING_PARAMS]
        path = s.path.rstrip("/")
        return urlunsplit((s.scheme.lower(), s.netloc.lower(), path,
                           urlencode(q, doseq=True), ""))  # no fragment
    except Exception:
        return (u or "").strip()

def clean_title(t: str) -> str:
    """Collapse whitespace; trim verbose descriptions."""
    t = " ".join((t or "").split())
    cut_tokens = [" learn more", " read more", " apply now", " see more"]
    tl = t.lower()
    for tok in cut_tokens:
        i = tl.find(tok)
        if i > 0:
            t = t[:i].strip()
            break
    if len(t) > 120:  # hard cap
        t = t[:120].rstrip() + "…"
    return t

def better_title(a: str, b: str) -> str:
    """Choose the more 'title-like' string for same URL."""
    a, b = (a or "").strip(), (b or "").strip()
    if not a: return b
    if not b: return a
    if abs(len(a) - len(b)) > 15:
        return a if len(a) < len(b) else b
    pa = sum(ch in ".:;!?" for ch in a)
    pb = sum(ch in ".:;!?" for ch in b)
    return a if pa < pb else b

def fetch(url: str) -> str:
    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def text_ok(text: str) -> bool:
    return any(p.search(text) for p in ROLE_INCLUDE) and not any(p.search(text) for p in ROLE_EXCLUDE)

def pick_country(text: str, countries):
    for c in countries:
        if re.search(rf"\b{re.escape(c)}\b", text, re.I):
            return c
    return ""

def extract_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")
    candidates = []

    # 1) Direct anchors
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(base_url, a["href"])
        if not title:
            continue
        if any(p.search(title) for p in ROLE_INCLUDE) and not any(p.search(title) for p in ROLE_EXCLUDE):
            candidates.append((clean_title(title), href))

    # 2) Job-card-like elements
    for el in soup.select("[class*='job'], [class*='career'], [class*='position']"):
        t = " ".join(el.get_text(" ", strip=True).split())
        if t and text_ok(t):
            link = el.find("a", href=True)
            href = urljoin(base_url, link["href"]) if link else base_url
            candidates.append((clean_title(t), href))

    # Deduplicate by URL
    by_url = {}
    for t, h in candidates:
        key = normalize_url(h)
        if key in by_url:
            by_url[key] = better_title(by_url[key], t)
        else:
            by_url[key] = t

    return [(title, url) for url, title in by_url.items()]

# --- main ---
def main():
    cfg = {
        "companies": [
            # Example entries; expand as needed
            {"name": "AAC Clyde Space", "careers_url": "https://aac-clyde.space/careers", "countries": ["Sweden", "UK"]},
            {"name": "Spire", "careers_url": "https://spire.com/careers", "countries": ["Luxembourg", "USA", "UK"]},
            # add more...
        ]
    }

    rows = []
    seen_links = set()

    for c in cfg["companies"]:
        name = c["name"]
        url = c["careers_url"]
        countries = c.get("countries", [])

        if not url:
            continue

        try:
            html = fetch(url)
        except Exception as e:
            print(f"[warn] {name}: fetch failed: {e}", file=sys.stderr)
            continue

        for title, href in extract_links(url, html):
            key = normalize_url(href)
            if key in seen_links:
                continue
            seen_links.add(key)

            text = f"{title} {href}"
            if not text_ok(text):
                continue
            country_guess = pick_country(text, countries)

            if country_guess and country_guess not in LOC_PRIORITY:
                continue

            rows.append({
                "Company": name,
                "Role": title,
                "Experience": "",
                "Location": country_guess,
                "Link": href
            })

        time.sleep(0.5)

    with open("Jobs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company", "Role", "Experience", "Location", "Link"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
