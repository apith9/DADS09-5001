"""
Optional script to load sample Airbnb-style documents into MongoDB Atlas.

Usage (set env vars or edit CONNECTION_URI locally — do not commit credentials):
    export MONGO_URI="mongodb+srv://..."
    python scripts/seed_mongodb.py
"""

import os
import random
from datetime import datetime

from pymongo import MongoClient

COUNTRIES = ["United States", "France", "Spain", "Italy", "Thailand", "Japan", "Portugal"]
PROPERTY_TYPES = ["Apartment", "House", "Condominium", "Loft", "Villa"]
ROOM_TYPES = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
CITIES = {
    "United States": [("New York", "Manhattan"), ("Los Angeles", "Hollywood"), ("Miami", "South Beach")],
    "France": [("Paris", "Le Marais"), ("Lyon", "Presqu'île"), ("Nice", "Promenade")],
    "Spain": [("Barcelona", "Eixample"), ("Madrid", "Centro"), ("Seville", "Triana")],
    "Italy": [("Rome", "Trastevere"), ("Milan", "Brera"), ("Florence", "Duomo")],
    "Thailand": [("Bangkok", "Sukhumvit"), ("Chiang Mai", "Old City"), ("Phuket", "Patong")],
    "Japan": [("Tokyo", "Shibuya"), ("Osaka", "Namba"), ("Kyoto", "Gion")],
    "Portugal": [("Lisbon", "Alfama"), ("Porto", "Ribeira"), ("Faro", "Marina")],
}

# Approximate city centers for demo coordinates
COORDS = {
    "New York": (40.7128, -74.0060),
    "Paris": (48.8566, 2.3522),
    "Barcelona": (41.3851, 2.1734),
    "Rome": (41.9028, 12.4964),
    "Bangkok": (13.7563, 100.5018),
    "Tokyo": (35.6762, 139.6503),
    "Lisbon": (38.7223, -9.1393),
}


def generate_listings(n: int = 500) -> list[dict]:
    """Generate synthetic listing documents."""
    listings = []
    for i in range(n):
        country = random.choice(COUNTRIES)
        city, neighbourhood = random.choice(CITIES[country])
        room_type = random.choices(ROOM_TYPES, weights=[50, 35, 10, 5])[0]
        base_price = {"Entire home/apt": 120, "Private room": 55, "Shared room": 30, "Hotel room": 90}[room_type]
        price = round(base_price * random.uniform(0.6, 2.5) + random.gauss(0, 15), 2)
        price = max(20, price)

        lat, lon = COORDS.get(city, (0.0, 0.0))
        lat += random.uniform(-0.08, 0.08)
        lon += random.uniform(-0.08, 0.08)

        listings.append(
            {
                "name": f"Cozy stay #{i + 1} in {neighbourhood}",
                "country": country,
                "city": city,
                "neighbourhood": neighbourhood,
                "property_type": random.choice(PROPERTY_TYPES),
                "room_type": room_type,
                "price": price,
                "review_scores_rating": round(min(100, max(60, random.gauss(88, 8))), 1),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "host_id": f"host_{random.randint(1, 120)}",
                "created_at": datetime.utcnow(),
            }
        )
    return listings


def main() -> None:
    uri = os.environ.get("MONGO_URI")
    if not uri:
        raise SystemExit("Set MONGO_URI environment variable before running this script.")

    db_name = os.environ.get("MONGO_DB", "airbnb")
    collection_name = os.environ.get("MONGO_COLLECTION", "listings")

    client = MongoClient(uri)
    collection = client[db_name][collection_name]

    collection.delete_many({})  # clear demo data
    docs = generate_listings(800)
    result = collection.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} documents into {db_name}.{collection_name}")


if __name__ == "__main__":
    main()
