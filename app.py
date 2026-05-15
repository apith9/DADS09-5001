"""
Airbnb Analytics Dashboard
Streamlit app connected to MongoDB Atlas.
"""

import pandas as pd
import streamlit as st

from utils import charts
from utils.database import load_listings_data, test_connection
from utils.security import get_safe_secrets_summary
from utils.preprocessing import (
    apply_filters,
    clean_listings,
    compute_kpis,
    generate_insights,
    get_filter_options,
)

# ---------------------------------------------------------------------------
# Page config & global styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Airbnb Analytics Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* Main header */
    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF5A5F 0%, #FF385C 50%, #E61E4D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        color: #6b7280;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    /* KPI cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        color: #6b7280 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }
    /* Insight cards */
    .insight-box {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 0.85rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.65rem;
        font-size: 0.95rem;
        color: #1e3a5f;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #fafafa;
    }
    /* Hide Streamlit footer branding for cleaner demo */
    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Dashboard title and subtitle."""
    st.markdown('<p class="main-header">🏠 Airbnb Analytics Dashboard</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Explore listings, pricing, and reviews — powered by MongoDB Atlas</p>',
        unsafe_allow_html=True,
    )


def render_sidebar_filters(options: dict) -> dict:
    """
    Sidebar filter controls.
    Returns a dict of selected filter values.
    """
    st.sidebar.header("🔍 Filters")

    if options["countries"]:
        countries = st.sidebar.multiselect(
            "Country",
            options=options["countries"],
            default=options["countries"],
            help="Select one or more countries",
        )
    else:
        countries = []
        st.sidebar.caption("Country filter unavailable (no country field in data).")

    if options["property_types"]:
        property_types = st.sidebar.multiselect(
            "Property Type",
            options=options["property_types"],
            default=options["property_types"],
        )
    else:
        property_types = []
        st.sidebar.caption("Property type filter unavailable.")

    if options["room_types"]:
        room_types = st.sidebar.multiselect(
            "Room Type",
            options=options["room_types"],
            default=options["room_types"],
        )
    else:
        room_types = []
        st.sidebar.caption("Room type filter unavailable.")

    price_min = options["price_min"]
    price_max = options["price_max"]
    price_range = st.sidebar.slider(
        "Price Range ($)",
        min_value=float(price_min),
        max_value=float(price_max),
        value=(float(price_min), float(price_max)),
        step=1.0,
    )

    st.sidebar.divider()
    st.sidebar.caption("Data refreshes every 10 minutes (cached).")

    return {
        "countries": countries,
        "property_types": property_types,
        "room_types": room_types,
        "price_range": price_range,
    }


def render_kpis(kpis: dict) -> None:
    """Four KPI metric cards in a responsive row."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Listings", f"{kpis['total_listings']:,}")
    with c2:
        st.metric("Average Price", f"${kpis['avg_price']:,.2f}")
    with c3:
        st.metric("Avg Review Score", f"{kpis['avg_review']:.2f}")
    with c4:
        st.metric("Number of Hosts", f"{kpis['num_hosts']:,}")


def render_charts(df: pd.DataFrame) -> None:
    """Two-column chart grid."""
    row1_a, row1_b = st.columns(2)
    with row1_a:
        st.plotly_chart(charts.listings_by_country(df), use_container_width=True)
    with row1_b:
        st.plotly_chart(charts.avg_price_by_room_type(df), use_container_width=True)

    row2_a, row2_b = st.columns(2)
    with row2_a:
        st.plotly_chart(charts.price_distribution(df), use_container_width=True)
    with row2_b:
        st.plotly_chart(charts.top_expensive_locations(df), use_container_width=True)

    st.plotly_chart(charts.review_score_analysis(df), use_container_width=True)


def render_map_section(df: pd.DataFrame) -> None:
    """Interactive map: native st.map + Plotly mapbox."""
    st.subheader("📍 Geographic Distribution")

    geo = df.dropna(subset=["latitude", "longitude"]).copy()
    if geo.empty:
        st.warning("No listings with valid coordinates for the current filters.")
        return

    tab_native, tab_plotly = st.tabs(["Streamlit Map", "Plotly Map"])

    with tab_native:
        # st.map expects columns named lat/lon or latitude/longitude
        map_df = geo[["latitude", "longitude"]].rename(
            columns={"latitude": "lat", "longitude": "lon"}
        )
        st.map(map_df, size=20, color="#FF5A5F")

    with tab_plotly:
        st.plotly_chart(charts.listings_map(geo), use_container_width=True)


