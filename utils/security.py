"""
Security helpers: keep database passwords out of logs, UI, and public repos.
"""

import re
from typing import Any

import streamlit as st

# Placeholder values that must not be used in production
_PLACEHOLDER_MARKERS = (
    "<username>",
    "<password>",
    "<cluster>",
    "your_atlas_password",
    "USERNAME",
    "PASSWORD",
    "xxxxx",
)


def sanitize_error_message(message: str) -> str:
    """
    Strip credentials from exception text before showing users.
    pymongo errors may echo the connection string containing the password.
    """
    if not message:
        return "Connection failed. Check secrets and Atlas network access."

    redacted = str(message)
    redacted = re.sub(
        r"mongodb(\+srv)?://[^\s\)'\"]+",
        "mongodb+srv://***:***@***",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(password|passwd|pwd)\s*[=:]\s*\S+",
        r"\1=***",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted


def _is_placeholder(value: str) -> bool:
    if not value or not isinstance(value, str):
        return True
    lower = value.lower()
    return any(marker.lower() in lower for marker in _PLACEHOLDER_MARKERS)


def get_connection_method() -> str | None:
    """
    Detect how credentials are supplied without reading values into logs.
    Returns: 'split_credentials', 'mongo_uri', or None if not configured.
    """
    try:
        secrets: Any = st.secrets
    except (FileNotFoundError, Exception):
        return None

    if "MONGO_URI" in secrets and not _is_placeholder(str(secrets["MONGO_URI"])):
        return "mongo_uri"

    required = ("MONGO_USERNAME", "MONGO_PASSWORD", "MONGO_CLUSTER")
    if all(k in secrets for k in required):
        if any(_is_placeholder(str(secrets[k])) for k in required):
            return None
        return "split_credentials"

    return None


def secrets_are_configured() -> bool:
    """True when real (non-placeholder) MongoDB secrets exist."""
    return get_connection_method() is not None


def get_safe_secrets_summary() -> dict[str, str]:
    """
    Metadata for the UI — never includes passwords or full URIs.
    """
    method = get_connection_method()
    if method is None:
        return {
            "status": "missing",
            "method": "none",
            "message": "MongoDB credentials not configured.",
        }

    db = str(st.secrets.get("MONGO_DB", "airbnb"))
    collection = str(st.secrets.get("MONGO_COLLECTION", "listings"))

    return {
        "status": "ok",
        "method": method,
        "message": "Credentials loaded from st.secrets (not stored in source code).",
        "database": db,
        "collection": collection,
    }
