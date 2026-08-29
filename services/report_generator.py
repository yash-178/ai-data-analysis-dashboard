"""
report_generator.py
---------------------
Builds a downloadable, professionally formatted PDF report summarizing
the dataset, data-quality findings, key statistics, and AI insights.
Uses ReportLab (pure Python, no external binary dependencies).
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT

PRIMARY = colors.HexColor("#4f46e5")
DARK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
LIGHT_BG = colors.HexColor("#f3f4f6")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleBig", fontSize=22, leading=26, textColor=PRIMARY,
                               spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Subtitle", fontSize=11, textColor=MUTED, spaceAfter=20))
    styles.add(ParagraphStyle(name="Section", fontSize=15, leading=18, textColor=DARK,
                               spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=10, leading=15, textColor=DARK, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="InsightTitle", fontSize=10.5, leading=14, textColor=PRIMARY,
                               fontName="Helvetica-Bold", spaceBefore=8))
    return styles


def generate_pdf_report(filename, overview, cleaning_log, analytics, insights) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = _styles()
    story = []

    # --- Title ---
    story.append(Paragraph("AI Data Analysis Report", styles["TitleBig"]))
    story.append(Paragraph(
        f"Dataset: <b>{filename or 'Uploaded dataset'}</b> &nbsp;|&nbsp; "
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        styles["Subtitle"],
    ))
    story.append(HRFlowable(width="100%", color=LIGHT_BG, thickness=1))

    # --- Dataset Summary ---
    story.append(Paragraph("1. Dataset Summary", styles["Section"]))
    summary_data = [
        ["Metric", "Value"],
        ["Total Rows", f"{overview['rows']:,}"],
        ["Total Columns", f"{overview['columns']:,}"],
        ["Numeric Columns", str(len(overview["column_types"]["numeric"]))],
        ["Categorical Columns", str(len(overview["column_types"]["categorical"]))],
        ["Datetime Columns", str(len(overview["column_types"]["datetime"]))],
        ["Duplicate Rows", str(overview["duplicates"]["duplicate_rows"])],
    ]
    story.append(_styled_table(summary_data, col_widths=[2.5 * inch, 3.5 * inch]))

    # --- Data Quality ---
    story.append(Paragraph("2. Data Quality", styles["Section"]))
    missing = [m for m in overview["missing"] if m["missing_count"] > 0][:10]
    if missing:
        dq_data = [["Column", "Missing Count", "Missing %"]]
        for m in missing:
            dq_data.append([m["column"], str(m["missing_count"]), f"{m['missing_pct']}%"])
        story.append(_styled_table(dq_data, col_widths=[2.8 * inch, 1.8 * inch, 1.4 * inch]))
    else:
        story.append(Paragraph("No missing values detected in this dataset.", styles["Body"]))

    if cleaning_log:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Cleaning actions applied:</b>", styles["Body"]))
        for entry in cleaning_log:
            story.append(Paragraph(f"&bull; {entry}", styles["Body"]))

    # --- Key Statistics ---
    story.append(Paragraph("3. Key Statistics", styles["Section"]))
    num_summary = analytics.get("numeric_summary", [])
    if num_summary:
        stat_data = [["Column", "Min", "Max", "Mean", "Median", "Outliers"]]
        for row in num_summary[:12]:
            stat_data.append([
                row["column"], f"{row['min']:.2f}", f"{row['max']:.2f}",
                f"{row['mean']:.2f}", f"{row['median']:.2f}", str(row["outliers"]),
            ])
        story.append(_styled_table(stat_data, col_widths=[1.7 * inch, 0.85 * inch, 0.85 * inch,
                                                            0.9 * inch, 0.9 * inch, 0.8 * inch]))
    else:
        story.append(Paragraph("No numeric columns available for statistical summary.", styles["Body"]))

    strong_corr = analytics.get("strong_correlations", [])
    if strong_corr:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Strong correlations (|r| ≥ 0.7):</b>", styles["Body"]))
        for c in strong_corr[:8]:
            story.append(Paragraph(
                f"&bull; {c['column_a']} &harr; {c['column_b']}: r = {c['correlation']} ({c['strength']})",
                styles["Body"],
            ))

    # --- AI Insights ---
    story.append(PageBreak())
    story.append(Paragraph("4. AI-Generated Insights", styles["Section"]))
    for ins in insights:
        story.append(Paragraph(f"{ins['title']}", styles["InsightTitle"]))
        story.append(Paragraph(ins["description"], styles["Body"]))
        story.append(Spacer(1, 4))

    # --- Footer note ---
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=LIGHT_BG, thickness=1))
    story.append(Paragraph(
        "Generated automatically by AI Data Analysis Dashboard using rule-based statistical analysis.",
        styles["Subtitle"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _styled_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table
