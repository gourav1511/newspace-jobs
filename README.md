# NewSpace Job Board Dashboard

This repository hosts a static website that displays weekly job openings from NewSpace companies. The page itself is static; job data is loaded at runtime from a CSV file.

## How it works

- `script.js` fetches `scraper/Jobs.csv` with a cache-busting query string and renders it as an HTML table. Columns appear based on the headers present in the CSV, so optional fields like Experience or Location show up only when they exist.
- `scraper/` contains a Python scraper that crawls company career pages listed in `scraper/companies.yaml` and writes a minimal `Jobs.csv` file (Company, Role, Link).
- A scheduled GitHub Actions workflow (`.github/workflows/scrape.yml`) runs the scraper every Saturday around 08:00 CET/CEST and commits updated data back to the repository.

## Repository structure

- `index.html` – main web page.
- `style.css` – simple styling.
- `script.js` – CSV loading and table rendering logic; edit the `CSV_URL` constant if you want to load data from a different CSV or a published Google Sheet.
- `scraper/` – Python code and configuration for automated scraping:
  - `scraper/Jobs.csv` – generated job listings.
  - `scraper/companies.yaml` – list of companies and role filters.
  - `scraper/scrape.py` – script that outputs `scraper/Jobs.csv`.
  - `scraper/requirements.txt` – Python dependencies.

## Updating the listings

### Automatic scrape

1. Install Python dependencies:
   ```sh
   pip install -r scraper/requirements.txt
   ```
2. Adjust `scraper/companies.yaml` to define which companies to scan and any role filters.
3. Run the scraper:
   ```sh
   python scraper/scrape.py
   ```
   This overwrites `scraper/Jobs.csv` with fresh listings.
4. Open `index.html` in a browser; the page will show the updated table.

### Using a custom CSV or Google Sheet

If you prefer to curate listings manually, publish a Google Sheet (or provide another CSV) and update the `CSV_URL` in `script.js` to point at it. The table will adapt to whatever columns your file provides.

## Hosting

Because the site is static, it can be hosted on GitHub Pages, Netlify, or any other static hosting service.

