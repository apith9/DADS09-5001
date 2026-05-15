"""
Data cleaning, filtering, and insight generation for Airbnb listings.
"""

from typing import Optional

import numpy as np
import pandas as pd


# Canonical column names used across the dashboard
REQUIRED_COLUMNS = [
    "name",
    "country",
    "property_type",
    "room_type",
    "price",
    "review_scores_rating",
    "latitude",
    "longitude",
    "host_id",
]


def clean_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize types, handle missing values, and derive helper columns.
    """
    if df.empty:
        return df

    out = df.copy()

    # Normalize string columns
    for col in ["country", "property_type", "room_type", "name"]:
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()
            out[col] = out[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # Price: strip currency symbols and coerce to float
    if "price" in out.columns:
        if out["price"].dtype == object:
            out["price"] = (
                out["price"]
                .astype(str)
                .str.replace(r"[^\d.]", "", regex=True)
                .replace("", np.nan)
            )
        out["price"] = pd.to_numeric(out["price"], errors="coerce")

    # Review score
    if "review_scores_rating" in out.columns:
        out["review_scores_rating"] = pd.to_numeric(
            out["review_scores_rating"], errors="coerce"
        )

    # Coordinates
    for col in ["latitude", "longitude"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Host id as string for counting unique hosts
    if "host_id" in out.columns:
        out["host_id"] = out["host_id"].astype(str)

    # Location label for maps / top locations
    if "neighbourhood" in out.columns or "city" in out.columns:
        nb = out.get("neighbourhood", pd.Series([""] * len(out)))
        ct = out.get("city", pd.Series([""] * len(out)))
        out["location"] = (
            nb.fillna("").astype(str)
            + ", "
            + ct.fillna("").astype(str)
        ).str.strip(", ").replace("", np.nan)
    elif "country" in out.columns:
        out["location"] = out["country"]

    # Drop rows without usable price for price-based charts (keep for counts if needed)
    out = out.dropna(subset=["country"], how="all")

    return out


def apply_filters(
    df: pd.DataFrame,
    countries: Optional[list[str]] = None,
    property_types: Optional[list[str]] = None,
    room_types: Optional[list[str]] = None,
    price_range: Optional[tuple[float, float]] = None,
) -> pd.DataFrame:
    """Apply sidebar filters to the dataframe."""
    if df.empty:
        return df

    filtered = df.copy()

    if countries and "country" in filtered.columns:
        filtered = filtered[filtered["country"].isin(countries)]

    if property_types and "property_type" in filtered.columns:
        filtered = filtered[filtered["property_type"].isin(property_types)]

    if room_types and "room_type" in filtered.columns:
        filtered = filtered[filtered["room_type"].isin(room_types)]

    if price_range and "price" in filtered.columns:
        lo, hi = price_range
        mask = filtered["price"].between(lo, hi) | filtered["price"].isna()
        filtered = filtered[mask]

    return filtered


def compute_kpis(df: pd.DataFrame) -> dict[str, float | int | str]:
    """Calculate KPI metrics for the filtered dataset."""
    if df.empty:
        return {
            "total_listings": 0,
            "avg_price": 0.0,
            "avg_review": 0.0,
            "num_hosts": 0,
        }

    prices = df["price"].dropna() if "price" in df.columns else pd.Series(dtype=float)
    reviews = (
        df["review_scores_rating"].dropna()
        if "review_scores_rating" in df.columns
        else pd.Series(dtype=float)
    )
    hosts = df["host_id"].nunique() if "host_id" in df.columns else 0

    return {
        "total_listings": len(df),
        "avg_price": float(prices.mean()) if len(prices) else 0.0,
        "avg_review": float(reviews.mean()) if len(reviews) else 0.0,
        "num_hosts": int(hosts),
    }


def generate_insights(df: pd.DataFrame) -> list[str]:
    """
    Auto-generate human-readable insights from the current filtered data.
    AI-style narrative summaries for the insights panel.
    """
    insights: list[str] = []

    if df.empty:
        return ["No data available for the selected filters. Adjust filters to see insights."]

    # Highest average price by country
    if "country" in df.columns and "price" in df.columns:
        country_price = (
            df.dropna(subset=["price"])
            .groupby("country")["price"]
            .mean()
            .sort_values(ascending=False)
        )
        if not country_price.empty:
            top_country = country_price.index[0]
            top_price = country_price.iloc[0]
            insights.append(
                f"**Highest average price** is in **{top_country}** "
                f"at **${top_price:,.2f}** per night (among filtered listings)."
            )

    # Most common room type
    if "room_type" in df.columns:
        room_counts = df["room_type"].value_counts()
        if not room_counts.empty:
            common_room = room_counts.index[0]
            pct = 100 * room_counts.iloc[0] / len(df)
            insights.append(
                f"**Most common room type** is **{common_room}** "
                f"({pct:.1f}% of filtered listings)."
            )

    # Price vs review correlation trend
    if "price" in df.columns and "review_scores_rating" in df.columns:
        subset = df[["price", "review_scores_rating"]].dropna()
        if len(subset) > 10:
            corr = subset["price"].corr(subset["review_scores_rating"])
            if corr > 0.15:
                insights.append(
                    f"**Trend:** Higher-priced listings tend to have **slightly higher** "
                    f"review scores (correlation ≈ {corr:.2f})."
                )
            elif corr < -0.15:
                insights.append(
                    f"**Trend:** Higher-priced listings show **slightly lower** "
                    f"review scores (correlation ≈ {corr:.2f})."
                )
            else:
                insights.append(
                    "**Trend:** Price and review scores show **weak correlation** "
                    f"(≈ {corr:.2f}) in the current selection."
                )

    # Geographic spread
    if "country" in df.columns:
        n_countries = df["country"].nunique()
        insights.append(
            f"The filtered dataset spans **{n_countries}** "
            f"{'country' if n_countries == 1 else 'countries'}."
        )

    # Expensive locations
    if "location" in df.columns and "price" in df.columns:
        loc_price = (
            df.dropna(subset=["location", "price"])
            .groupby("location")["price"]
            .mean()
            .sort_values(ascending=False)
        )
        if len(loc_price) >= 3:
            insights.append(
                f"**Premium locations** in this view include "
                f"**{loc_price.index[0]}**, **{loc_price.index[1]}**, and "
                f"**{loc_price.index[2]}** by average nightly rate."
            )

    # Listing volume
    if "property_type" in df.columns:
        prop_counts = df["property_type"].value_counts()
        if not prop_counts.empty:
            insights.append(
                f"**{prop_counts.index[0]}** is the dominant property type "
                f"with {prop_counts.iloc[0]:,} listings."
            )

    return insights


def get_filter_options(df: pd.DataFrame) -> dict[str, list]:
    """Extract sorted unique values for sidebar multiselects."""
    def _unique(col: str) -> list:
        if col not in df.columns:
            return []
        return sorted(df[col].dropna().astype(str).unique().tolist())

    prices = df["price"].dropna() if "price" in df.columns else pd.Series([0, 500])
    pmin = float(prices.min()) if len(prices) else 0.0
    pmax = float(prices.max()) if len(prices) else 500.0

    return {
        "countries": _unique("country"),
        "property_types": _unique("property_type"),
        "room_types": _unique("room_type"),
        "price_min": max(0.0, pmin),
        "price_max": max(pmin + 1, pmax),
    }
