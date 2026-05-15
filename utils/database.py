"""
MongoDB Atlas connection utilities.
Credentials are loaded ONLY from st.secrets — never hardcode passwords.
"""

from typing import Any, Optional
from urllib.parse import quote_plus

import certifi
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from utils.security import (
    get_connection_method,
    sanitize_error_message,
    secrets_are_configured,
)


def _get_secret(key: str, default: Optional[str] = None) -> str:
    """Read a secret from Streamlit secrets with optional default."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        if default is not None:
            return default
        raise KeyError(
            f"Missing secret '{key}'. "
            "Local: add .streamlit/secrets.toml (gitignored). "
            "Cloud: App settings → Secrets on share.streamlit.io."
        )


def _build_client() -> MongoClient:
    """
    Build MongoDB client from st.secrets only.
    Prefer split credentials (username/password/cluster) — safer for public deploys
    because the password never appears in a single connection string in your repo.
    """
    if not secrets_are_configured():
        raise ConnectionError(
            "MongoDB secrets are missing or still use placeholder values. "
            "Configure st.secrets locally or in Streamlit Cloud."
        )

    method = get_connection_method()

    client_kwargs = {
        "serverSelectionTimeoutMS": 15000,
        "tlsCAFile": certifi.where(),  # fixes SSL on macOS / some cloud runtimes
    }

    if method == "mongo_uri":
        uri = _get_secret("MONGO_URI")
        return MongoClient(uri, **client_kwargs)

    # split_credentials (recommended for Streamlit Community Cloud)
    username = quote_plus(_get_secret("MONGO_USERNAME"))
    password = quote_plus(_get_secret("MONGO_PASSWORD"))
    cluster = _get_secret("MONGO_CLUSTER")
    db_name = _get_secret("MONGO_DB", "airbnb")
    uri = (
        f"mongodb+srv://{username}:{password}@{cluster}/"
        f"{db_name}?retryWrites=true&w=majority"
    )
    return MongoClient(uri, **client_kwargs)


@st.cache_resource(show_spinner="Connecting to MongoDB Atlas...")
def get_mongo_client() -> MongoClient:
    """Create a cached MongoDB client (credentials stay server-side)."""
    return _build_client()


def get_database() -> Database:
    """Return the target database from secrets."""
    client = get_mongo_client()
    db_name = _get_secret("MONGO_DB", "airbnb")
    return client[db_name]


def get_collection() -> Collection:
    """Return the Airbnb listings collection."""
    db = get_database()
    collection_name = _get_secret("MONGO_COLLECTION", "listings")
    return db[collection_name]


@st.cache_data(ttl=600, show_spinner="Loading listings from MongoDB...")
def load_listings_data(
    projection: Optional[dict[str, int]] = None,
    limit: int = 0,
) -> pd.DataFrame:
    """
    Fetch all listings from MongoDB and return as a DataFrame.
    Uses caching to avoid repeated full-collection reads.
    """
    collection = get_collection()

    # Load full documents so we can map varied Airbnb / Atlas field names
    cursor = collection.find({}, projection)
    if limit > 0:
        cursor = cursor.limit(limit)

    records: list[dict[str, Any]] = list(cursor)
    if not records:
        return pd.DataFrame()

    # Flatten nested fields (e.g. address.country, review_scores.rating)
    df = pd.json_normalize(records, sep="_")
    if "_id" in df.columns:
        df = df.drop(columns=["_id"], errors="ignore")
    return df


def test_connection() -> tuple[bool, str]:
    """Ping MongoDB; error messages are sanitized so passwords never leak."""
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        return True, "Connected to MongoDB Atlas (credentials via st.secrets)."
    except Exception as exc:
        safe_msg = sanitize_error_message(str(exc))
        return False, f"Connection failed: {safe_msg}"
