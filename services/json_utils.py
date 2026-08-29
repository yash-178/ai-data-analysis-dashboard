"""
json_utils.py
--------------
Helpers to safely convert pandas/NumPy objects (which are NOT natively
JSON serializable - e.g. np.int64, np.nan, pd.Timestamp) into plain
Python structures that Flask's jsonify() can handle without raising
TypeErrors.
"""

import json
import math
import numpy as np
import pandas as pd


def _default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, (pd.Series,)):
        return obj.tolist()
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def to_jsonable(obj):
    """Round-trip an object through JSON with a NumPy/Pandas-aware encoder
    so every NaN/np.int64/Timestamp etc. becomes a plain, jsonify-safe value.
    """
    return json.loads(json.dumps(obj, default=_default))


def df_to_records(df, limit=None):
    """Convert a DataFrame to a list of JSON-safe dict records.
    NaN values become None (null) rather than the string "NaN".
    """
    if limit is not None:
        df = df.head(limit)
    # Using pandas' own to_json handles NaN -> null and Timestamps cleanly.
    return json.loads(df.to_json(orient="records", date_format="iso"))
