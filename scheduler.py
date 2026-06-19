import schedule
import time
from scraper import DivarScraper
from datetime import datetime

def job():
    """Daily scraping job"""
    print(f"\n{'='*50}")
    print(f"Running daily scrape at {datetime.now()}")
    print(f"{'='*50}\n")

    scraper = DivarScraper()
    scraper.run(neighborhood='darvazeh-shemiran')

    print(f"\n{'='*50}")
    print(f"Scrape completed at {datetime.now()}")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    print("Divar Price Tracker Scheduler Started")
    print("Running initial scrape...")

    # Run immediately on start
    job()

    # Schedule daily runs at 9:00 AM
    schedule.every().day.at("09:00").do(job)

    print("\nScheduler is running. Press Ctrl+C to stop.")
    print("Daily scrapes scheduled for 09:00 AM")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
