"""
insights.py
------------
Generates "AI Insights": human-readable, data-driven observations using
deterministic statistical/rule-based logic (no external LLM calls).
Each insight has a type/severity so the frontend can style it
consistently (e.g. warning vs positive vs neutral).
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .cleaning import detect_column_types
from .analytics import _iqr_outlier_count
from .json_utils import to_jsonable


def _insight(category, title, description, severity="info", icon="lightbulb"):
    return {
        "category": category,
        "title": title,
        "description": description,
        "severity": severity,  # info | positive | warning | critical
        "icon": icon,
    }


def generate_insights(df: pd.DataFrame) -> list:
    insights = []
    types = detect_column_types(df)
    numeric_cols = types["numeric"]
    categorical_cols = types["categorical"]
    datetime_cols = types["datetime"]
    total_rows = len(df)

    if total_rows == 0:
        return [_insight("data_quality", "Empty dataset",
                          "The uploaded dataset has no rows to analyze.", "critical", "alert")]

    # ---------- Data quality: missing values ----------
    missing_pct = (df.isna().sum() / total_rows * 100).sort_values(ascending=False)
    worst_missing = missing_pct[missing_pct > 0].head(3)
    if not worst_missing.empty:
        cols_desc = ", ".join(f"'{c}' ({v:.1f}%)" for c, v in worst_missing.items())
        severity = "critical" if worst_missing.iloc[0] > 40 else "warning"
        insights.append(_insight(
            "data_quality", "Missing data detected",
            f"The columns with the most missing values are {cols_desc}. "
            f"Consider imputing or dropping these before modeling.",
            severity, "alert-triangle",
        ))
    else:
        insights.append(_insight(
            "data_quality", "No missing values",
            "The dataset has no missing values across any column - great data quality.",
            "positive", "check-circle",
        ))

    # ---------- Duplicates ----------
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        insights.append(_insight(
            "data_quality", "Duplicate rows found",
            f"Found {dup_count} duplicate row(s) ({dup_count / total_rows * 100:.1f}% of the data). "
            f"Removing duplicates can prevent skewed statistics and biased models.",
            "warning", "copy",
        ))

    # ---------- Outliers ----------
    outlier_findings = []
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        n_out = _iqr_outlier_count(s)
        if n_out > 0:
            outlier_findings.append((col, n_out, n_out / len(s) * 100))
    outlier_findings.sort(key=lambda t: t[1], reverse=True)
    if outlier_findings:
        top = outlier_findings[:3]
        desc = "; ".join(f"'{c}' has {n} outlier(s) ({p:.1f}%)" for c, n, p in top)
        insights.append(_insight(
            "outliers", "Outliers detected",
            f"Using the IQR method, {desc}. Investigate whether these are data errors "
            f"or genuine extreme values before drawing conclusions.",
            "warning", "trending-up",
        ))

    # ---------- Skewed distributions ----------
    skewed = []
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) > 2:
            sk = s.skew()
            if abs(sk) > 1:
                skewed.append((col, sk))
    if skewed:
        skewed.sort(key=lambda t: abs(t[1]), reverse=True)
        c, sk = skewed[0]
        direction = "right (positively)" if sk > 0 else "left (negatively)"
        insights.append(_insight(
            "distribution", f"Skewed distribution in '{c}'",
            f"'{c}' is skewed {direction} (skewness = {sk:.2f}). "
            f"A log transform or robust scaling may help if this feeds a model.",
            "info", "bar-chart-2",
        ))

    # ---------- Strong correlations ----------
    strong_pairs = []
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr(numeric_only=True)
        seen = set()
        for c1 in corr.columns:
            for c2 in corr.columns:
                if c1 == c2:
                    continue
                pair = tuple(sorted([c1, c2]))
                if pair in seen:
                    continue
                seen.add(pair)
                val = corr.loc[c1, c2]
                if pd.notna(val) and abs(val) >= 0.7:
                    strong_pairs.append((c1, c2, val))
        strong_pairs.sort(key=lambda t: abs(t[2]), reverse=True)
        if strong_pairs:
            c1, c2, val = strong_pairs[0]
            rel = "positively" if val > 0 else "negatively"
            insights.append(_insight(
                "correlation", f"Strong correlation between '{c1}' and '{c2}'",
                f"'{c1}' and '{c2}' are strongly {rel} correlated (r = {val:.2f}). "
                f"This suggests they move together and one may be predictive of the other.",
                "positive", "link",
            ))
        else:
            insights.append(_insight(
                "correlation", "No strong correlations found",
                "No pair of numeric columns showed a strong linear relationship "
                "(|r| >= 0.7). Features appear relatively independent.",
                "info", "link",
            ))

    # ---------- Highest / lowest values ----------
    for col in numeric_cols[:5]:
        s = df[col].dropna()
        if s.empty:
            continue
        insights.append(_insight(
            "extremes", f"Range of '{col}'",
            f"'{col}' ranges from {s.min():,.2f} (min) to {s.max():,.2f} (max), "
            f"with an average of {s.mean():,.2f}.",
            "info", "arrow-up-down",
        ))
        break  # keep the panel focused - just the primary numeric column

    # ---------- Dominant category ----------
    for col in categorical_cols:
        vc = df[col].value_counts(normalize=True)
        if not vc.empty and vc.iloc[0] > 0.5:
            insights.append(_insight(
                "patterns", f"'{col}' is dominated by one category",
                f"'{vc.index[0]}' accounts for {vc.iloc[0] * 100:.1f}% of all values in '{col}'. "
                f"This class imbalance may bias aggregate statistics or models.",
                "warning", "pie-chart",
            ))
            break

    # ---------- Trend over time ----------
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        temp = df[[date_col] + numeric_cols].dropna(subset=[date_col]).sort_values(date_col)
        if len(temp) >= 3:
            target = numeric_cols[0]
            y = temp[target].values.astype(float)
            x = np.arange(len(temp)).reshape(-1, 1)
            mask = ~np.isnan(y)
            if mask.sum() >= 3:
                model = LinearRegression()
                model.fit(x[mask], y[mask])
                slope = float(model.coef_[0])
                if abs(slope) > 1e-9:
                    direction = "an upward" if slope > 0 else "a downward"
                    insights.append(_insight(
                        "trends", f"Trend detected in '{target}'",
                        f"'{target}' shows {direction} trend over '{date_col}' "
                        f"(approx. {slope:+.3f} per record). Consider this when forecasting.",
                        "info", "trending-up" if slope > 0 else "trending-down",
                    ))

    # ---------- High cardinality warning ----------
    for col in categorical_cols:
        nunique = df[col].nunique()
        if nunique > 0 and nunique / total_rows > 0.9 and total_rows > 20:
            insights.append(_insight(
                "data_quality", f"'{col}' looks like an identifier",
                f"'{col}' has {nunique} unique values across {total_rows} rows - "
                f"it may be an ID field rather than a useful categorical feature for analysis.",
                "info", "hash",
            ))
            break

    # ---------- Business recommendations (templated) ----------
    recommendations = []
    if dup_count > 0:
        recommendations.append("Remove duplicate rows before running further analysis or modeling.")
    if not worst_missing.empty:
        recommendations.append("Address missing values via imputation or targeted collection before relying on affected columns.")
    if outlier_findings:
        recommendations.append(f"Review outliers in '{outlier_findings[0][0]}' - they may represent errors or high-value edge cases worth investigating separately.")
    if strong_pairs:
        recommendations.append(f"Since '{strong_pairs[0][0]}' and '{strong_pairs[0][1]}' are highly correlated, consider using only one in a predictive model to avoid multicollinearity.")
    if not recommendations:
        recommendations.append("The dataset looks reasonably clean - proceed to modeling or deeper segmentation analysis.")

    insights.append(_insight(
        "recommendations", "Recommended next steps",
        " ".join(recommendations),
        "positive", "clipboard-list",
    ))

    return to_jsonable(insights)
