# Deployment Guide

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `divar-price-tracker`
3. Description: `Real estate price tracker for Divar.ir apartments`
4. Make it **Public** (required for free Streamlit Cloud hosting)
5. Do NOT initialize with README (we already have files)
6. Click "Create repository"

## Step 2: Push Code to GitHub

Run these commands in the terminal:

```bash
cd /Users/mahdihasanzadeh/Desktop/divar-price-tracker

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/divar-price-tracker.git

# Push to GitHub
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 3: Deploy to Streamlit Cloud (FREE)

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Connect your GitHub account (if not already connected)
4. Select:
   - Repository: `YOUR_USERNAME/divar-price-tracker`
   - Branch: `main`
   - Main file path: `dashboard.py`
5. Click "Deploy!"

**Your app will be live at:** `https://YOUR_USERNAME-divar-price-tracker.streamlit.app`

## Step 4: Set Up Automated Data Collection

### Option A: GitHub Actions (Free, Recommended for deployed app)

Create `.github/workflows/scrape.yml`:

```yaml
name: Daily Scrape

on:
  schedule:
    - cron: '0 6 * * *'  # Runs daily at 6 AM UTC (9:30 AM Iran time)
  workflow_dispatch:  # Allows manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run scraper
        run: python scraper.py
      - name: Commit database
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add price_data.db
          git commit -m "Update price data" || exit 0
          git push
```

**Note:** You'll need to remove `*.db` from `.gitignore` first.

### Option B: Local Scheduled Task (If running on your own server)

**macOS/Linux - Using cron:**
```bash
crontab -e
# Add this line:
0 9 * * * cd /Users/mahdihasanzadeh/Desktop/divar-price-tracker && python scraper.py
```

**Or run the scheduler continuously:**
```bash
python scheduler.py
```

## Alternative: Deploy to Render (Free)

1. Go to https://render.com/
2. Sign up/login
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Settings:
   - Name: `divar-price-tracker`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0`
6. Click "Create Web Service"

## Alternative: Deploy to Railway (Free)

1. Go to https://railway.app/
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect and deploy

## Troubleshooting

**Database is empty on deployed app:**
- The scraper needs to run at least once
- Click "Refresh Data Now" button in the sidebar
- Or wait for scheduled scraping to run

**App crashes on deployment:**
- Check Streamlit Cloud logs
- Make sure all dependencies are in requirements.txt
- Database will be created automatically on first run

**Data not persisting between deployments:**
- For Streamlit Cloud, you need to commit the database file to git
- Remove `*.db` from `.gitignore`
- Commit and push: `git add price_data.db && git commit -m "Add database" && git push`

## Quick Deploy Command

```bash
# Run this after creating GitHub repo
cd /Users/mahdihasanzadeh/Desktop/divar-price-tracker
git remote add origin https://github.com/YOUR_USERNAME/divar-price-tracker.git
git push -u origin main

# Then go to share.streamlit.io and deploy!
```

## Your URLs After Deployment

- **Streamlit Cloud:** `https://YOUR_USERNAME-divar-price-tracker.streamlit.app`
- **Render:** `https://divar-price-tracker.onrender.com`
- **Railway:** Provided after deployment