def render_data_table(df: pd.DataFrame) -> None:
    """Searchable table with CSV download."""
    st.subheader("📋 Listings Data")

    search = st.text_input("Search listings", placeholder="Search by name, country, room type...")

    display_cols = [
        c
        for c in [
            "name",
            "country",
            "property_type",
            "room_type",
            "price",
            "review_scores_rating",
            "latitude",
            "longitude",
            "host_id",
            "location",
        ]
        if c in df.columns
    ]
    table_df = df[display_cols].copy()

    if search:
        mask = table_df.astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        table_df = table_df[mask]

    st.dataframe(
        table_df,
        use_container_width=True,
        height=400,
        hide_index=True,
    )

    csv = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered data as CSV",
        data=csv,
        file_name="airbnb_filtered_listings.csv",
        mime="text/csv",
        type="primary",
    )


def render_insights(df: pd.DataFrame) -> None:
    """AI-style auto-generated insights panel."""
    st.subheader("💡 Smart Insights")
    insights = generate_insights(df)
    for text in insights:
        st.markdown(
            f'<div class="insight-box">{text}</div>',
            unsafe_allow_html=True,
        )


def render_security_panel() -> None:
    """
    Show that credentials come from st.secrets only.
    Never display st.secrets values — passwords must not appear in the UI.
    """
    summary = get_safe_secrets_summary()
    with st.sidebar.expander("🔒 Secure deployment", expanded=False):
        st.markdown(
            "**Public app, private password:** credentials live in "
            "`st.secrets` (local file or Streamlit Cloud Secrets), "
            "**not** in your GitHub repository."
        )
        if summary["status"] == "ok":
            st.success(summary["message"])
            st.caption(f"Method: `{summary['method']}`")
            st.caption(
                f"Database: `{summary['database']}` · "
                f"Collection: `{summary['collection']}`"
            )
        else:
            st.warning(summary["message"])
        st.markdown(
            "- ✅ `.streamlit/secrets.toml` is gitignored\n"
            "- ✅ No password in `app.py` or `utils/`\n"
            "- ✅ Connection errors are redacted"
        )


def main() -> None:
    """Application entry point."""
    render_header()

    # Connection status in sidebar
    st.sidebar.title("Airbnb Dashboard")
    render_security_panel()

    ok, msg = test_connection()
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)
        st.error(
            "Cannot connect to MongoDB. Add secrets to "
            "`.streamlit/secrets.toml` (local) or **Streamlit Cloud → Settings → Secrets** "
            "(public deploy). Ensure Atlas Network Access allows the server IP."
        )
        st.stop()

    # Load and clean data (cached in database module)
    raw_df = load_listings_data()
    if raw_df.empty:
        st.warning(
            "No documents found in the collection. "
            "Import Airbnb data into MongoDB Atlas first."
        )
        st.stop()

    df = clean_listings(raw_df)

    with st.expander("📎 Loaded data columns (from MongoDB)", expanded=False):
        st.caption(
            f"{len(raw_df):,} rows · Fields are auto-mapped to dashboard names "
            f"(`country`, `price`, `room_type`, …)."
        )
        st.write(list(df.columns))

    options = get_filter_options(df)
    filters = render_sidebar_filters(options)

    filtered_df = apply_filters(
        df,
        countries=filters["countries"] or None,
        property_types=filters["property_types"] or None,
        room_types=filters["room_types"] or None,
        price_range=filters["price_range"],
    )

    if filtered_df.empty:
        st.warning("No listings match the current filters.")
        st.stop()

    # KPIs
    kpis = compute_kpis(filtered_df)
    render_kpis(kpis)

    st.divider()

    # Insights (above charts for narrative flow)
    render_insights(filtered_df)

    st.divider()

    # Charts
    st.subheader("📊 Analytics")
    render_charts(filtered_df)

    st.divider()

    # Map
    render_map_section(filtered_df)

    st.divider()

    # Data table
    render_data_table(filtered_df)


if __name__ == "__main__":
    main()
