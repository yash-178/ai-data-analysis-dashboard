/* ==========================================================================
   dataset.js — handles file upload, overview rendering (Dashboard tab),
   dataset statistics + search/filter (Dataset tab).
   ========================================================================== */

const AppState = {
  hasDataset: false,
  filename: null,
  overview: null,
  columns: { numeric: [], categorical: [], datetime: [], boolean: [] },
};

/* ---------------- Upload ---------------- */
async function handleFileUpload(file) {
  if (!file) return;
  const allowed = ["csv", "xlsx", "xls"];
  const ext = file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast("Unsupported file type. Please upload a .csv, .xlsx, or .xls file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  showLoading("Uploading and analyzing dataset…");
  try {
    const res = await API.postForm("/api/upload", formData);
    showToast(res.message || "Dataset uploaded successfully.", "success");
    AppState.hasDataset = true;
    AppState.filename = file.name;
    AppState.overview = res.overview;
    updateSidebarChip();
    await refreshColumns();
    renderDashboard(res.overview);
    unlockAllSections();
    // If user is on dataset/cleaning/etc, refresh those too
    if (typeof onDatasetLoaded === "function") onDatasetLoaded();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

function updateSidebarChip() {
  const chip = document.getElementById("sidebarDatasetChip");
  const name = document.getElementById("sidebarDatasetName");
  if (AppState.hasDataset) {
    chip.classList.add("active");
    name.textContent = AppState.filename;
  } else {
    chip.classList.remove("active");
    name.textContent = "No dataset loaded";
  }
}

function unlockAllSections() {
  // Maps each section's nav/page key to the actual DOM id prefix used in
  // index.html. Most sections use their full name as the prefix, but the
  // Visualizations section uses the shortened "viz" prefix (vizGate /
  // vizContent) — this map keeps that in sync instead of assuming a 1:1
  // match between section name and element id.
  const idPrefixes = {
    dashboard: "dashboard",
    dataset: "dataset",
    cleaning: "cleaning",
    visualizations: "viz",
    insights: "insights",
    report: "report",
  };
  Object.keys(idPrefixes).forEach((s) => {
    const prefix = idPrefixes[s];
    const gate = document.getElementById(`${prefix}Gate`) || document.getElementById(`${prefix}Empty`);
    const content = document.getElementById(`${prefix}Content`);
    if (gate) gate.classList.add("hidden");
    if (content) content.classList.remove("hidden");
  });
}

async function refreshColumns() {
  try {
    const res = await API.get("/api/columns");
    AppState.columns = res.columns;
    populateColumnDropdowns();
  } catch (err) {
    console.error(err);
  }
}

/* ---------------- Dashboard rendering ---------------- */
function renderDashboard(overview) {
  AppState.overview = overview;

  const kpiGrid = document.getElementById("kpiGrid");
  const missingTotal = overview.missing.reduce((sum, m) => sum + m.missing_count, 0);
  kpiGrid.innerHTML = `
    ${kpiCard("Total Rows", formatNumber(overview.rows), `${overview.filename || "dataset"}`, "var(--indigo)")}
    ${kpiCard("Total Columns", formatNumber(overview.columns), `${overview.column_types.numeric.length} numeric · ${overview.column_types.categorical.length} categorical`, "var(--cyan)")}
    ${kpiCard("Missing Cells", formatNumber(missingTotal), missingTotal > 0 ? "Needs attention" : "Clean dataset", missingTotal > 0 ? "var(--warning)" : "var(--success)")}
    ${kpiCard("Duplicate Rows", formatNumber(overview.duplicates.duplicate_rows), `${overview.duplicates.duplicate_pct}% of rows`, overview.duplicates.duplicate_rows > 0 ? "var(--critical)" : "var(--success)")}
  `;

  // Data types table
  document.getElementById("dtypeTableWrap").innerHTML = renderTable(
    overview.dtypes.map((d) => ({ column: d.column, type: badgeForType(d.dtype), dtype: d.dtype })),
    { columns: ["column", "dtype", "type"], headerLabels: { column: "Column", dtype: "Pandas dtype", type: "Category" } }
  );

  // Missing values table
  const missingRows = overview.missing.filter((m) => m.missing_count > 0);
  document.getElementById("missingTableWrap").innerHTML = missingRows.length
    ? renderTable(
        missingRows.map((m) => ({
          column: m.column,
          missing_count: formatNumber(m.missing_count),
          missing_pct: barCell(m.missing_pct),
        })),
        { columns: ["column", "missing_count", "missing_pct"], headerLabels: { column: "Column", missing_count: "Missing", missing_pct: "% Missing" } }
      )
    : `<p style="color:var(--success); font-size:13px; padding:8px 0;">✓ No missing values detected.</p>`;

  // Preview table
  document.getElementById("previewTableWrap").innerHTML = renderTable(overview.preview, {
    emptyMessage: "Dataset is empty.",
  });

  document.getElementById("dashboardEmpty").classList.add("hidden");
  document.getElementById("dashboardContent").classList.remove("hidden");
}

function kpiCard(label, value, sub, accent) {
  return `
    <div class="kpi-card" style="--kpi-accent:${accent}">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-sub">${sub}</div>
    </div>`;
}

function barCell(pct) {
  const clamped = Math.min(100, pct);
  return `<div>${pct}%<div class="bar-mini"><div style="width:${clamped}%; background:${pct > 40 ? "var(--critical)" : "var(--warning)"}"></div></div></div>`;
}

/* ---------------- Dataset tab: stats + search/filter ---------------- */
async function loadDatasetTab() {
  if (!AppState.hasDataset) return;
  const overview = AppState.overview || (await API.get("/api/overview")).overview;

  const numRows = (overview.stats.numeric || []).map((s) => ({
    column: s.column,
    count: formatNumber(s.count),
    mean: formatNumber(s.mean),
    std: formatNumber(s.std),
    min: formatNumber(s.min),
    max: formatNumber(s.max),
  }));
  document.getElementById("numericStatsWrap").innerHTML = renderTable(numRows, {
    columns: ["column", "count", "mean", "std", "min", "max"],
    headerLabels: { column: "Column", count: "Count", mean: "Mean", std: "Std Dev", min: "Min", max: "Max" },
    emptyMessage: "No numeric columns in this dataset.",
  });

  const catRows = (overview.stats.categorical || []).map((s) => ({
    column: s.column,
    unique: formatNumber(s.unique),
    top: s.top ?? "—",
    freq: formatNumber(s.freq),
  }));
  document.getElementById("categoricalStatsWrap").innerHTML = renderTable(catRows, {
    columns: ["column", "unique", "top", "freq"],
    headerLabels: { column: "Column", unique: "Unique Values", top: "Most Common", freq: "Frequency" },
    emptyMessage: "No categorical columns in this dataset.",
  });

  populateFilterColumnDropdown();
  document.getElementById("filterResultsWrap").innerHTML = "";
  document.getElementById("filterMeta").textContent = "";
}

function populateFilterColumnDropdown() {
  const select = document.getElementById("filterColumn");
  const all = [...AppState.columns.numeric, ...AppState.columns.categorical, ...AppState.columns.datetime, ...AppState.columns.boolean];
  select.innerHTML = all.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
}

async function runSearch(query) {
  try {
    const res = await API.post("/api/search", { query });
    document.getElementById("filterMeta").textContent = `Showing ${res.count} of ${res.total} rows matching "${query}"`;
    document.getElementById("filterResultsWrap").innerHTML = renderTable(res.preview, { emptyMessage: "No matching rows found." });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function runFilter() {
  const column = document.getElementById("filterColumn").value;
  const operator = document.getElementById("filterOperator").value;
  const value = document.getElementById("filterValue").value;
  if (!value) {
    showToast("Enter a value to filter by.", "error");
    return;
  }
  try {
    const res = await API.post("/api/filter", { column, operator, value });
    document.getElementById("filterMeta").textContent = `Showing ${res.count} of ${res.total} rows where ${column} ${operator.replace("_", " ")} "${value}"`;
    document.getElementById("filterResultsWrap").innerHTML = renderTable(res.preview, { emptyMessage: "No matching rows found." });
  } catch (err) {
    showToast(err.message, "error");
  }
}

function clearFilter() {
  document.getElementById("searchInput").value = "";
  document.getElementById("filterValue").value = "";
  document.getElementById("filterMeta").textContent = "";
  document.getElementById("filterResultsWrap").innerHTML = "";
}
