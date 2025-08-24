// Simple script to populate the jobs table from a CSV file.

document.addEventListener('DOMContentLoaded', () => {
  // Fetch the CSV data.  By default this script loads a local jobs.csv file.
  // However, you can point it at a published Google Sheet.  In this version
  // we hard‑code the export URL of the user’s Sheet to simplify updates.
  // If you later change your sheet ID or publish a different sheet, update
  // the link below.  See the README for instructions on publishing a sheet
  // as CSV.
  // Fetch data from the published Google Sheet.  The user has published their
  // sheet via the `pubhtml` endpoint.  To access the raw CSV, change the
  // suffix to `pub?gid=0&single=true&output=csv`.  If you later publish a
  // different sheet or add more tabs, update this URL accordingly.
  fetch('https://docs.google.com/spreadsheets/d/e/2PACX-1vRXIYbN66p93YaPqqr2pU5Pj7rpoibHksrJfSEj_Hf3KYHknunVyRs4XRBB9WdSZxuHUFhBzYA3gEV8/pub?gid=0&single=true&output=csv')
    .then((response) => response.text())
    .then((data) => {
      // Split the data into lines and ignore empty lines.
      const rows = data
        .trim()
        .split(/\r?\n/)
        .filter((line) => line.length > 0);

      if (rows.length <= 1) return;

      // A regular expression to split CSV values by commas that are not inside quotes.
      const csvSplit = /,(?=(?:[^"]*"[^"]*")*[^"]*$)/;

      // Skip the header row (index 0).
      const tbody = document.getElementById('jobs-tbody');
      for (let i = 1; i < rows.length; i++) {
        const cols = rows[i]
          .split(csvSplit)
          .map((c) => c.replace(/^"|"$/g, '').trim());

        const tr = document.createElement('tr');

        // Company
        const companyCell = document.createElement('td');
        companyCell.textContent = cols[0];
        tr.appendChild(companyCell);

        // Role
        const roleCell = document.createElement('td');
        roleCell.textContent = cols[1];
        tr.appendChild(roleCell);

        // Experience
        const expCell = document.createElement('td');
        expCell.textContent = cols[2];
        tr.appendChild(expCell);

        // Location
        const locCell = document.createElement('td');
        locCell.textContent = cols[3];
        tr.appendChild(locCell);

        // Link (last column)
        const linkCell = document.createElement('td');
        const link = document.createElement('a');
        link.href = cols[4];
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Apply';
        linkCell.appendChild(link);
        tr.appendChild(linkCell);

        tbody.appendChild(tr);
      }
    })
    .catch((err) => {
      console.error('Error loading jobs:', err);
    });
});