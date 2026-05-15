"""
Plotly chart builders for the Airbnb dashboard.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Consistent color palette for a polished look
COLORS = px.colors.qualitative.Set2
TEMPLATE = "plotly_white"
CHART_HEIGHT = 380


def listings_by_country(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of listing counts by country."""
    if df.empty or "country" not in df.columns:
        return _empty_figure("No country data")

    counts = (
        df.groupby("country", as_index=False)
        .size()
        .rename(columns={"size": "listings"})
        .sort_values("listings", ascending=True)
        .tail(15)
    )

    fig = px.bar(
        counts,
        x="listings",
        y="country",
        orientation="h",
        title="Listings by Country (Top 15)",
        color="listings",
        color_continuous_scale="Blues",
        template=TEMPLATE,
        height=CHART_HEIGHT,
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return fig


def avg_price_by_room_type(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart of average price per room type."""
    if df.empty or "room_type" not in df.columns or "price" not in df.columns:
        return _empty_figure("No room type / price data")

    agg = (
        df.dropna(subset=["price", "room_type"])
        .groupby("room_type", as_index=False)["price"]
        .mean()
        .sort_values("price", ascending=False)
    )

    fig = px.bar(
        agg,
        x="room_type",
        y="price",
        title="Average Price by Room Type",
        color="room_type",
        color_discrete_sequence=COLORS,
        template=TEMPLATE,
        height=CHART_HEIGHT,
        labels={"price": "Avg Price ($)", "room_type": "Room Type"},
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-25)
    return fig


def price_distribution(df: pd.DataFrame) -> go.Figure:
    """Histogram of nightly prices."""
    if df.empty or "price" not in df.columns:
        return _empty_figure("No price data")

    prices = df["price"].dropna()
    if prices.empty:
        return _empty_figure("No valid prices")

    # Cap extreme outliers for readability (99th percentile)
    cap = prices.quantile(0.99)
    clipped = prices[prices <= cap]

    fig = px.histogram(
        x=clipped,
        nbins=40,
        title="Price Distribution (capped at 99th percentile)",
        template=TEMPLATE,
        height=CHART_HEIGHT,
        color_discrete_sequence=[COLORS[0]],
        labels={"x": "Price ($)", "count": "Listings"},
    )
    fig.update_layout(bargap=0.05, showlegend=False)
    return fig


def top_expensive_locations(df: pd.DataFrame, n: int = 10) -> go.Figure:
    """Top N locations by average nightly price."""
    loc_col = "location" if "location" in df.columns else "country"
    if df.empty or loc_col not in df.columns or "price" not in df.columns:
        return _empty_figure("No location / price data")

    agg = (
        df.dropna(subset=[loc_col, "price"])
        .groupby(loc_col, as_index=False)
        .agg(avg_price=("price", "mean"), count=("price", "size"))
        .query("count >= 3")  # minimum listings for stability
        .sort_values("avg_price", ascending=False)
        .head(n)
        .sort_values("avg_price", ascending=True)
    )

    if agg.empty:
        return _empty_figure("Not enough location data")

    fig = px.bar(
        agg,
        x="avg_price",
        y=loc_col,
        orientation="h",
        title=f"Top {n} Most Expensive Locations (avg. price)",
        color="avg_price",
        color_continuous_scale="Reds",
        template=TEMPLATE,
        height=CHART_HEIGHT,
        labels={"avg_price": "Avg Price ($)", loc_col: "Location"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return fig


def review_score_analysis(df: pd.DataFrame) -> go.Figure:
    """Box plot of review scores by room type."""
    if df.empty or "review_scores_rating" not in df.columns:
        return _empty_figure("No review score data")

    subset = df.dropna(subset=["review_scores_rating"])
    if subset.empty:
        return _empty_figure("No valid review scores")

    color_col = "room_type" if "room_type" in subset.columns else None

    fig = px.box(
        subset,
        x=color_col or "review_scores_rating",
        y="review_scores_rating",
        title="Review Score Analysis by Room Type",
        color=color_col,
        color_discrete_sequence=COLORS,
        template=TEMPLATE,
        height=CHART_HEIGHT,
        labels={"review_scores_rating": "Review Score"},
    )
    if color_col:
        fig.update_layout(xaxis_tickangle=-25)
    return fig


def listings_map(df: pd.DataFrame, max_points: int = 2000) -> go.Figure:
    """Scatter mapbox of listing locations colored by price."""
    if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
        return _empty_figure("No coordinate data")

    geo = df.dropna(subset=["latitude", "longitude"]).copy()
    if geo.empty:
        return _empty_figure("No valid coordinates")

    if len(geo) > max_points:
        geo = geo.sample(n=max_points, random_state=42)

    fig = px.scatter_mapbox(
        geo,
        lat="latitude",
        lon="longitude",
        color="price" if "price" in geo.columns else None,
        hover_name="name" if "name" in geo.columns else None,
        hover_data={
            c: True
            for c in ["country", "room_type", "price", "review_scores_rating"]
            if c in geo.columns
        },
        color_continuous_scale="Viridis",
        zoom=1,
        height=500,
        title="Airbnb Listings Map",
        opacity=0.7,
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=40, b=0),
        template=TEMPLATE,
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Placeholder figure when data is insufficient."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#888"),
    )
    fig.update_layout(
        template=TEMPLATE,
        height=CHART_HEIGHT,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
