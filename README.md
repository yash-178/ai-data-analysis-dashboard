# AI Data Analysis Dashboard

A full-stack, browser-based data analysis dashboard built with **Flask, Pandas, NumPy, Scikit-learn, and Plotly**. Upload any CSV or Excel dataset and instantly get automated data cleaning, statistical summaries, interactive visualizations, rule-based AI insights, search/filtering, and a downloadable PDF report.

Built as a portfolio project for a Data Science internship — works with **any** tabular dataset, not hard-coded for a specific file.

![Tech](https://img.shields.io/badge/backend-Flask-000000) ![Tech](https://img.shields.io/badge/analysis-Pandas%20%2B%20NumPy-150458) ![Tech](https://img.shields.io/badge/viz-Plotly-3F4F75) ![Tech](https://img.shields.io/badge/ml-Scikit--learn-F7931E)

---

## ✨ Features

| Section | What it does |
|---|---|
| **Dashboard** | KPI cards (rows, columns, missing cells, duplicates), column data types, missing-value breakdown, dataset preview |
| **Dataset** | Full numeric & categorical statistical summary, free-text search across all columns, structured single-column filtering (equals, contains, greater than, etc.) |
| **Data Cleaning** | Detects missing values, duplicates, and column types; configurable cleaning (drop duplicates, fill missing via mean/median/mode/zero, drop rows/columns, trim whitespace, standardize case, auto-detect dates); one-click **Auto Clean**; **Reset to Original**; full cleaning action log |
| **Visualizations** | Interactive Plotly charts: bar, line, pie, histogram, scatter, and correlation heatmap — all driven by user-selected columns |
| **AI Insights** | Rule-based, statistically-grounded observations: missing-data risk, outliers (IQR method), skewed distributions, strong correlations, dominant categories, trends over time, and templated recommendations |
| **Report** | One-click downloadable **PDF report** with dataset summary, data-quality findings, key statistics, correlations, and the full AI insights panel |

The app works with **any** CSV/Excel dataset — column types, charts, and insights all adapt automatically to whatever you upload.

---

## 🏗️ Project Structure

```
ai-data-analysis-dashboard/
├── app.py                    # Flask app & all REST API routes
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   └── index.html            # Single-page dashboard UI
├── static/
│   ├── css/style.css         # Design system / styling
│   └── js/
│       ├── api.js            # fetch wrapper + shared UI helpers (toasts, tables)
│       ├── app.js            # navigation & event wiring
│       ├── dataset.js         # upload, dashboard & dataset tab rendering
│       ├── cleaning.js       # data cleaning tab logic
│       ├── charts.js         # visualization builder + Plotly rendering
│       ├── insights.js       # AI insights rendering
│       └── report.js         # PDF report download
├── services/                  # Modular backend logic (imported by app.py)
│   ├── data_store.py          # session-based in-memory dataset storage
│   ├── cleaning.py            # missing/duplicate detection + cleaning ops
│   ├── analytics.py           # overview & analytics computations
│   ├── visualization.py       # Plotly figure builder
│   ├── insights.py            # rule-based AI insight generation
│   ├── filtering.py           # search & filter logic
│   ├── report_generator.py    # PDF report builder (ReportLab)
│   └── json_utils.py          # NumPy/Pandas → JSON-safe conversion helpers
└── uploads/                    # (empty — reserved for future disk-based storage)
```


### 5. Use it
1. Click **Upload Dataset** and choose a `.csv`, `.xlsx`, or `.xls` file.
2. Explore the **Dashboard** for an instant overview.
3. Visit **Data Cleaning** to inspect and fix data quality issues (or hit **One-Click Auto Clean**).
4. Build charts in **Visualizations**.
5. Review automatically generated findings in **AI Insights**.
6. Download a shareable **PDF report** from the **Report** tab.

---

## 🔌 API Overview

All endpoints are prefixed with `/api` and return JSON (`{"success": true/false, ...}`), except `/api/report` which streams a PDF file.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/upload` | Upload a CSV/Excel file |
| GET | `/api/overview` | Dataset shape, dtypes, missing values, stats, preview |
| GET | `/api/columns` | Column names grouped by type (numeric/categorical/datetime/boolean) |
| GET | `/api/cleaning/summary` | Data-quality diagnostics |
| POST | `/api/cleaning/apply` | Apply selected cleaning operations |
| POST | `/api/cleaning/auto` | One-click sensible-defaults cleaning |
| POST | `/api/cleaning/reset` | Revert to the originally uploaded data |
| POST | `/api/chart` | Generate a Plotly figure (`type`, `x`, `y`, `color`, `agg`) |
| GET | `/api/analytics` | Automatic metrics: top categories, correlations, trends, distributions |
| GET | `/api/insights` | Rule-based AI insights |
| POST | `/api/search` | Free-text search across the dataset |
| POST | `/api/filter` | Structured single-column filter |
| GET | `/api/report` | Download the PDF analysis report |
| POST | `/api/clear` | Clear the current session's dataset |
| GET | `/api/status` | Whether a dataset is currently loaded |

Data is stored **server-side, in memory, per browser session** (via a signed session cookie) — no database required for this demo. Restarting the Flask process clears all uploaded data, which is intentional for a lightweight local/demo deployment.

---

## 🧪 Tested With

The app was verified end-to-end using several sample datasets during development, including:
- A realistic sales dataset (mixed numeric/categorical/datetime, missing values, duplicates, outliers)
- An all-categorical dataset
- A dataset with a fully-empty column and a boolean column
- Both `.csv` and `.xlsx` formats

Error handling was verified for: unsupported file types, empty files, corrupted files, missing/invalid chart columns, and requests made with no dataset uploaded.

---

## ⚙️ Configuration Notes

- **Max upload size**: 25 MB (configurable via `MAX_CONTENT_LENGTH` in `app.py`).
- **Secret key**: Set the `SECRET_KEY` environment variable in production (`app.py` falls back to a random key per process start, which is fine for local/demo use but means sessions won't persist across restarts).
- **No API keys or secrets** are required or exposed — AI Insights use deterministic statistical/rule-based logic, not an external LLM API.

To run in production, use a proper WSGI server instead of Flask's built-in dev server, e.g.:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Data processing**: Pandas, NumPy
- **Statistics/ML**: Scikit-learn (used for feature scaling utilities/consistency where applicable), NumPy `polyfit` for trend detection, IQR method for outlier detection
- **Visualization**: Plotly (rendered client-side via Plotly.js from a CDN)
- **PDF generation**: ReportLab
- **Frontend**: HTML5, CSS3 (custom design system, no framework), vanilla JavaScript (modular, no build step)

---

## 📄 License

This project is provided as-is for portfolio/educational use.
