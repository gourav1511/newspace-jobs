// Robust CSV → HTML table for GitHub Pages
document.addEventListener("DOMContentLoaded", () => {
  const CSV_FILE = "scraper/Jobs.csv";
  const CSV_URL = new URL(`${CSV_FILE}?ts=${Date.now()}`, document.baseURI).toString();
  const TABLE_ID = "jobs-table";
  const PREFERRED_ORDER = ["Company", "Role", "Experience", "Location", "Link"];

  function parseCSV(text) {
    const out = [];
    let row = [], field = "", i = 0, inQuotes = false;
    while (i < text.length) {
      const c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
          inQuotes = false; i++; continue;
        }
        field += c; i++; continue;
      }
      if (c === '"') { inQuotes = true; i++; continue; }
      if (c === ",") { row.push(field); field = ""; i++; continue; }
      if (c === "\r") { i++; continue; }
      if (c === "\n") { row.push(field); out.push(row); row = []; field = ""; i++; continue; }
      field += c; i++;
    }
    row.push(field);
    if (row.length && (row.length > 1 || row[0].trim() !== "")) out.push(row);
    return out;
  }

  function ensureTable() {
    let t = document.getElementById(TABLE_ID);
    if (!t) {
      t = document.createElement("table");
      t.id = TABLE_ID;
      document.body.appendChild(t);
    }
    t.innerHTML = "";
    return t;
  }

  function buildTable(headers, rows) {
    const table = ensureTable();
    const idx = {};
    headers.forEach((h, i) => { idx[h.trim()] = i; });

    const show = PREFERRED_ORDER.filter(h => idx[h] !== undefined);
    if (!show.length) show.push(...headers);

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    show.forEach(h => { const th = document.createElement("th"); th.textContent = h; trh.appendChild(th); });
    thead.appendChild(trh);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach(r => {
      const tr = document.createElement("tr");
      show.forEach(h => {
        const td = document.createElement("td");
        const i = idx[h];
        const v = i !== undefined ? (r[i] ?? "") : "";
        if (h === "Link" && v) {
          const a = document.createElement("a");
          a.href = v; a.target = "_blank"; a.rel = "noopener";
          a.textContent = "Apply";
          td.appendChild(a);
        } else {
          td.textContent = v;
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  fetch(CSV_URL, { cache: "no-store" })
    .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.text(); })
    .then(t => {
      const rows = parseCSV(t);
      if (!rows.length) { console.warn("CSV empty"); return; }
      const headers = rows[0].map(h => h.trim());
      buildTable(headers, rows.slice(1));
    })
    .catch(err => {
      console.error("Failed to load scraper/Jobs.csv:", err);
      const t = ensureTable();
      t.innerHTML = "<caption>Failed to load scraper/Jobs.csv</caption>";
    });
});
