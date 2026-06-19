import requests
import json
import sqlite3
from datetime import datetime
from typing import List, Dict
import time

class DivarScraper:
    def __init__(self, db_path='price_data.db'):
        self.base_url = "https://api.divar.ir/v8/web-search/tehran/buy-apartment"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_token TEXT UNIQUE,
                title TEXT,
                price REAL,
                price_per_sqm REAL,
                area REAL,
                rooms INTEGER,
                district TEXT,
                neighborhood TEXT,
                floor INTEGER,
                building_age INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_token TEXT,
                price REAL,
                price_per_sqm REAL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_token) REFERENCES listings(listing_token)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                avg_price REAL,
                median_price REAL,
                avg_price_per_sqm REAL,
                median_price_per_sqm REAL,
                total_listings INTEGER,
                min_price REAL,
                max_price REAL
            )
        ''')

        conn.commit()
        conn.close()

    def scrape_listings(self, neighborhood='darvazeh-shemiran', max_pages=5):
        """Scrape apartment listings from Divar"""
        all_listings = []
        page = 0
        last_post_date = None

        while page < max_pages:
            params = {
                'districts': '1',
            }

            if neighborhood:
                params['neighborhoods'] = neighborhood

            if last_post_date:
                params['last-post-date'] = last_post_date

            try:
                response = requests.get(self.base_url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                if 'web_widgets' not in data or 'list_data' not in data['web_widgets']:
                    break

                widgets = data['web_widgets']['list_data']

                for widget in widgets:
                    if widget.get('widget_type') == 'POST_ROW':
                        listing_data = self.parse_listing(widget['data'])
                        if listing_data:
                            all_listings.append(listing_data)

                # Check if there's a next page
                last_post_date = data.get('last_post_date')
                if not last_post_date or not widgets:
                    break

                page += 1
                time.sleep(1)  # Be respectful to the server

            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                break

        return all_listings

    def parse_listing(self, widget_data):
        """Parse listing data from widget"""
        try:
            listing = {
                'token': widget_data.get('token'),
                'title': widget_data.get('title', ''),
                'price': None,
                'price_per_sqm': None,
                'area': None,
                'rooms': None,
                'district': None,
                'neighborhood': None,
            }

            # Extract data from middle_description_text
            if 'middle_description_text' in widget_data:
                desc_parts = widget_data['middle_description_text'].split('•')
                for part in desc_parts:
                    part = part.strip()
                    if 'متر' in part and listing['area'] is None:
                        try:
                            listing['area'] = float(part.replace('متر', '').strip())
                        except:
                            pass
                    elif 'اتاق' in part:
                        try:
                            listing['rooms'] = int(part.replace('اتاق', '').strip())
                        except:
                            pass

            # Extract price from top_description_text
            if 'top_description_text' in widget_data:
                price_text = widget_data['top_description_text']
                if 'تومان' in price_text:
                    try:
                        # Remove commas and extract number
                        price_str = price_text.replace('تومان', '').replace(',', '').strip()
                        listing['price'] = float(price_str)

                        # Calculate price per square meter
                        if listing['area'] and listing['area'] > 0:
                            listing['price_per_sqm'] = listing['price'] / listing['area']
                    except:
                        pass

            return listing if listing['token'] else None

        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None

    def save_listings(self, listings: List[Dict]):
        """Save listings to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = datetime.now().date()

        for listing in listings:
            if not listing.get('price'):
                continue

            # Insert or update listing
            cursor.execute('''
                INSERT OR IGNORE INTO listings (
                    listing_token, title, price, price_per_sqm, area, rooms, district, neighborhood
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing['token'],
                listing['title'],
                listing['price'],
                listing['price_per_sqm'],
                listing['area'],
                listing['rooms'],
                listing.get('district'),
                listing.get('neighborhood')
            ))

            # Add to price history
            cursor.execute('''
                INSERT INTO price_history (listing_token, price, price_per_sqm)
                VALUES (?, ?, ?)
            ''', (
                listing['token'],
                listing['price'],
                listing['price_per_sqm']
            ))

        conn.commit()

        # Calculate daily statistics
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (
                date, avg_price, median_price, avg_price_per_sqm,
                median_price_per_sqm, total_listings, min_price, max_price
            )
            SELECT
                DATE('now') as date,
                AVG(price) as avg_price,
                (SELECT AVG(price) FROM (
                    SELECT price FROM price_history
                    WHERE DATE(scraped_at) = DATE('now')
                    ORDER BY price
                    LIMIT 2 - (SELECT COUNT(*) FROM price_history WHERE DATE(scraped_at) = DATE('now')) % 2
                    OFFSET (SELECT (COUNT(*) - 1) / 2 FROM price_history WHERE DATE(scraped_at) = DATE('now'))
                )) as median_price,
                AVG(price_per_sqm) as avg_price_per_sqm,
                (SELECT AVG(price_per_sqm) FROM (
                    SELECT price_per_sqm FROM price_history
                    WHERE DATE(scraped_at) = DATE('now') AND price_per_sqm IS NOT NULL
                    ORDER BY price_per_sqm
                    LIMIT 2 - (SELECT COUNT(*) FROM price_history WHERE DATE(scraped_at) = DATE('now') AND price_per_sqm IS NOT NULL) % 2
                    OFFSET (SELECT (COUNT(*) - 1) / 2 FROM price_history WHERE DATE(scraped_at) = DATE('now') AND price_per_sqm IS NOT NULL)
                )) as median_price_per_sqm,
                COUNT(*) as total_listings,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM price_history
            WHERE DATE(scraped_at) = DATE('now')
        ''')

        conn.commit()
        conn.close()

        print(f"Saved {len(listings)} listings to database")

    def run(self, neighborhood='darvazeh-shemiran'):
        """Run the scraper"""
        print(f"Starting scrape for {neighborhood}...")
        listings = self.scrape_listings(neighborhood=neighborhood)
        print(f"Found {len(listings)} listings")

        if listings:
            self.save_listings(listings)
            print("Data saved successfully")
        else:
            print("No listings found")

if __name__ == '__main__':
    scraper = DivarScraper()
    scraper.run()
