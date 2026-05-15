# Airbnb Analytics Dashboard

A production-style **Streamlit** dashboard that explores Airbnb listings stored in **MongoDB Atlas**. Built for data science and full-stack coursework with interactive Plotly charts, geographic maps, KPI cards, and auto-generated insights.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)

---

## Features

| Section | Description |
|--------|-------------|
| **Sidebar filters** | Country, property type, room type, price range slider |
| **KPI cards** | Total listings, average price, average review score, number of hosts |
| **Charts** | Listings by country, avg price by room type, price histogram, top expensive locations, review analysis |
| **Maps** | `st.map()` and Plotly scatter mapbox |
| **Data table** | Searchable dataframe + CSV download |
| **Smart insights** | Auto-generated narrative insights from filtered data |

---

## Can you deploy a public Streamlit app without leaking your database password?

**Yes.** This project is built for that:

| What goes on **public GitHub** | What stays **private** |
|-------------------------------|-------------------------|
| `app.py`, `utils/`, charts | `MONGO_PASSWORD`, `MONGO_URI` |
| `secrets.toml.example` (placeholders only) | Real `.streamlit/secrets.toml` (gitignored) |
| README, requirements | **Streamlit Cloud → Secrets** (encrypted at rest) |

**How it works**

1. Code reads credentials only via `st.secrets` — never hardcoded in Python files.
2. `.gitignore` blocks `secrets.toml` so you cannot accidentally push passwords.
3. On [Streamlit Community Cloud](https://share.streamlit.io), you paste secrets in **App settings → Secrets**; they are injected at runtime on Streamlit’s servers, not exposed in the public repo or in the browser.
4. `utils/security.py` redacts connection strings from error messages so a failed login does not print your password.
5. The dashboard UI shows *that* secrets are loaded — never the actual password.

**Deploy checklist (safe public website)**

- [ ] Push repo to GitHub **without** `secrets.toml`
- [ ] Confirm `secrets.toml` is in `.gitignore`
- [ ] Add secrets in Streamlit Cloud UI (copy structure from `secrets.toml.example`)
- [ ] Use a read-only MongoDB user if possible
- [ ] Never `st.write(st.secrets)` or print `MONGO_URI` for debugging

---

## Project structure

```
project/
├── app.py                      # Main Streamlit application
├── requirements.txt
├── README.md
├── .gitignore
├── utils/
│   ├── database.py             # MongoDB via st.secrets only
│   ├── security.py             # Redact errors; validate secrets
│   ├── charts.py               # Plotly chart builders
│   └── preprocessing.py        # Cleaning, filters, KPIs, insights
├── scripts/
│   └── seed_mongodb.py         # Optional sample data loader
└── .streamlit/
    └── secrets.toml.example    # Template for local secrets
```

---

## Prerequisites

- Python 3.10+
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) cluster (free tier works)
- Airbnb-style documents in a collection (see [Dataset fields](#dataset-fields))

---

## 1. MongoDB Atlas setup

1. Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register).
2. **Database Access** → create a database user (username + password).
3. **Network Access** → add your IP (`0.0.0.0/0` only for quick demos; restrict in production).
4. **Database** → Create database `airbnb` and collection `listings`.
5. Import your Airbnb JSON/CSV or run the included seed script (see below).

### Dataset fields

Each document should include fields similar to:

| Field | Type | Example |
|-------|------|---------|
| `name` | string | `"Sunny loft in Paris"` |
| `country` | string | `"France"` |
| `property_type` | string | `"Apartment"` |
| `room_type` | string | `"Entire home/apt"` |
| `price` | number or string | `95` or `"$95"` |
| `review_scores_rating` | number | `92.5` |
| `latitude` | number | `48.8566` |
| `longitude` | number | `2.3522` |
| `host_id` | string | `"host_42"` |

Optional: `city`, `neighbourhood` (used for location labels).

---

## 2. Local installation

```bash
cd project
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure secrets (local)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your credentials (recommended: **split fields**):

```toml
MONGO_USERNAME = "your_atlas_username"
MONGO_PASSWORD = "your_real_password"
MONGO_CLUSTER = "cluster0.xxxxx.mongodb.net"
MONGO_DB = "airbnb"
MONGO_COLLECTION = "listings"
```

> **Security:** `secrets.toml` is in `.gitignore`. Your public GitHub repo only contains `secrets.toml.example` with placeholders.

Optional single-line URI (still via secrets, not in code):

```toml
# MONGO_URI = "mongodb+srv://..."
```

### Optional: seed sample data

```bash
export MONGO_URI="mongodb+srv://USER:PASS@cluster.mongodb.net/airbnb?retryWrites=true&w=majority"
python scripts/seed_mongodb.py
```

### Run the dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 3. MongoDB connection example (no password in source code)

```python
import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def get_client():
    # Password exists only in st.secrets — not in this file
    user = st.secrets["MONGO_USERNAME"]
    password = st.secrets["MONGO_PASSWORD"]
    cluster = st.secrets["MONGO_CLUSTER"]
    db = st.secrets.get("MONGO_DB", "airbnb")
    uri = f"mongodb+srv://{user}:{password}@{cluster}/{db}?retryWrites=true&w=majority"
    return MongoClient(uri, serverSelectionTimeoutMS=10000)
```

See `utils/database.py` and `utils/security.py` for caching, validation, and safe error messages.

---

## 4. Deploy to Streamlit Community Cloud

1. Push this project to a **public** GitHub repository (without `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app** → select your repo, branch `main`, main file path: `app.py`.
4. Open **App settings → Secrets** and paste (use your real values; this UI is private):

```toml
MONGO_USERNAME = "your_atlas_username"
MONGO_PASSWORD = "your_atlas_password"
MONGO_CLUSTER = "cluster0.xxxxx.mongodb.net"
MONGO_DB = "airbnb"
MONGO_COLLECTION = "listings"
```

5. In MongoDB Atlas **Network Access**, allow Streamlit Cloud (often `0.0.0.0/0` for class projects).
6. Deploy — your app URL is public; your password is not in the repo.

### Adding secrets safely

| Do | Don't |
|----|--------|
| Store password in **Streamlit Cloud Secrets** | Commit `secrets.toml` to GitHub |
| Keep `secrets.toml.example` with placeholders only | Put `MONGO_PASSWORD` in `app.py` |
| Use `.streamlit/secrets.toml` locally (gitignored) | `st.write(st.secrets)` in the app |
| Rotate Atlas password if leaked | Paste real URI in README or screenshots |

---

## 5. Performance notes

- `@st.cache_resource` caches the MongoDB client.
- `@st.cache_data(ttl=600)` caches listing data for 10 minutes.
- Plotly maps sample up to 2,000 points for responsiveness.
- Price histogram caps at the 99th percentile to reduce outlier skew.

---

## 6. Example screenshots (for your report)

When documenting your university project, capture:

1. **Home / KPI row** — gradient title, four metric cards after applying filters.
2. **Smart Insights** — blue insight cards with country/room-type narratives.
3. **Analytics grid** — two-column Plotly charts (country bar chart, room-type pricing).
4. **Geographic tab** — Streamlit map vs Plotly map side by side.
5. **Data table** — search box filtering rows + CSV download button.
6. **Sidebar** — multiselect filters and price slider with connection status.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Connection failed` | Check `MONGO_URI`, Atlas IP whitelist, username/password |
| Empty dashboard | Verify collection name and that documents exist |
| `Missing secret` | Create `.streamlit/secrets.toml` or Cloud secrets |
| Slow load | Reduce collection size or add indexes on `country`, `price` |

---

## License

MIT — suitable for academic and portfolio use.
