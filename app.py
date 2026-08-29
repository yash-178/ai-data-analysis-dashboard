"""
AI Data Analysis Dashboard
----------------------------
Flask backend serving a browser-based data analysis dashboard.
Upload any CSV/Excel dataset and get automatic cleaning, statistics,
interactive Plotly visualizations, rule-based AI insights, search &
filtering, and a downloadable PDF report - all through a REST API
consumed by the vanilla-JS frontend in templates/index.html.
"""

import os
import io
import traceback
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file, session

from services import data_store, cleaning, analytics, visualization, insights as insights_svc, filtering
from services.json_utils import df_to_records, to_jsonable
from services.report_generator import generate_pdf_report

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
app = Flask(__name__)

# NOTE: In production, set SECRET_KEY via an environment variable and never
# commit a real secret to source control. A random fallback is used here so
# the app works out-of-the-box for local/demo purposes.
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def error_response(message, status=400):
    return jsonify({"success": False, "error": message}), status


def require_dataset():
    """Returns the current DataFrame or None; caller should error_response if None."""
    return data_store.get_df()


# --------------------------------------------------------------------------
# Page route
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return error_response("No file part in the request. Please choose a file to upload.")

    file = request.files["file"]
    if file.filename == "":
        return error_response("No file selected.")

    if not allowed_file(file.filename):
        return error_response(
            "Unsupported file type. Please upload a .csv, .xlsx, or .xls file."
        )

    try:
        filename = file.filename
        ext = filename.rsplit(".", 1)[1].lower()

        if ext == "csv":
            # Try to gracefully handle common encoding issues
            try:
                df = pd.read_csv(file, low_memory=False)
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, low_memory=False, encoding="latin1")
        else:
            df = pd.read_excel(file)

        if df.empty or df.shape[1] == 0:
            return error_response("The uploaded file appears to be empty or has no columns.")

        # Normalize column names (strip whitespace) without altering data
        df.columns = [str(c).strip() for c in df.columns]

        data_store.save_dataset(df, filename)

        overview = analytics.compute_overview(df, filename)
        return jsonify({"success": True, "message": f"'{filename}' uploaded successfully.",
                        "overview": overview})

    except pd.errors.EmptyDataError:
        return error_response("The uploaded CSV file is empty.")
    except pd.errors.ParserError as e:
        return error_response(f"Could not parse the file. It may be corrupted or malformed: {e}")
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to process the file: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
@app.route("/api/overview", methods=["GET"])
def get_overview():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        overview = analytics.compute_overview(df, data_store.get_filename())
        return jsonify({"success": True, "overview": overview})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to compute overview: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------
@app.route("/api/cleaning/summary", methods=["GET"])
def cleaning_summary():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        summary = cleaning.get_cleaning_summary(df)
        return jsonify({"success": True, "summary": to_jsonable(summary),
                        "log": data_store.get_cleaning_log()})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to analyze data quality: {str(e)}", status=500)


@app.route("/api/cleaning/apply", methods=["POST"])
def apply_cleaning():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        options = request.get_json(force=True, silent=True) or {}
        cleaned_df, log = cleaning.apply_cleaning(df, options)
        data_store.update_df(cleaned_df)
        data_store.add_cleaning_log(log)
        overview = analytics.compute_overview(cleaned_df, data_store.get_filename())
        return jsonify({"success": True, "log": log, "overview": overview})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to apply cleaning: {str(e)}", status=500)


@app.route("/api/cleaning/auto", methods=["POST"])
def auto_clean():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        cleaned_df, log = cleaning.auto_clean(df)
        data_store.update_df(cleaned_df)
        data_store.add_cleaning_log(log)
        overview = analytics.compute_overview(cleaned_df, data_store.get_filename())
        return jsonify({"success": True, "log": log, "overview": overview})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Auto-clean failed: {str(e)}", status=500)


