import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode, parse_qsl

import requests
import yaml
from bs4 import BeautifulSoup

# =========================
# Utilities
# =========================

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid"
}

GENERIC_TITLE_PATTERNS = [
    re.compile(r"\bopen (roles?|positions?)\b", re.I),
    re.compile(r"\ball locations?\b", re.I),
    re.compile(r"\ball departments?\b", re.I),
    re.compile(r"\bview all\b", re.I),
    re.compile(r"\bcareers?\b", re.I),
]

ATS_PATTERNS = {
    "greenhouse": re.compile(r"boards\.greenhouse\.io/([^/\"'\s]+)", re.I),
    "lever":      re.compile(r"jobs\.lever\.co/([^/\"'\s]+)", re.I),
    "personio":   re.compile(r"([a-z0-9-]+)\.jobs\.personio\.de", re.I),
    "recruitee":  re.compile(r"([a-z0-9-]+)\.recruitee\.com", re.I),
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

def normalize_url(u: str) -> str:
    """Strip hash + tracking params + trailing slash for stable de-dup keys."""
    try:
        s = urlsplit(u)
        q = [(k, v) for (k, v) in parse_qsl(s.query, keep_blank_values=True)
             if k not in TRACKING_PARAMS]
        path = s.path.rstrip("/")
        return urlunsplit((s.scheme.lower(), s.netloc.lower(), path,
                           urlencode(q, doseq=True), ""))  # no fragment
    except Exception:
        return (u or "").strip()

def fetch(url: str) -> str:
    resp = requests.get(url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def fetch_json(url: str):
    r = requests.get(url, timeout=20, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def clean_title(t: str) -> str:
    """Collapse whitespace; remove marketing tails; clamp very long blobs."""
    t = " ".join((t or "").split())
    tl = t.lower()
    for tok in (" learn more", " read more", " apply now", " see more"):
        i = tl.find(tok)
        if i > 0:
            t = t[:i].strip()
            break
    if len(t) > 120:
        t = t[:120].rstrip() + "…"
    return t

def better_title(a: str, b: str) -> str:
    """Pick the more 'title-like' string for the same URL."""
    a, b = (a or "").strip(), (b or "").strip()
    if not a: return b
    if not b: return a
    if abs(len(a) - len(b)) > 15:
        return a if len(a) < len(b) else b
    pa = sum(ch in ".:;!?" for ch in a)
    pb = sum(ch in ".:;!?" for ch in b)
    return a if pa < pb else b

def is_generic_title(title: str) -> bool:
    t = (title or "").strip()
    return any(p.search(t) for p in GENERIC_TITLE_PATTERNS)

def is_generic_href(href: str, base_url: str) -> bool:
    """
    Treat links that land on the careers root/same page/hash/filter as generic.
    """
    try:
        base_norm = normalize_url(base_url)
        href_norm = normalize_url(href)
        if not href_norm:
            return True
        if href_norm == base_norm:
            return True

        b = urlsplit(base_norm)
        h = urlsplit(href_norm)
        same_netloc = (b.netloc == h.netloc)

        base_path = b.path.rstrip("/")
        href_path = h.path.rstrip("/")
        looks_like_root = href_path in {base_path, (base_path + "/careers").rstrip("/")}
        only_query_or_hash = (href_path == base_path) and (h.query or h.fragment)

        if same_netloc and (looks_like_root or only_query_or_hash):
            return True
    except Exception:
        return False
    return False

# =========================
# Config & filtering
# =========================

def load_config():
    cfg_path = Path(__file__).parent / "companies.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def compile_patterns(str_list):
    """
    Turn YAML strings into case-insensitive regex objects.
    - 're:<pattern>' is treated as raw regex.
    - Otherwise use substring match via re.escape().
    """
    pats = []
    for item in (str_list or []):
        s = item.strip()
        if not s:
            continue
        if s.startswith("re:"):
            pats.append(re.compile(s[3:], re.I))
        else:
            pats.append(re.compile(re.escape(s), re.I))
    return pats

def matches(title: str, include_pats, exclude_pats) -> bool:
    """
    Enforce YAML as single source of truth:
    - include list MUST be non-empty and at least one must match.
    - exclude list drops the match.
    """
    if not include_pats:
        return False
    if not any(p.search(title) for p in include_pats):
        return False
    if exclude_pats and any(p.search(title) for p in exclude_pats):
        return False
    return True

# =========================
# Static HTML scraping
# =========================

def extract_links_static(base_url: str, html: str, include_pats, exclude_pats):
    soup = BeautifulSoup(html, "lxml")
    candidates = []

    # 1) Plain anchors
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title:
            continue
        href = urljoin(base_url, a["href"])
        title = clean_title(title)

        if is_generic_title(title) or is_generic_href(href, base_url):
            continue

        if matches(title, include_pats, exclude_pats):
            candidates.append((title, href))

    # 2) Job-card-like containers
    for el in soup.select("[class*='job'], [class*='career'], [class*='position']"):
        t = " ".join(el.get_text(" ", strip=True).split())
        if not t:
            continue
        link = el.find("a", href=True)
        href = urljoin(base_url, link["href"]) if link else base_url
        t = clean_title(t)

        if is_generic_title(t) or is_generic_href(href, base_url):
            continue

        if matches(t, include_pats, exclude_pats):
            candidates.append((t, href))

    # De-dup by URL; pick best title per URL
    by_url = {}
    for t, h in candidates:
        key = normalize_url(h)
        if key in by_url:
            by_url[key] = better_title(by_url[key], t)
        else:
            by_url[key] = t

    return [(title, url) for url, title in by_url.items()]

# =========================
# ATS adapters
# =========================

def list_greenhouse(board: str):
    """Greenhouse public API: https://boards-api.greenhouse.io/v1/boards/{board}/jobs"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    data = fetch_json(url)
    out = []
    for job in data.get("jobs", []):
        title = clean_title(job.get("title") or "")
        link = job.get("absolute_url") or ""
        if title and link:
            out.append((title, link))
    return out

def list_lever(company: str):
    """Lever public API: https://api.lever.co/v0/postings/{company}?mode=json"""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    data = fetch_json(url)
    out = []
    for job in data:
        title = clean_title(job.get("text") or job.get("title") or "")
        link = job.get("hostedUrl") or job.get("applyUrl") or ""
        if title and link:
            out.append((title, link))
    return out

def list_personio(subdomain: str):
    """
    Personio public search JSON.
    Typical endpoint: https://{sub}.jobs.personio.de/search.json
    - Some tenants return a dict with "jobPostings": [...]
    - Others return a list at the root.
    This function handles both and normalizes (title, link).
    """
    url = f"https://{subdomain}.jobs.personio.de/search.json"
    data = fetch_json(url)

    # Normalize to a list of postings
    if isinstance(data, dict):
        postings = (
            data.get("jobPostings")
            or data.get("items")
            or data.get("postings")
            or []
        )
    elif isinstance(data, list):
        postings = data
    else:
        postings = []

    out = []
    for job in postings:
        if not isinstance(job, dict):
            continue

        # Title fields vary: "name", "title", "position"
        title = job.get("name") or job.get("title") or job.get("position") or ""

        # URL fields vary:
        # - "url" may be relative or absolute
        # - some return "postingUrl" or "urls" dict
        link = (
            job.get("url")
            or job.get("postingUrl")
            or (job.get("urls") or {}).get("careers")
            or ""
        )

        # Build absolute URL if needed
        if link and not link.startswith("http"):
            link = f"https://{subdomain}.jobs.personio.de{link}"

        title = clean_title(title)
        if title and link:
            out.append((title, link))

    return out

def list_recruitee(subdomain: str):
    """Recruitee public API: https://{sub}.recruitee.com/api/offers/"""
    url = f"https://{subdomain}.recruitee.com/api/offers/"
    data = fetch_json(url)
    out = []
    for item in data.get("offers", []):
        title = clean_title(item.get("title") or "")
        slug = item.get("slug") or ""
        link = f"https://{subdomain}.recruitee.com/o/{slug}" if slug else ""
        if title and link:
            out.append((title, link))
    return out

def auto_detect_ats(html: str):
    """Try to infer ATS provider + token from page HTML."""
    for ats, rx in ATS_PATTERNS.items():
        m = rx.search(html or "")
        if m:
            token = m.group(1)
            return ats, token
    return None, None

def list_from_ats(ats_cfg: dict, html: str):
    """Return [(title, link)] via explicit ATS config or auto-detection."""
    if ats_cfg:
        t = (ats_cfg.get("type") or "").strip().lower()
        if t == "greenhouse" and ats_cfg.get("board"):
            return list_greenhouse(ats_cfg["board"])
        if t == "lever" and ats_cfg.get("company"):
            return list_lever(ats_cfg["company"])
        if t == "personio" and ats_cfg.get("subdomain"):
            return list_personio(ats_cfg["subdomain"])
        if t == "recruitee" and ats_cfg.get("subdomain"):
            return list_recruitee(ats_cfg["subdomain"])

    # fallback: try auto-detection
    ats, token = auto_detect_ats(html)
    if ats == "greenhouse":
        return list_greenhouse(token)
    if ats == "lever":
        return list_lever(token)
    if ats == "personio":
        return list_personio(token)
    if ats == "recruitee":
        return list_recruitee(token)

    return []

# =========================
# Main
# =========================

def main():
    cfg = load_config()

    roles_cfg = (cfg.get("roles") or {})
    include_pats = compile_patterns(roles_cfg.get("include") or [])
    exclude_pats = compile_patterns(roles_cfg.get("exclude") or [])

    if not include_pats:
        print("[error] roles.include in companies.yaml is empty — nothing will match.", file=sys.stderr)
        sys.exit(1)

    rows = []
    seen_links = set()

    for comp in cfg.get("companies", []):
        name = (comp.get("name") or "").strip()
        careers_url = (comp.get("careers_url") or "").strip()
        ats_cfg = comp.get("ats") or {}

        if not name or not careers_url:
            continue

        try:
            html = fetch(careers_url)
        except Exception as e:
            print(f"[warn] {name}: fetch failed: {e}", file=sys.stderr)
            continue

        # 1) Try static HTML first
        items = extract_links_static(careers_url, html, include_pats, exclude_pats)

        # 2) If nothing found, try ATS adapters (explicit or auto-detect)
        if not items:
            items = list_from_ats(ats_cfg, html)

        # Filter by include/exclude again (for ATS results) and de-dup by URL
        for title, href in items:
            if not matches(title, include_pats, exclude_pats):
                continue
            key = normalize_url(href)
            if key in seen_links:
                continue
            seen_links.add(key)

            rows.append({
                "Company": name,
                "Role": title,
                "Link": href
            })

        time.sleep(0.3)  # be polite

    # Write minimal CSV to scraper/Jobs.csv
    out_path = Path(__file__).resolve().parents[1] / "scraper" / "Jobs.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Company","Role","Link"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
