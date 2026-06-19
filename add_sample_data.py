"""
Add sample data to test the dashboard
Run this to populate the database with sample apartment listings
"""

import sqlite3
from datetime import datetime, timedelta
import random

def add_sample_data(db_path='price_data.db'):
    # First initialize the database using the scraper
    from scraper import DivarScraper
    scraper = DivarScraper(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Sample apartment data for Darvazeh Shemiran area
    base_prices = [
        12000000000,  # 12 billion toman
        15000000000,  # 15 billion
        18000000000,  # 18 billion
        20000000000,  # 20 billion
        25000000000,  # 25 billion
        30000000000,  # 30 billion
    ]

    areas = [70, 85, 95, 105, 120, 140, 160]
    rooms = [1, 2, 2, 3, 3]
    building_ages = [0, 2, 5, 8, 10, 15, 20, 25]

    listings_added = 0

    # Darvazeh Shemiran approximate coordinates: 35.7456°N, 51.4215°E
    # Generate random coordinates within the neighborhood
    base_lat = 35.7456
    base_lon = 51.4215

    # Create sample listings
    for i in range(20):
        token = f"sample_{i}_{int(datetime.now().timestamp())}"
        area = random.choice(areas)
        room = random.choice(rooms)
        building_age = random.choice(building_ages)
        price = random.choice(base_prices) + random.randint(-2000000000, 2000000000)
        price_per_sqm = price / area

        # Generate random coordinates within ~1km radius
        lat = base_lat + random.uniform(-0.008, 0.008)
        lon = base_lon + random.uniform(-0.01, 0.01)

        title = f"آپارتمان {area} متری {room} خوابه - دروازه شمیران"
        url = f"https://divar.ir/v/{token}"

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO listings (
                    listing_token, title, price, price_per_sqm, area, rooms,
                    district, neighborhood, building_age, url, latitude, longitude
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token, title, price, price_per_sqm, area, room,
                'دروازه شمیران', 'darvazeh-shemiran', building_age, url, lat, lon
            ))

            cursor.execute('''
                INSERT INTO price_history (listing_token, price, price_per_sqm)
                VALUES (?, ?, ?)
            ''', (token, price, price_per_sqm))

            listings_added += 1

        except Exception as e:
            print(f"Error adding listing: {e}")

    conn.commit()

    # Add historical daily stats for the past 7 days
    for days_ago in range(7, 0, -1):
        date = (datetime.now() - timedelta(days=days_ago)).date()

        avg_price = 18000000000 + random.randint(-2000000000, 3000000000)
        avg_price_per_sqm = avg_price / 100

        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (
                date, avg_price, median_price, avg_price_per_sqm,
                median_price_per_sqm, total_listings, min_price, max_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date,
            avg_price,
            avg_price * 0.95,  # median slightly lower
            avg_price_per_sqm,
            avg_price_per_sqm * 0.95,
            random.randint(15, 25),
            avg_price * 0.6,
            avg_price * 1.8
        ))

    conn.commit()
    conn.close()

    print(f"✅ Added {listings_added} sample listings")
    print(f"✅ Added 7 days of historical stats")
    print("\nYou can now view the dashboard with sample data!")
    print("Note: This is sample data. Real scraping from Divar requires handling their anti-bot measures.")

if __name__ == '__main__':
    add_sample_data()