@app.route("/api/cleaning/reset", methods=["POST"])
def reset_cleaning():
    if not data_store.has_dataset():
        return error_response("No dataset uploaded yet.", status=404)
    try:
        data_store.reset_to_original()
        df = require_dataset()
        overview = analytics.compute_overview(df, data_store.get_filename())
        return jsonify({"success": True, "message": "Dataset reset to original upload.",
                        "overview": overview})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to reset dataset: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Columns (for populating chart/filter dropdowns)
# --------------------------------------------------------------------------
@app.route("/api/columns", methods=["GET"])
def get_columns():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    types = cleaning.detect_column_types(df)
    return jsonify({"success": True, "columns": types, "all": list(df.columns)})


# --------------------------------------------------------------------------
# Visualizations
# --------------------------------------------------------------------------
@app.route("/api/chart", methods=["POST"])
def get_chart():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        payload = request.get_json(force=True, silent=True) or {}
        chart_type = payload.get("type")
        x = payload.get("x")
        y = payload.get("y")
        color = payload.get("color")
        agg = payload.get("agg", "mean")

        fig_payload = visualization.build_chart(df, chart_type, x=x, y=y, color=color, agg=agg)
        return jsonify({"success": True, "figure": fig_payload})
    except visualization.ChartError as e:
        return error_response(str(e))
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to generate chart: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------
@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        result = analytics.compute_analytics(df)
        return jsonify({"success": True, "analytics": result})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to compute analytics: {str(e)}", status=500)


# --------------------------------------------------------------------------
# AI Insights
# --------------------------------------------------------------------------
@app.route("/api/insights", methods=["GET"])
def get_insights():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        result = insights_svc.generate_insights(df)
        return jsonify({"success": True, "insights": result})
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to generate insights: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Search & Filter
# --------------------------------------------------------------------------
@app.route("/api/search", methods=["POST"])
def search_data():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        payload = request.get_json(force=True, silent=True) or {}
        query = payload.get("query", "")
        columns = payload.get("columns")  # optional list
        result_df = filtering.search_dataset(df, query, columns)
        return jsonify({
            "success": True,
            "count": len(result_df),
            "total": len(df),
            "preview": df_to_records(result_df, limit=100),
        })
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Search failed: {str(e)}", status=500)


@app.route("/api/filter", methods=["POST"])
def filter_data():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        payload = request.get_json(force=True, silent=True) or {}
        column = payload.get("column")
        operator = payload.get("operator")
        value = payload.get("value")
        result_df = filtering.filter_dataset(df, column, operator, value)
        return jsonify({
            "success": True,
            "count": len(result_df),
            "total": len(df),
            "preview": df_to_records(result_df, limit=100),
        })
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Filter failed: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Report generation
# --------------------------------------------------------------------------
@app.route("/api/report", methods=["GET"])
def download_report():
    df = require_dataset()
    if df is None:
        return error_response("No dataset uploaded yet.", status=404)
    try:
        filename = data_store.get_filename()
        overview = analytics.compute_overview(df, filename)
        cleaning_log = data_store.get_cleaning_log()
        analytics_data = analytics.compute_analytics(df)
        insights_data = insights_svc.generate_insights(df)

        pdf_bytes = generate_pdf_report(filename, overview, cleaning_log, analytics_data, insights_data)

        out_name = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=out_name,
        )
    except Exception as e:
        traceback.print_exc()
        return error_response(f"Failed to generate report: {str(e)}", status=500)


# --------------------------------------------------------------------------
# Session / dataset management
# --------------------------------------------------------------------------
@app.route("/api/clear", methods=["POST"])
def clear_data():
    data_store.clear_dataset()
    return jsonify({"success": True, "message": "Dataset cleared."})


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"success": True, "has_dataset": data_store.has_dataset(),
                    "filename": data_store.get_filename()})


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(413)
def too_large(e):
    return error_response("File too large. Maximum upload size is 25 MB.", status=413)


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return error_response("Endpoint not found.", status=404)
    return render_template("index.html")


@app.errorhandler(500)
def server_error(e):
    return error_response("An unexpected server error occurred.", status=500)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
