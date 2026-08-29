/* ==========================================================================
   app.js — navigation between sections, event wiring, initial bootstrap.
   ========================================================================== */

const SECTION_META = {
  dashboard: { title: "Dashboard", subtitle: "Overview of your uploaded dataset" },
  dataset: { title: "Dataset", subtitle: "Statistics, search, and filtering" },
  cleaning: { title: "Data Cleaning", subtitle: "Detect and fix data quality issues" },
  visualizations: { title: "Visualizations", subtitle: "Build interactive charts from your data" },
  insights: { title: "AI Insights", subtitle: "Automatically generated, data-driven observations" },
  report: { title: "Report", subtitle: "Download a professional analysis report" },
};

function switchSection(section) {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === section);
  });
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.toggle("active", page.id === `page-${section}`);
  });
  const meta = SECTION_META[section];
  document.getElementById("pageTitle").textContent = meta.title;
  document.getElementById("pageSubtitle").textContent = meta.subtitle;

  // Lazy-load section data when navigated to
  if (!AppState.hasDataset) return;
  if (section === "dataset") loadDatasetTab();
  if (section === "cleaning") loadCleaningTab();
  if (section === "insights") loadInsightsTab();
  if (section === "visualizations") populateColumnDropdowns();
}

function onDatasetLoaded() {
  // Refresh whichever tab is currently visible
  const activeBtn = document.querySelector(".nav-item.active");
  if (!activeBtn) return;
  const section = activeBtn.dataset.section;
  if (section === "dataset") loadDatasetTab();
  if (section === "cleaning") loadCleaningTab();
  if (section === "insights") loadInsightsTab();
  if (section === "visualizations") populateColumnDropdowns();
}

function wireEvents() {
  // Navigation
  document.getElementById("nav").addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-item");
    if (btn) switchSection(btn.dataset.section);
  });

  // File upload (both topbar and empty-state buttons point to #fileInput)
  document.getElementById("fileInput").addEventListener("change", (e) => {
    const file = e.target.files[0];
    handleFileUpload(file);
    e.target.value = ""; // allow re-uploading the same filename
  });

  // Dataset tab: search & filter
  let searchDebounce;
  document.getElementById("searchInput").addEventListener("input", (e) => {
    clearTimeout(searchDebounce);
    const value = e.target.value;
    searchDebounce = setTimeout(() => {
      if (value.trim()) runSearch(value.trim());
      else clearFilter();
    }, 350);
  });
  document.getElementById("applyFilterBtn").addEventListener("click", runFilter);
  document.getElementById("clearFilterBtn").addEventListener("click", clearFilter);

  // Cleaning tab
  document.getElementById("optMissingStrategy").addEventListener("change", (e) => {
    document.getElementById("thresholdRow").style.display = e.target.value === "drop_columns" ? "flex" : "none";
  });
  document.getElementById("applyCleaningBtn").addEventListener("click", applySelectedCleaning);
  document.getElementById("autoCleanBtn").addEventListener("click", runAutoClean);
  document.getElementById("resetCleaningBtn").addEventListener("click", resetCleaning);

  // Visualizations tab
  document.getElementById("chartType").addEventListener("change", updateChartFormVisibility);
  document.getElementById("generateChartBtn").addEventListener("click", generateChart);

  // Insights tab
  document.getElementById("refreshInsightsBtn").addEventListener("click", loadInsightsTab);

  // Report tab
  document.getElementById("downloadReportBtn").addEventListener("click", downloadReport);
}

async function bootstrap() {
  wireEvents();
  // Check if a dataset already exists in this session (e.g. page refresh)
  try {
    const res = await API.get("/api/status");
    if (res.has_dataset) {
      AppState.hasDataset = true;
      AppState.filename = res.filename;
      updateSidebarChip();
      unlockAllSections();
      const overviewRes = await API.get("/api/overview");
      AppState.overview = overviewRes.overview;
      renderDashboard(overviewRes.overview);
      await refreshColumns();
    }
  } catch (err) {
    // No dataset yet — this is expected on first load
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
