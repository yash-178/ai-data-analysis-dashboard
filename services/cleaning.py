"""
cleaning.py
------------
Detection and application of data-cleaning / preprocessing operations.
Works generically on any DataFrame - nothing here is dataset-specific.
"""

import numpy as np
import pandas as pd


def detect_column_types(df: pd.DataFrame) -> dict:
    """Classify each column as numeric, categorical, or datetime."""
    numeric_cols, categorical_cols, datetime_cols, boolean_cols = [], [], [], []

    for col in df.columns:
        series = df[col]
        if pd.api.types.is_bool_dtype(series):
            boolean_cols.append(col)
        elif pd.api.types.is_datetime64_any_dtype(series):
            datetime_cols.append(col)
        elif pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
        else:
            # Try to see if an object column is secretly a date column
            if _looks_like_datetime(series):
                datetime_cols.append(col)
            else:
                categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
        "boolean": boolean_cols,
    }


def _looks_like_datetime(series: pd.Series, sample_size: int = 25) -> bool:
    """Heuristic: sample some non-null values and see if pandas can parse
    a good majority of them as dates without us committing to a conversion.
    """
    sample = series.dropna().astype(str).head(sample_size)
    if len(sample) == 0:
        return False
    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        try:
            parsed = pd.to_datetime(sample, errors="coerce")
        except Exception:
            return False
    success_rate = parsed.notna().mean()
    return success_rate >= 0.9


def detect_missing(df: pd.DataFrame) -> list:
    """Return per-column missing value counts/percentages."""
    total_rows = len(df)
    report = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if total_rows > 0:
            pct = round((missing / total_rows) * 100, 2)
        else:
            pct = 0.0
        report.append({
            "column": col,
            "missing_count": missing,
            "missing_pct": pct,
        })
    return sorted(report, key=lambda r: r["missing_count"], reverse=True)


def detect_duplicates(df: pd.DataFrame) -> dict:
    dup_count = int(df.duplicated().sum())
    return {
        "duplicate_rows": dup_count,
        "duplicate_pct": round((dup_count / len(df)) * 100, 2) if len(df) else 0.0,
    }


def get_cleaning_summary(df: pd.DataFrame) -> dict:
    """Full diagnostic bundle used by the Data Cleaning tab."""
    types = detect_column_types(df)
    missing = detect_missing(df)
    duplicates = detect_duplicates(df)
    total_missing_cells = int(df.isna().sum().sum())
    return {
        "column_types": types,
        "missing": missing,
        "duplicates": duplicates,
        "total_missing_cells": total_missing_cells,
        "rows": len(df),
        "columns": len(df.columns),
    }


