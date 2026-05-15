"""
Data cleaning, filtering, and insight generation for Airbnb listings.
Supports multiple MongoDB / CSV field naming conventions.
"""

from typing import Optional

import numpy as np
import pandas as pd

# Standard dashboard columns
STANDARD_COLUMNS = [
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

# Map standard name -> possible source column names (after json_normalize)
COLUMN_ALIASES: dict[str, list[str]] = {
    "name": ["name", "listing_name", "title", "NAME"],
    "country": [
        "country",
        "Country",
        "country_code",
        "address_country",
        "address.country",
        "country_name",
    ],
    "property_type": [
        "property_type",
        "propertyType",
        "property_type_group",
        "PROPERTY_TYPE",
    ],
    "room_type": ["room_type", "roomType", "ROOM_TYPE"],
    "price": ["price", "Price", "nightly_price", "price_night", "weekly_price"],
    "review_scores_rating": [
        "review_scores_rating",
        "review_scores.rating",
        "review_scores_rating",
        "reviews_rating",
        "review_scores_review_scores_rating",
        "rating",
    ],
    "latitude": ["latitude", "lat", "geo_lat", "location_lat", "coordinates_1"],
    "longitude": ["longitude", "lon", "lng", "geo_lng", "location_lon", "coordinates_0"],
    "host_id": ["host_id", "host.id", "host_id_host_id", "host_host_id"],
    "city": ["city", "address_city", "address.city", "City"],
    "neighbourhood": [
        "neighbourhood",
        "neighborhood",
        "neighbourhood_cleansed",
        "address_neighbourhood",
    ],
}


def _find_source_column(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    """Return the first matching column name in the dataframe."""
    columns_lower = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias in df.columns:
            return alias
        if alias.lower() in columns_lower:
            return columns_lower[alias.lower()]
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename varied Airbnb / MongoDB fields to standard dashboard column names.
    Missing columns are created as NA (no KeyError).
    """
    if df.empty:
        return df

    out = df.copy()

    for standard, aliases in COLUMN_ALIASES.items():
        if standard in out.columns:
            continue
        source = _find_source_column(out, aliases)
        if source is not None:
            out[standard] = out[source]

    # Ensure all standard columns exist
    for col in STANDARD_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan

    return out


def clean_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize types, handle missing values, and derive helper columns.
    """
    if df.empty:
        return df

    out = normalize_columns(df)

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
        nb = out["neighbourhood"] if "neighbourhood" in out.columns else pd.Series([""] * len(out))
        ct = out["city"] if "city" in out.columns else pd.Series([""] * len(out))
        out["location"] = (
            nb.fillna("").astype(str) + ", " + ct.fillna("").astype(str)
        ).str.strip(", ").replace("", np.nan)
    elif "country" in out.columns:
        out["location"] = out["country"]

    # Drop rows with no country only when country column has values
    if "country" in out.columns and out["country"].notna().any():
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
    """
    insights: list[str] = []

    if df.empty:
        return ["No data available for the selected filters. Adjust filters to see insights."]

    if "country" in df.columns and "price" in df.columns:
        country_price = (
            df.dropna(subset=["price", "country"])
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

    if "room_type" in df.columns:
        room_counts = df["room_type"].value_counts()
        if not room_counts.empty:
            common_room = room_counts.index[0]
            pct = 100 * room_counts.iloc[0] / len(df)
            insights.append(
                f"**Most common room type** is **{common_room}** "
                f"({pct:.1f}% of filtered listings)."
            )

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

    if "country" in df.columns:
        n_countries = df["country"].nunique()
        insights.append(
            f"The filtered dataset spans **{n_countries}** "
            f"{'country' if n_countries == 1 else 'countries'}."
        )

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

    if "property_type" in df.columns:
        prop_counts = df["property_type"].value_counts()
        if not prop_counts.empty:
            insights.append(
                f"**{prop_counts.index[0]}** is the dominant property type "
                f"with {prop_counts.iloc[0]:,} listings."
            )

    if not insights:
        insights.append(
            "Data loaded successfully. Map field names in MongoDB to "
            "`country`, `price`, `room_type`, etc. for richer insights."
        )

    return insights


def get_filter_options(df: pd.DataFrame) -> dict[str, list]:
    """Extract sorted unique values for sidebar multiselects."""
    def _unique(col: str) -> list:
        if col not in df.columns:
            return []
        vals = df[col].dropna().astype(str)
        vals = vals[~vals.isin(["nan", "None", ""])]
        return sorted(vals.unique().tolist())

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
