/* ==========================================================================
   cleaning.js — Data Cleaning tab: diagnostics + apply/auto-clean/reset.
   ========================================================================== */

async function loadCleaningTab() {
  if (!AppState.hasDataset) return;
  try {
    const res = await API.get("/api/cleaning/summary");
    renderCleaningSummary(res.summary);
    renderCleaningLog(res.log);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderCleaningSummary(summary) {
  const kpiGrid = document.getElementById("cleaningKpis");
  kpiGrid.innerHTML = `
    ${kpiCard("Total Rows", formatNumber(summary.rows), "In current dataset", "var(--indigo)")}
    ${kpiCard("Missing Cells", formatNumber(summary.total_missing_cells), "Across all columns", summary.total_missing_cells > 0 ? "var(--warning)" : "var(--success)")}
    ${kpiCard("Duplicate Rows", formatNumber(summary.duplicates.duplicate_rows), `${summary.duplicates.duplicate_pct}% of rows`, summary.duplicates.duplicate_rows > 0 ? "var(--critical)" : "var(--success)")}
    ${kpiCard("Column Types", `${summary.column_types.numeric.length}N / ${summary.column_types.categorical.length}C`, "Numeric / Categorical", "var(--cyan)")}
  `;

  const missingRows = summary.missing.filter((m) => m.missing_count > 0);
  document.getElementById("cleaningMissingWrap").innerHTML = missingRows.length
    ? renderTable(
        missingRows.map((m) => ({ column: m.column, missing_count: formatNumber(m.missing_count), missing_pct: barCell(m.missing_pct) })),
        { columns: ["column", "missing_count", "missing_pct"], headerLabels: { column: "Column", missing_count: "Missing", missing_pct: "% Missing" } }
      )
    : `<p style="color:var(--success); font-size:13px;">✓ No missing values detected.</p>`;

  const typeRows = [];
  Object.entries(summary.column_types).forEach(([type, cols]) => {
    cols.forEach((c) => typeRows.push({ column: c, type: badgeForType(type === "numeric" ? "float" : type) }));
  });
  document.getElementById("cleaningTypesWrap").innerHTML = renderTable(typeRows, {
    columns: ["column", "type"],
    headerLabels: { column: "Column", type: "Detected Type" },
    emptyMessage: "No columns found.",
  });
}

function renderCleaningLog(log) {
  const list = document.getElementById("cleaningLogList");
  if (!log || log.length === 0) {
    list.innerHTML = `<li class="log-empty">No cleaning actions applied yet.</li>`;
    return;
  }
  list.innerHTML = log.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("");
}

function gatherCleaningOptions() {
  return {
    drop_duplicates: document.getElementById("optDropDuplicates").checked,
    trim_whitespace: document.getElementById("optTrimWhitespace").checked,
    convert_dates: document.getElementById("optConvertDates").checked,
    standardize_case: document.getElementById("optCaseMode").value,
    missing_strategy: document.getElementById("optMissingStrategy").value,
    missing_threshold: parseFloat(document.getElementById("optMissingThreshold").value) || 50,
  };
}

async function applySelectedCleaning() {
  showLoading("Applying cleaning operations…");
  try {
    const options = gatherCleaningOptions();
    const res = await API.post("/api/cleaning/apply", options);
    showToast("Cleaning operations applied.", "success");
    AppState.overview = res.overview;
    await refreshColumns();
    renderDashboard(res.overview);
    await loadCleaningTab();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

async function runAutoClean() {
  showLoading("Running one-click auto clean…");
  try {
    const res = await API.post("/api/cleaning/auto", {});
    showToast("Auto-clean complete.", "success");
    AppState.overview = res.overview;
    await refreshColumns();
    renderDashboard(res.overview);
    await loadCleaningTab();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

async function resetCleaning() {
  showLoading("Resetting to original dataset…");
  try {
    const res = await API.post("/api/cleaning/reset", {});
    showToast("Dataset reset to original upload.", "info");
    AppState.overview = res.overview;
    await refreshColumns();
    renderDashboard(res.overview);
    await loadCleaningTab();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}