def apply_cleaning(df: pd.DataFrame, options: dict):
    """Apply a set of user-selected cleaning operations.

    options keys (all optional, booleans/strings):
      - drop_duplicates: bool
      - missing_strategy: 'mean' | 'median' | 'mode' | 'zero' |
                           'drop_rows' | 'drop_columns' | 'none'
      - missing_threshold: float (0-100) - columns with more than this
            percent missing get dropped when missing_strategy == 'drop_columns'
      - trim_whitespace: bool - strip leading/trailing spaces on text columns
      - convert_dates: bool - convert columns that look like dates to datetime
      - standardize_case: 'lower' | 'upper' | 'none' - normalize text case

    Returns (cleaned_df, log:list[str])
    """
    log = []
    cleaned = df.copy(deep=True)
    types = detect_column_types(cleaned)

    # 1. Convert date-like text columns first (helps downstream logic)
    if options.get("convert_dates"):
        for col in types["categorical"]:
            if _looks_like_datetime(cleaned[col]):
                try:
                    cleaned[col] = pd.to_datetime(cleaned[col], errors="coerce")
                    log.append(f"Converted column '{col}' to datetime.")
                except Exception:
                    pass
        types = detect_column_types(cleaned)  # refresh after conversion

    # 2. Trim whitespace on text columns
    if options.get("trim_whitespace"):
        text_cols = types["categorical"]
        changed = False
        for col in text_cols:
            if cleaned[col].dtype == object:
                before = cleaned[col].copy()
                cleaned[col] = cleaned[col].apply(
                    lambda v: v.strip() if isinstance(v, str) else v
                )
                if not before.equals(cleaned[col]):
                    changed = True
        if changed:
            log.append("Trimmed leading/trailing whitespace from text columns.")

    # 3. Standardize text case
    case_mode = options.get("standardize_case", "none")
    if case_mode in ("lower", "upper"):
        for col in types["categorical"]:
            if cleaned[col].dtype == object:
                cleaned[col] = cleaned[col].apply(
                    lambda v: (v.lower() if case_mode == "lower" else v.upper())
                    if isinstance(v, str) else v
                )
        log.append(f"Standardized text case to {case_mode}case for categorical columns.")

    # 4. Duplicates
    if options.get("drop_duplicates"):
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates()
        removed = before - len(cleaned)
        if removed > 0:
            log.append(f"Removed {removed} duplicate row(s).")
        else:
            log.append("No duplicate rows found to remove.")

    # 5. Missing values
    strategy = options.get("missing_strategy", "none")
    if strategy == "drop_columns":
        threshold = float(options.get("missing_threshold", 50))
        total_rows = len(cleaned)
        cols_to_drop = []
        if total_rows > 0:
            for col in cleaned.columns:
                pct = (cleaned[col].isna().sum() / total_rows) * 100
                if pct > threshold:
                    cols_to_drop.append(col)
        if cols_to_drop:
            cleaned = cleaned.drop(columns=cols_to_drop)
            log.append(
                f"Dropped {len(cols_to_drop)} column(s) with more than "
                f"{threshold}% missing values: {', '.join(cols_to_drop)}."
            )
        else:
            log.append(f"No columns exceeded the {threshold}% missing-value threshold.")

    elif strategy == "drop_rows":
        before = len(cleaned)
        cleaned = cleaned.dropna()
        removed = before - len(cleaned)
        log.append(f"Dropped {removed} row(s) containing missing values.")

    elif strategy in ("mean", "median", "zero", "mode"):
        types_now = detect_column_types(cleaned)
        filled_cols = []
        for col in types_now["numeric"]:
            if cleaned[col].isna().any():
                if strategy == "mean":
                    fill_val = cleaned[col].mean()
                elif strategy == "median":
                    fill_val = cleaned[col].median()
                elif strategy == "zero":
                    fill_val = 0
                else:  # mode
                    m = cleaned[col].mode()
                    fill_val = m.iloc[0] if not m.empty else 0
                cleaned[col] = cleaned[col].fillna(fill_val)
                filled_cols.append(col)
        # Categorical columns always filled with mode (or 'Unknown') regardless
        # of the numeric strategy chosen, since mean/median don't apply to text.
        for col in types_now["categorical"]:
            if cleaned[col].isna().any():
                m = cleaned[col].mode()
                fill_val = m.iloc[0] if not m.empty else "Unknown"
                cleaned[col] = cleaned[col].fillna(fill_val)
                filled_cols.append(col)
        if filled_cols:
            log.append(
                f"Filled missing values using '{strategy}' strategy in columns: "
                f"{', '.join(filled_cols)}."
            )
        else:
            log.append("No missing values found to fill.")

    if not log:
        log.append("No cleaning operations were selected.")

    return cleaned, log


def auto_clean(df: pd.DataFrame):
    """One-click sensible-defaults cleaning pipeline."""
    options = {
        "convert_dates": True,
        "trim_whitespace": True,
        "standardize_case": "none",
        "drop_duplicates": True,
        "missing_strategy": "drop_columns",
        "missing_threshold": 60,
    }
    cleaned, log = apply_cleaning(df, options)
    # After dropping very-empty columns, impute the rest sensibly
    cleaned, log2 = apply_cleaning(cleaned, {"missing_strategy": "median"})
    log.extend(log2)
    return cleaned, log
