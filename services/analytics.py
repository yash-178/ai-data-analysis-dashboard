"""
analytics.py
-------------
Computes the "Dataset Overview" payload and the automatic Analytics
metrics (top categories, min/max/avg, trends, distributions,
correlations, comparisons) shown on the dashboard.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .cleaning import detect_column_types, detect_missing, detect_duplicates
from .json_utils import to_jsonable, df_to_records


def compute_overview(df: pd.DataFrame, filename: str = None) -> dict:
    types = detect_column_types(df)
    missing = detect_missing(df)

    dtypes = [{"column": c, "dtype": str(df[c].dtype)} for c in df.columns]

    # Statistical summary (numeric describe + categorical describe)
    stats = {}
    if types["numeric"]:
        desc = df[types["numeric"]].describe().transpose()
        desc = desc.reset_index().rename(columns={"index": "column"})
        stats["numeric"] = to_jsonable(desc.to_dict(orient="records"))
    else:
        stats["numeric"] = []

    if types["categorical"]:
        cat_stats = []
        for col in types["categorical"]:
            vc = df[col].value_counts()
            cat_stats.append({
                "column": col,
                "unique": int(df[col].nunique()),
                "top": str(vc.index[0]) if len(vc) else None,
                "freq": int(vc.iloc[0]) if len(vc) else 0,
            })
        stats["categorical"] = to_jsonable(cat_stats)
    else:
        stats["categorical"] = []

    return {
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_types": types,
        "dtypes": dtypes,
        "missing": missing,
        "duplicates": detect_duplicates(df),
        "stats": stats,
        "preview": df_to_records(df, limit=10),
    }


def _iqr_outlier_count(series: pd.Series) -> int:
    s = series.dropna()
    if len(s) < 4:
        return 0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((s < lower) | (s > upper)).sum())


def compute_analytics(df: pd.DataFrame) -> dict:
    """Automatically computed metrics used across Analytics + Insights."""
    types = detect_column_types(df)
    numeric_cols = types["numeric"]
    categorical_cols = types["categorical"]
    datetime_cols = types["datetime"]

    result = {
        "numeric_summary": [],
        "top_categories": [],
        "correlations": {"columns": [], "matrix": []},
        "strong_correlations": [],
        "trends": [],
        "distributions": [],
        "comparisons": [],
    }

    # --- Numeric summary: min/max/mean/median/std + outliers ---
    for col in numeric_cols:
        s = df[col].dropna()
        if s.empty:
            continue
        result["numeric_summary"].append({
            "column": col,
            "min": float(s.min()),
            "max": float(s.max()),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()) if len(s) > 1 else 0.0,
            "outliers": _iqr_outlier_count(s),
            "skew": float(s.skew()) if len(s) > 2 else 0.0,
        })

    # --- Top categories per categorical column ---
    for col in categorical_cols:
        vc = df[col].value_counts().head(5)
        total = df[col].notna().sum()
        result["top_categories"].append({
            "column": col,
            "items": [
                {
                    "value": str(idx),
                    "count": int(cnt),
                    "pct": round((cnt / total) * 100, 2) if total else 0.0,
                }
                for idx, cnt in vc.items()
            ],
        })

    # --- Correlation matrix + strong pairs ---
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr(numeric_only=True).round(3)
        result["correlations"] = {
            "columns": list(corr.columns),
            "matrix": to_jsonable(corr.values.tolist()),
        }
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
                    result["strong_correlations"].append({
                        "column_a": c1,
                        "column_b": c2,
                        "correlation": round(float(val), 3),
                        "strength": "strong positive" if val > 0 else "strong negative",
                    })
        result["strong_correlations"].sort(key=lambda r: abs(r["correlation"]), reverse=True)

    # --- Trends: if a datetime column exists, compute slope of numeric cols over time ---
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        temp = df[[date_col] + numeric_cols].dropna(subset=[date_col]).sort_values(date_col)
        if len(temp) >= 3:
            x = np.arange(len(temp)).reshape(-1, 1)
            for col in numeric_cols:
                y = temp[col].values.astype(float)
                mask = ~np.isnan(y)
                if mask.sum() < 3:
                    continue
                # Use scikit-learn's LinearRegression to fit a simple trend line
                # (slope = rate of change per record) over the time-ordered data.
                model = LinearRegression()
                model.fit(x[mask], y[mask])
                slope = float(model.coef_[0])
                r_squared = float(model.score(x[mask], y[mask]))
                direction = "increasing" if slope > 0 else ("decreasing" if slope < 0 else "flat")
                result["trends"].append({
                    "column": col,
                    "over": date_col,
                    "direction": direction,
                    "slope": slope,
                    "r_squared": round(r_squared, 3),
                })

    # --- Distributions (histogram bin counts) for numeric columns ---
    for col in numeric_cols[:8]:  # cap to keep payload light
        s = df[col].dropna()
        if s.empty:
            continue
        counts, bin_edges = np.histogram(s, bins=10)
        result["distributions"].append({
            "column": col,
            "counts": counts.tolist(),
            "bin_edges": [round(float(b), 3) for b in bin_edges],
        })

    # --- Comparisons: mean of numeric columns grouped by top categorical column ---
    if categorical_cols and numeric_cols:
        group_col = categorical_cols[0]
        target_col = numeric_cols[0]
        if df[group_col].nunique() <= 20:
            grouped = df.groupby(group_col)[target_col].mean().sort_values(ascending=False).head(10)
            result["comparisons"].append({
                "group_by": group_col,
                "metric": target_col,
                "aggregation": "mean",
                "items": [
                    {"category": str(idx), "value": round(float(val), 3)}
                    for idx, val in grouped.items()
                ],
            })

    return to_jsonable(result)
