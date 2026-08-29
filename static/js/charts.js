/* ==========================================================================
   charts.js — Visualizations tab: dynamic form + Plotly chart rendering.
   ========================================================================== */

function populateColumnDropdowns() {
  const all = [
    ...AppState.columns.numeric,
    ...AppState.columns.categorical,
    ...AppState.columns.datetime,
    ...AppState.columns.boolean,
  ];
  const numeric = AppState.columns.numeric;

  fillSelect("xCol", all);
  fillSelect("yCol", numeric);
  fillSelect("colorCol", all, true);

  updateChartFormVisibility();
}

function fillSelect(id, options, includeNone = false) {
  const select = document.getElementById(id);
  const current = select.value;
  let html = includeNone ? `<option value="">None</option>` : "";
  html += options.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  select.innerHTML = html;
  if (options.includes(current)) select.value = current;
}

function updateChartFormVisibility() {
  const type = document.getElementById("chartType").value;
  const xGroup = document.getElementById("xColGroup");
  const yGroup = document.getElementById("yColGroup");
  const colorGroup = document.getElementById("colorColGroup");
  const aggGroup = document.getElementById("aggGroup");
  const xLabel = document.getElementById("xColLabel");

  // Reset visibility
  xGroup.style.display = "flex";
  yGroup.style.display = "flex";
  colorGroup.style.display = "flex";
  aggGroup.style.display = "flex";

  switch (type) {
    case "bar":
      xLabel.textContent = "Category Column";
      yGroup.style.display = "flex";
      colorGroup.style.display = "none";
      break;
    case "line":
      xLabel.textContent = "X Axis";
      colorGroup.style.display = "none";
      aggGroup.style.display = "none";
      break;
    case "pie":
      xLabel.textContent = "Category Column";
      yGroup.style.display = "none";
      colorGroup.style.display = "none";
      aggGroup.style.display = "none";
      break;
    case "histogram":
      xLabel.textContent = "Numeric Column";
      yGroup.style.display = "none";
      colorGroup.style.display = "none";
      aggGroup.style.display = "none";
      break;
    case "scatter":
      xLabel.textContent = "X Axis (numeric)";
      aggGroup.style.display = "none";
      break;
    case "heatmap":
      xGroup.style.display = "none";
      yGroup.style.display = "none";
      colorGroup.style.display = "none";
      aggGroup.style.display = "none";
      break;
  }
}

async function generateChart() {
  const type = document.getElementById("chartType").value;
  const x = document.getElementById("xCol").value;
  const y = document.getElementById("yCol").value;
  const color = document.getElementById("colorCol").value;
  const agg = document.getElementById("aggFn").value;

  const output = document.getElementById("chartOutput");
  output.innerHTML = `<div class="chart-placeholder">Generating chart…</div>`;

  try {
    const res = await API.post("/api/chart", { type, x, y, color, agg });
    output.innerHTML = "";
    const div = document.createElement("div");
    div.style.width = "100%";
    output.appendChild(div);
    Plotly.newPlot(div, res.figure.data, res.figure.layout, {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["lasso2d", "select2d"],
    });
  } catch (err) {
    output.innerHTML = `<div class="chart-placeholder text-danger">${escapeHtml(err.message)}</div>`;
    showToast(err.message, "error");
  }
}
