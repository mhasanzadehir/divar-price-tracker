# Divar Real Estate Price Tracker

Track apartment prices from Divar.ir over time and visualize price trends with an interactive dashboard.

## Features

- **Automated Daily Scraping**: Collects apartment listings from Divar automatically
- **Historical Price Tracking**: Stores price data in SQLite database for trend analysis
- **Interactive Dashboard**: Beautiful web interface with charts showing:
  - Average and median price trends over time
  - Price per square meter trends
  - Number of listings over time
  - Price distribution histograms
  - Current listings table

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Run Initial Scrape

First, collect some initial data:

```bash
python scraper.py
```

This will scrape current listings from Divar for the Darvazeh Shemiran area and store them in the database.

### 2. View Dashboard

Launch the dashboard to see your data:

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at http://localhost:8501

### 3. Set Up Daily Automated Scraping

To automatically collect data every day:

```bash
python scheduler.py
```

This will:
- Run an initial scrape immediately
- Schedule daily scrapes at 9:00 AM
- Keep running until you stop it (Ctrl+C)

**For production**: Use a process manager or system service to keep the scheduler running:

#### Using cron (macOS/Linux):
```bash
# Edit crontab
crontab -e

# Add this line to run scraper daily at 9 AM
0 9 * * * cd /Users/mahdihasanzadeh/Desktop/divar-price-tracker && python scraper.py
```

#### Using launchd (macOS):
Create a plist file at `~/Library/LaunchAgents/com.divar.scraper.plist`

## Database Structure

The application uses SQLite with three tables:

- **listings**: Stores unique apartment listings
- **price_history**: Tracks price changes over time
- **daily_stats**: Aggregated daily statistics (avg, median, min, max prices)

## Customization

### Change Neighborhood

Edit `scraper.py` or `scheduler.py` and modify the `neighborhood` parameter:

```python
scraper.run(neighborhood='your-neighborhood-name')
```

### Adjust Scraping Frequency

In `scheduler.py`, change the schedule:

```python
# Run every 12 hours
schedule.every(12).hours.do(job)

# Run at specific time
schedule.every().day.at("21:00").do(job)
```

## Dashboard Features

- **Summary Metrics**: Quick overview of latest prices
- **Interactive Charts**: Hover for detailed information
- **Time Range Selector**: Choose how many days to display (7-90 days)
- **Multiple Views**:
  - Average Price trends
  - Price per m² trends
  - Listing count over time
  - Price distributions
- **Listings Table**: Browse current apartments with all details

## Notes

- The scraper is respectful to Divar's servers with built-in delays
- Data is stored locally in `price_data.db`
- Run the scraper daily for best trend visualization
- More historical data = better insights

## Troubleshooting

**No data showing on dashboard?**
- Run `python scraper.py` first to collect initial data

**Scraper not finding listings?**
- Check your internet connection
- Verify the neighborhood parameter is correct
- Divar's API may have changed (check console for errors)

**Dashboard not updating?**
- Refresh the browser page
- Make sure scraper has run recently
