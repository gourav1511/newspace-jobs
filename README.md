## Job Board Dashboard

This simple website provides a lightweight dashboard for weekly job updates. It’s
designed with non‑technical users in mind: you only need to update a CSV file or
publish a Google&nbsp;Sheet to keep the listings current. The page itself remains
static and automatically loads whatever is in the `jobs.csv` file.

### Files

* **index.html** – The main webpage that displays the job table.
* **style.css** – Basic styling for the layout and table.
* **script.js** – JavaScript that reads data from `jobs.csv` and populates the
  table. In the initial version of this site we have already configured
  `script.js` to load data from your published Google Sheet. If you
  publish a different Sheet later, edit the `fetch(...)` call in
  `script.js` accordingly.
* **jobs.csv** – A comma‑separated file containing one row per job. The first
  line is the header (`Company,Role,Experience,Location,Link`). Each
  subsequent row must have values enclosed in quotes if they contain commas.

### Updating the listings

1. Edit **jobs.csv** with a text editor or spreadsheet application. Each row
   should include:
   - Company name.
   - Role title (e.g., *Project Manager*).
   - Desired experience range (e.g., *2+ years – 5 years*).
   - Location (e.g., *Munich, Germany*).
   - A URL pointing directly to the job posting on the employer’s website.
2. Save the file in CSV format and replace the existing `jobs.csv` in the
   site folder.
3. When you open `index.html` in a browser, the table will reflect the new
   entries automatically.

### Pulling from Google Sheets (optional)

If you prefer to manage data in a Google Sheet instead of a local CSV file,
follow these steps:

1. Create a new Google Sheet and insert your job data using the same
   column order as `jobs.csv` (Company, Role, Experience, Location, Link).
2. From the Sheet menu, choose **File → Share → Publish to web**. Publish the
   entire sheet as a **Comma Separated Values (CSV)** format. Google will give
   you a link ending with `output=csv`.
3. In **script.js**, replace `fetch('jobs.csv')` with `fetch('URL')`, where
   `URL` is the link from step 2. The site will now load data from the Sheet
   directly.

### Automating weekly updates

Google Sheets automatically recalculates and refreshes data from import
functions like `IMPORTXML` or `IMPORTFEED` roughly every hour【462126922950035†L122-L127】, so you
can use built‑in formulas to scrape company career pages each week. For example,
Ben Collins’ tutorial shows how you can pull structured data from a website
into a sheet with the `IMPORTXML` function【16327416756003†L34-L41】. By combining such formulas with
a time‑driven Google Apps Script trigger, your Sheet can automatically collect
new listings every Saturday at 11:30 AM IST and then populate the dashboard.

When you are ready to share your dashboard publicly, upload these files to a
hosting service such as GitHub Pages, Netlify, or your own domain. Because the
site is static, no server‑side code is needed, and hosting is free on many
platforms.