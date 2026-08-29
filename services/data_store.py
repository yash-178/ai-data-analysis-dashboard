"""
data_store.py
--------------
Simple server-side, in-memory storage for uploaded datasets.

Each browser session gets its own entry (keyed by a UUID stored in the
Flask session cookie) so multiple users/tabs can work independently
without stepping on each other's data. This is intentionally simple
(no database) since the app is meant to run as a single-process demo /
portfolio project - swap this out for Redis or a DB for production use.
"""

import uuid
from flask import session

# In-memory store: { session_id: { df, original_df, filename, cleaning_log } }
_STORE = {}


def get_session_id():
    """Return the current session's unique id, creating one if needed."""
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def has_dataset():
    return get_session_id() in _STORE


def save_dataset(df, filename):
    """Store a freshly uploaded dataset, resetting any cleaning history."""
    sid = get_session_id()
    _STORE[sid] = {
        "df": df,
        "original_df": df.copy(deep=True),
        "filename": filename,
        "cleaning_log": [],
    }


def get_dataset():
    """Return the full dataset entry dict, or None if nothing uploaded."""
    sid = get_session_id()
    return _STORE.get(sid)


def get_df():
    ds = get_dataset()
    return ds["df"] if ds else None


def get_original_df():
    ds = get_dataset()
    return ds["original_df"] if ds else None


def update_df(df):
    sid = get_session_id()
    if sid in _STORE:
        _STORE[sid]["df"] = df


def add_cleaning_log(entries):
    """entries: list[str] describing cleaning actions taken."""
    sid = get_session_id()
    if sid in _STORE:
        _STORE[sid]["cleaning_log"].extend(entries)


def get_cleaning_log():
    ds = get_dataset()
    return ds["cleaning_log"] if ds else []


def get_filename():
    ds = get_dataset()
    return ds["filename"] if ds else None


def reset_to_original():
    """Undo all cleaning actions and restore the originally uploaded data."""
    sid = get_session_id()
    if sid in _STORE:
        _STORE[sid]["df"] = _STORE[sid]["original_df"].copy(deep=True)
        _STORE[sid]["cleaning_log"] = []


def clear_dataset():
    sid = get_session_id()
    _STORE.pop(sid, None)
