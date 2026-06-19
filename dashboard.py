import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from scraper import DivarScraper

class PriceDashboard:
    def __init__(self, db_path='price_data.db'):
        self.db_path = db_path
        self.ensure_database_exists()

    def ensure_database_exists(self):
        """Ensure database exists and has initial data"""
        if not os.path.exists(self.db_path):
            scraper = DivarScraper(self.db_path)
            # Database will be created automatically

    def get_daily_stats(self):
        """Get daily statistics from database"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT
                date,
                avg_price,
                median_price,
                avg_price_per_sqm,
                median_price_per_sqm,
                total_listings,
                min_price,
                max_price
            FROM daily_stats
            ORDER BY date ASC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])

        return df

    def get_price_history(self, days=30):
        """Get price history for recent days"""
        conn = sqlite3.connect(self.db_path)
        query = f'''
            SELECT
                DATE(scraped_at) as date,
                price,
                price_per_sqm,
                listing_token
            FROM price_history
            WHERE scraped_at >= datetime('now', '-{days} days')
            ORDER BY scraped_at DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])

        return df

    def get_current_listings(self, filters=None):
        """Get current listings with optional filters"""
        conn = sqlite3.connect(self.db_path)

        where_clauses = []
        params = []

        if filters:
            if filters.get('min_price'):
                where_clauses.append("l.price >= ?")
                params.append(filters['min_price'])

            if filters.get('max_price'):
                where_clauses.append("l.price <= ?")
                params.append(filters['max_price'])

            if filters.get('min_area'):
                where_clauses.append("l.area >= ?")
                params.append(filters['min_area'])

            if filters.get('max_area'):
                where_clauses.append("l.area <= ?")
                params.append(filters['max_area'])

            if filters.get('rooms') and len(filters['rooms']) > 0:
                placeholders = ','.join('?' * len(filters['rooms']))
                where_clauses.append(f"l.rooms IN ({placeholders})")
                params.extend(filters['rooms'])

            if filters.get('min_age') is not None:
                where_clauses.append("l.building_age >= ?")
                params.append(filters['min_age'])

            if filters.get('max_age') is not None:
                where_clauses.append("l.building_age <= ?")
                params.append(filters['max_age'])

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f'''
            SELECT
                l.title,
                l.price,
                l.price_per_sqm,
                l.area,
                l.rooms,
                l.building_age,
                l.neighborhood,
                MAX(ph.scraped_at) as last_seen
            FROM listings l
            LEFT JOIN price_history ph ON l.listing_token = ph.listing_token
            {where_sql}
            GROUP BY l.listing_token
            ORDER BY last_seen DESC
            LIMIT 100
        '''

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_filter_stats(self):
        """Get min/max values for filters"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT
                MIN(price) as min_price,
                MAX(price) as max_price,
                MIN(area) as min_area,
                MAX(area) as max_area,
                MIN(building_age) as min_age,
                MAX(building_age) as max_age,
                MIN(rooms) as min_rooms,
                MAX(rooms) as max_rooms
            FROM listings
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    def run(self):
        """Run the Streamlit dashboard"""
        st.set_page_config(
            page_title="Divar Price Tracker - دروازه شمیران",
            page_icon="🏘️",
            layout="wide"
        )

        st.title("📊 Divar Real Estate Price Dashboard")
        st.markdown("### دروازه شمیران - Tehran Apartment Prices")

        # Sidebar - Settings
        st.sidebar.header("⚙️ Settings")
        days_to_show = st.sidebar.slider("Days to display", 7, 90, 30)

        # Add manual refresh button
        if st.sidebar.button("🔄 Refresh Data Now"):
            with st.spinner("Scraping latest data..."):
                scraper = DivarScraper(self.db_path)
                scraper.run(neighborhood='darvazeh-shemiran')
                st.sidebar.success("Data refreshed!")
                st.rerun()

        # Get filter stats for dynamic ranges
        filter_stats = self.get_filter_stats()

        # Sidebar - Filters
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Filters")

        filters = {}

        if filter_stats:
            # Price filters
            st.sidebar.subheader("💰 Price Range (تومان)")
            min_price_input = st.sidebar.number_input(
                "Min Price",
                min_value=0,
                max_value=int(filter_stats['max_price']) if filter_stats['max_price'] else 100000000000,
                value=0,
                step=1000000000,
                format="%d",
                help="Minimum price in Toman"
            )
            max_price_input = st.sidebar.number_input(
                "Max Price",
                min_value=0,
                max_value=int(filter_stats['max_price']) if filter_stats['max_price'] else 100000000000,
                value=int(filter_stats['max_price']) if filter_stats['max_price'] else 100000000000,
                step=1000000000,
                format="%d",
                help="Maximum price in Toman"
            )

            if min_price_input > 0:
                filters['min_price'] = min_price_input
            if max_price_input < (filter_stats['max_price'] or 100000000000):
                filters['max_price'] = max_price_input

            # Area filters
            st.sidebar.subheader("📏 Area (متر مربع)")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                min_area = st.number_input(
                    "Min m²",
                    min_value=0,
                    max_value=int(filter_stats['max_area']) if filter_stats['max_area'] else 500,
                    value=0,
                    step=10,
                    help="Minimum area in square meters"
                )
            with col2:
                max_area = st.number_input(
                    "Max m²",
                    min_value=0,
                    max_value=int(filter_stats['max_area']) if filter_stats['max_area'] else 500,
                    value=int(filter_stats['max_area']) if filter_stats['max_area'] else 500,
                    step=10,
                    help="Maximum area in square meters"
                )

            if min_area > 0:
                filters['min_area'] = min_area
            if max_area < (filter_stats['max_area'] or 500):
                filters['max_area'] = max_area

            # Rooms filter
            st.sidebar.subheader("🛏️ Number of Rooms")
            rooms_options = st.sidebar.multiselect(
                "Select rooms",
                options=[1, 2, 3, 4, 5],
                default=None,
                help="Filter by number of bedrooms"
            )
            if rooms_options:
                filters['rooms'] = rooms_options

            # Building age filter
            st.sidebar.subheader("🏗️ Building Age (years)")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                min_age = st.number_input(
                    "Min age",
                    min_value=0,
                    max_value=int(filter_stats['max_age']) if filter_stats['max_age'] else 50,
                    value=0,
                    step=1,
                    help="Minimum building age in years"
                )
            with col2:
                max_age = st.number_input(
                    "Max age",
                    min_value=0,
                    max_value=int(filter_stats['max_age']) if filter_stats['max_age'] else 50,
                    value=int(filter_stats['max_age']) if filter_stats['max_age'] else 50,
                    step=1,
                    help="Maximum building age in years"
                )

            if min_age > 0:
                filters['min_age'] = min_age
            if max_age < (filter_stats['max_age'] or 50):
                filters['max_age'] = max_age

            # Clear filters button
            if st.sidebar.button("🗑️ Clear All Filters"):
                st.rerun()

        # Get data with filters
        daily_stats = self.get_daily_stats()
        price_history = self.get_price_history(days=days_to_show)
        current_listings = self.get_current_listings(filters=filters if filters else None)

        # Summary metrics
        if not daily_stats.empty:
            latest = daily_stats.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Average Price",
                    f"{latest['avg_price']:,.0f} تومان",
                    delta=None
                )

            with col2:
                st.metric(
                    "Median Price",
                    f"{latest['median_price']:,.0f} تومان",
                    delta=None
                )

            with col3:
                st.metric(
                    "Avg Price/m²",
                    f"{latest['avg_price_per_sqm']:,.0f} تومان",
                    delta=None
                )

            with col4:
                st.metric(
                    "Total Listings",
                    f"{int(latest['total_listings'])}",
                    delta=None
                )

        # Price trends over time
        st.header("📈 Price Trends Over Time")

        if not daily_stats.empty and len(daily_stats) > 1:
            tab1, tab2, tab3 = st.tabs(["Average Price", "Price per m²", "Listing Count"])

            with tab1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_stats['date'],
                    y=daily_stats['avg_price'],
                    mode='lines+markers',
                    name='Average Price',
                    line=dict(color='#2E86AB', width=3)
                ))
                fig.add_trace(go.Scatter(
                    x=daily_stats['date'],
                    y=daily_stats['median_price'],
                    mode='lines+markers',
                    name='Median Price',
                    line=dict(color='#A23B72', width=3)
                ))
                fig.update_layout(
                    title="Average and Median Prices Over Time",
                    xaxis_title="Date",
                    yaxis_title="Price (تومان)",
                    hovermode='x unified',
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_stats['date'],
                    y=daily_stats['avg_price_per_sqm'],
                    mode='lines+markers',
                    name='Avg Price/m²',
                    line=dict(color='#F18F01', width=3)
                ))
                fig.add_trace(go.Scatter(
                    x=daily_stats['date'],
                    y=daily_stats['median_price_per_sqm'],
                    mode='lines+markers',
                    name='Median Price/m²',
                    line=dict(color='#C73E1D', width=3)
                ))
                fig.update_layout(
                    title="Price per Square Meter Over Time",
                    xaxis_title="Date",
                    yaxis_title="Price per m² (تومان)",
                    hovermode='x unified',
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=daily_stats['date'],
                    y=daily_stats['total_listings'],
                    name='Total Listings',
                    marker_color='#06A77D'
                ))
                fig.update_layout(
                    title="Number of Listings Over Time",
                    xaxis_title="Date",
                    yaxis_title="Number of Listings",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Not enough historical data yet. Run the scraper daily to build up price trends.")

        # Price distribution
        if not price_history.empty:
            st.header("📊 Price Distribution")

            col1, col2 = st.columns(2)

            with col1:
                fig = px.histogram(
                    price_history,
                    x='price',
                    nbins=30,
                    title='Distribution of Apartment Prices',
                    labels={'price': 'Price (تومان)', 'count': 'Number of Listings'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.histogram(
                    price_history.dropna(subset=['price_per_sqm']),
                    x='price_per_sqm',
                    nbins=30,
                    title='Distribution of Price per m²',
                    labels={'price_per_sqm': 'Price per m² (تومان)', 'count': 'Number of Listings'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

        # Current listings
        st.header("🏘️ Current Listings")

        # Show active filters summary
        if filters:
            filter_summary = []
            if 'min_price' in filters:
                filter_summary.append(f"Min Price: {filters['min_price']:,.0f}")
            if 'max_price' in filters:
                filter_summary.append(f"Max Price: {filters['max_price']:,.0f}")
            if 'min_area' in filters:
                filter_summary.append(f"Min Area: {filters['min_area']}m²")
            if 'max_area' in filters:
                filter_summary.append(f"Max Area: {filters['max_area']}m²")
            if 'rooms' in filters:
                filter_summary.append(f"Rooms: {', '.join(map(str, filters['rooms']))}")
            if 'min_age' in filters:
                filter_summary.append(f"Min Age: {filters['min_age']} years")
            if 'max_age' in filters:
                filter_summary.append(f"Max Age: {filters['max_age']} years")

            if filter_summary:
                st.info(f"🔍 Active Filters: {' | '.join(filter_summary)}")

        if not current_listings.empty:
            st.success(f"Found {len(current_listings)} listings")

            # Format the dataframe for display
            display_df = current_listings.copy()
            display_df['price'] = display_df['price'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")
            display_df['price_per_sqm'] = display_df['price_per_sqm'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")
            display_df['area'] = display_df['area'].apply(lambda x: f"{x:.0f}" if pd.notnull(x) else "N/A")
            display_df['building_age'] = display_df['building_age'].apply(lambda x: f"{x:.0f} years" if pd.notnull(x) else "N/A")

            st.dataframe(
                display_df,
                column_config={
                    "title": "Title",
                    "price": "Price (تومان)",
                    "price_per_sqm": "Price/m² (تومان)",
                    "area": "Area (m²)",
                    "rooms": "Rooms",
                    "building_age": "Building Age",
                    "neighborhood": "Neighborhood",
                    "last_seen": "Last Seen"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("No listings match your filters. Try adjusting the filter criteria.")

        # Footer
        st.markdown("---")
        st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    dashboard = PriceDashboard()
    dashboard.run()
