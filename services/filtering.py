"""
filtering.py
-------------
Search & filter helpers for the Dataset tab: free-text search across all
(or selected) columns, plus structured single-column filtering by
operator (equals, contains, greater-than, etc).
"""

import pandas as pd
from .cleaning import detect_column_types


def search_dataset(df: pd.DataFrame, query: str, columns=None) -> pd.DataFrame:
    """Case-insensitive substring search across selected columns (or all)."""
    if not query:
        return df
    cols = columns if columns else list(df.columns)
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return df.iloc[0:0]

    mask = pd.Series(False, index=df.index)
    query_lower = str(query).lower()
    for col in cols:
        mask = mask | df[col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
    return df[mask]


OPERATORS = {
    "equals": lambda s, v: s.astype(str) == str(v),
    "not_equals": lambda s, v: s.astype(str) != str(v),
    "contains": lambda s, v: s.astype(str).str.lower().str.contains(str(v).lower(), na=False, regex=False),
    "greater_than": lambda s, v: pd.to_numeric(s, errors="coerce") > float(v),
    "less_than": lambda s, v: pd.to_numeric(s, errors="coerce") < float(v),
    "greater_or_equal": lambda s, v: pd.to_numeric(s, errors="coerce") >= float(v),
    "less_or_equal": lambda s, v: pd.to_numeric(s, errors="coerce") <= float(v),
}


def filter_dataset(df: pd.DataFrame, column: str, operator: str, value) -> pd.DataFrame:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")
    if operator not in OPERATORS:
        raise ValueError(f"Unsupported operator '{operator}'.")
    try:
        mask = OPERATORS[operator](df[column], value)
    except (ValueError, TypeError):
        raise ValueError(f"Value '{value}' is not valid for a numeric comparison on '{column}'.")
    return df[mask]
