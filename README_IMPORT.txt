# NewSpace Jobs Scraper (GitHub Actions)

Files to copy to your repository root:

- `.github/workflows/scrape.yml`
- `scraper/requirements.txt`
- `scraper/companies.yaml`
- `scraper/scrape.py`

After committing, run the workflow once from **Actions**. The workflow runs every Saturday morning around 08:00 CET/CEST (via 06:00 & 07:00 UTC).
Update `scraper/companies.yaml` with the correct career URLs.
