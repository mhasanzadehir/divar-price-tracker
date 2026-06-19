import requests
import json
import sqlite3
from datetime import datetime
from typing import List, Dict
import time
import re
from bs4 import BeautifulSoup

class DivarScraper:
    def __init__(self, db_path='price_data.db'):
        self.page_url = "https://divar.ir/s/tehran/buy-apartment/darvazeh-shemiran"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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
                url TEXT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add URL and coordinates columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE listings ADD COLUMN url TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE listings ADD COLUMN latitude REAL')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE listings ADD COLUMN longitude REAL')
        except:
            pass

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

    def scrape_listings(self, neighborhood='darvazeh-shemiran'):
        """Scrape apartment listings from Divar by parsing HTML"""
        all_listings = []

        try:
            response = requests.get(self.page_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Extract JSON data from the page
            html_content = response.text

            # Find the preloaded state in the HTML
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', html_content, re.DOTALL)

            if match:
                try:
                    preloaded_data = json.loads(match.group(1))

                    # Navigate through the JSON structure to find listings
                    if 'slist' in preloaded_data:
                        slist_data = preloaded_data['slist']

                        # Look for posts in the data
                        if 'data' in slist_data and 'widget_list' in slist_data['data']:
                            widgets = slist_data['data']['widget_list']

                            for widget in widgets:
                                if widget.get('widget_type') == 'POST_ROW':
                                    listing_data = self.parse_widget(widget.get('data', {}))
                                    if listing_data and listing_data.get('price'):
                                        all_listings.append(listing_data)

                    # Also try alternative structure
                    if not all_listings and 'search' in preloaded_data:
                        search_data = preloaded_data.get('search', {})
                        if 'widgetList' in search_data:
                            for widget in search_data['widgetList']:
                                if widget.get('widget_type') == 'POST_ROW':
                                    listing_data = self.parse_widget(widget.get('data', {}))
                                    if listing_data and listing_data.get('price'):
                                        all_listings.append(listing_data)

                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")

            # If no listings found, try BeautifulSoup parsing
            if not all_listings:
                all_listings = self.parse_html_fallback(html_content)

        except Exception as e:
            print(f"Error scraping page: {e}")

        return all_listings

    def parse_widget(self, widget_data):
        """Parse listing data from widget"""
        try:
            listing = {
                'token': widget_data.get('token', ''),
                'title': widget_data.get('title', ''),
                'price': None,
                'price_per_sqm': None,
                'area': None,
                'rooms': None,
                'district': 'دروازه شمیران',
                'neighborhood': 'darvazeh-shemiran',
                'url': f"https://divar.ir/v/{widget_data.get('token', '')}" if widget_data.get('token') else None,
                'latitude': None,
                'longitude': None,
            }

            # Extract price from top_description_text
            if 'top_description_text' in widget_data:
                price_text = widget_data['top_description_text']
                listing['price'] = self.extract_price(price_text)

            # Extract details from middle_description_text
            if 'middle_description_text' in widget_data:
                desc_text = widget_data['middle_description_text']

                # Extract area
                area_match = re.search(r'(\d+)\s*متر', desc_text)
                if area_match:
                    listing['area'] = float(area_match.group(1))

                # Extract rooms
                room_match = re.search(r'(\d+)\s*اتاق', desc_text)
                if room_match:
                    listing['rooms'] = int(room_match.group(1))

            # Calculate price per sqm
            if listing['price'] and listing['area'] and listing['area'] > 0:
                listing['price_per_sqm'] = listing['price'] / listing['area']

            return listing if listing['token'] else None

        except Exception as e:
            print(f"Error parsing widget: {e}")
            return None

    def extract_price(self, text):
        """Extract numeric price from Persian text"""
        if not text:
            return None

        try:
            # Remove 'تومان' and commas
            text = text.replace('تومان', '').replace(',', '').strip()

            # Handle millions (میلیون)
            if 'میلیون' in text:
                num_match = re.search(r'([\d.]+)', text)
                if num_match:
                    return float(num_match.group(1)) * 1000000

            # Handle billions (میلیارد)
            if 'میلیارد' in text:
                num_match = re.search(r'([\d.]+)', text)
                if num_match:
                    return float(num_match.group(1)) * 1000000000

            # Direct number
            num_match = re.search(r'([\d]+)', text)
            if num_match:
                return float(num_match.group(1))

        except Exception as e:
            print(f"Error extracting price from '{text}': {e}")

        return None

    def parse_html_fallback(self, html_content):
        """Fallback method using BeautifulSoup if JSON extraction fails"""
        listings = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # This is a basic fallback - you may need to adjust selectors based on actual HTML structure
            # For now, we'll return empty as we'd need to inspect the actual HTML
            print("Using HTML fallback parser...")

        except Exception as e:
            print(f"Error in HTML fallback: {e}")

        return listings

    def save_listings(self, listings: List[Dict]):
        """Save listings to database"""
        if not listings:
            print("No listings to save")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_count = 0
        for listing in listings:
            if not listing.get('price'):
                continue

            try:
                # Insert or update listing
                cursor.execute('''
                    INSERT OR IGNORE INTO listings (
                        listing_token, title, price, price_per_sqm, area, rooms, district, neighborhood,
                        url, latitude, longitude
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    listing['token'],
                    listing['title'],
                    listing['price'],
                    listing['price_per_sqm'],
                    listing['area'],
                    listing['rooms'],
                    listing.get('district'),
                    listing.get('neighborhood'),
                    listing.get('url'),
                    listing.get('latitude'),
                    listing.get('longitude')
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

                saved_count += 1

            except Exception as e:
                print(f"Error saving listing: {e}")
                continue

        conn.commit()

        # Calculate daily statistics
        try:
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
        except Exception as e:
            print(f"Error calculating stats: {e}")

        conn.close()

        print(f"Saved {saved_count} listings to database")

    def run(self, neighborhood='darvazeh-shemiran'):
        """Run the scraper"""
        print(f"Starting scrape for {neighborhood}...")
        listings = self.scrape_listings(neighborhood=neighborhood)
        print(f"Found {len(listings)} listings")

        if listings:
            self.save_listings(listings)
            print("Data saved successfully")
        else:
            print("No listings found - this might be due to Divar's anti-scraping measures")
            print("Consider using the scraper at different times or with delays")

if __name__ == '__main__':
    scraper = DivarScraper()
    scraper.run()
