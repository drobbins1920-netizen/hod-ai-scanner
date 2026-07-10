import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"   # ← Paste your new Premium key

st.set_page_config(page_title="Auto HOD Scanner (Premium)", layout="wide")
st.title("🚀 Automatic HOD Momentum Scanner")
st.caption("Premium Plan | Auto-refresh every 20 seconds | Your criteria")

# Your criteria (easy to edit)
MIN_CHANGE = 20          # %
MIN_RVOL = 3
MAX_FLOAT_M = 30         # million
MIN_PRICE = 1
MAX_PRICE = 20

def get_top_gainers():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    try:
        return pd.DataFrame(requests.get(url, timeout=15).json())
    except:
        return pd.DataFrame()

placeholder = st.empty()

while True:
    with placeholder.container():
        st.caption(f"Last scan: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every 20s")
        
        df = get_top_gainers()
        
        if not df.empty:
            # Apply your filters
            filtered = df[
                (df['changesPercentage'] >= MIN_CHANGE) &
                (df['price'].between(MIN_PRICE, MAX_PRICE))
            ].copy()
            
            if not filtered.empty:
                st.success(f"Found {len(filtered)} potential HOD movers")
                st.dataframe(filtered[['symbol', 'price', 'changesPercentage', 'volume']].head(15), 
                             use_container_width=True)
                
                # Simple alert for strongest ones
                top = filtered[filtered['changesPercentage'] >= 30]
                if not top.empty:
                    for _, row in top.iterrows():
                        st.warning(f"🚨 STRONG MOVE: {row['symbol']} +{round(row['changesPercentage'],1)}%")
            else:
                st.info("No stocks currently matching your criteria.")
        else:
            st.error("No data — check your Premium key or try again.")
        
        time.sleep(20)   # ← Change this number for different timing (15–30 recommended)
