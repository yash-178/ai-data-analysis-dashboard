/* ==========================================================================
   insights.js — AI Insights tab: renders rule-based insight cards.
   ========================================================================== */

const SEVERITY_STYLE = {
  positive: { accent: "var(--success)", soft: "var(--success-soft)" },
  warning: { accent: "var(--warning)", soft: "var(--warning-soft)" },
  critical: { accent: "var(--critical)", soft: "var(--critical-soft)" },
  info: { accent: "var(--indigo)", soft: "var(--indigo-soft)" },
};

const ICON_PATHS = {
  "alert-triangle": '<path d="M12 3l9.5 17H2.5L12 3z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 10v4M12 17h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  "check-circle": '<path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  "copy": '<rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1" stroke="currentColor" stroke-width="1.8"/>',
  "trending-up": '<path d="M3 17l6-6 4 4 8-8M21 7v6M21 7h-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  "trending-down": '<path d="M3 7l6 6 4-4 8 8M21 17v-6M21 17h-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  "bar-chart-2": '<path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  "link": '<path d="M9 17H7A5 5 0 017 7h2M15 7h2a5 5 0 010 10h-2M8 12h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  "arrow-up-down": '<path d="M8 3L4 7l4 4M4 7h13M16 21l4-4-4-4M20 17H7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  "pie-chart": '<path d="M21.2 15a9 9 0 11-9.9-14.9M12.4 2.1V12h9.5" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
  "hash": '<path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  "clipboard-list": '<rect x="6" y="4" width="12" height="17" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M9 2h6v3H9zM9 10h6M9 14h6M9 18h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  "lightbulb": '<path d="M9 18h6M10 22h4M12 2a6 6 0 00-3.5 10.9c.6.45.95 1.16.95 1.9V15h5.1v-.2c0-.74.35-1.45.95-1.9A6 6 0 0012 2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
};

async function loadInsightsTab() {
  if (!AppState.hasDataset) return;
  const grid = document.getElementById("insightsGrid");
  grid.innerHTML = `<div class="chart-placeholder">Analyzing dataset…</div>`;
  try {
    const res = await API.get("/api/insights");
    renderInsights(res.insights);
  } catch (err) {
    showToast(err.message, "error");
    grid.innerHTML = `<div class="chart-placeholder text-danger">${escapeHtml(err.message)}</div>`;
  }
}

function renderInsights(insights) {
  const grid = document.getElementById("insightsGrid");
  if (!insights || insights.length === 0) {
    grid.innerHTML = `<div class="chart-placeholder">No insights could be generated for this dataset.</div>`;
    return;
  }
  grid.innerHTML = insights
    .map((ins) => {
      const style = SEVERITY_STYLE[ins.severity] || SEVERITY_STYLE.info;
      const iconSvg = ICON_PATHS[ins.icon] || ICON_PATHS["lightbulb"];
      return `
        <div class="insight-card" style="--card-accent:${style.accent}; --card-accent-soft:${style.soft}">
          <div class="insight-card-header">
            <div class="insight-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none">${iconSvg}</svg></div>
            <h4>${escapeHtml(ins.title)}</h4>
          </div>
          <p>${escapeHtml(ins.description)}</p>
          <span class="insight-tag">${escapeHtml((ins.category || "").replace("_", " "))}</span>
        </div>`;
    })
    .join("");
}
