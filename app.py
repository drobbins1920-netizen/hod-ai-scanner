import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"

st.set_page_config(page_title="Live HOD Scanner", layout="wide")
st.title("🚀 Live HOD Momentum Scanner")
st.caption("Newest matches appear at the top • Auto-refresh every 20s • Premium Plan")

# === SIDEBAR FILTERS ===
with st.sidebar:
    st.header("Filters (Adjust Live)")
    
    min_gain = st.slider("Minimum % Gain", 5, 100, 20)
    min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (1.0, 20.0), step=0.5)
    max_float_m = st.slider("Max Float (Millions)", 5, 100, 30)
    min_rvol = st.slider("Minimum RVOL (approx)", 1.0, 10.0, 3.0, step=0.5)
    
    refresh_seconds = st.slider("Auto-refresh (seconds)", 10, 60, 20)
    
    if st.button("Clear List"):
        st.session_state.qualified = []
        st.rerun()

# Initialize session state for rolling list
if "qualified" not in st.session_state:
    st.session_state.qualified = []

# === FUNCTIONS ===
def get_top_gainers():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    try:
        return pd.DataFrame(requests.get(url, timeout=15).json())
    except:
        return pd.DataFrame()

def get_news_title(symbol):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=1&apikey={API_KEY}"
    try:
        data = requests.get(url, timeout=8).json()
        return data[0]['title'] if data else "No recent news"
    except:
        return "News unavailable"

# === MAIN AUTO LOOP ===
placeholder = st.empty()

while True:
    with placeholder.container():
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto every {refresh_seconds}s")
        
        df = get_top_gainers()
        
        if not df.empty:
            # Apply current filters
            current_matches = df[
                (df['changesPercentage'] >= min_gain) &
                (df['price'].between(min_price, max_price))
            ].copy()
            
            # Add new matches to the top of the rolling list
            for _, row in current_matches.iterrows():
                symbol = row['symbol']
                price = round(row['price'], 2)
                change = round(row['changesPercentage'], 2)
                volume = int(row['volume'])
                
                # Simple RVOL approximation (you can improve later with historical data)
                rvol = round(volume / 500000, 1)   # rough proxy
                
                # Skip if already in list or doesn't meet RVOL/float
                if any(item['Ticker'] == symbol for item in st.session_state.qualified):
                    continue
                if rvol < min_rvol:
                    continue
                
                # Get float (light check)
                try:
                    float_data = requests.get(
                        f"https://financialmodelingprep.com/api/v3/shares-float?symbol={symbol}&apikey={API_KEY}",
                        timeout=6
                    ).json()
                    float_val = float_data[0].get('freeFloat', 999999999) / 1_000_000 if float_data else 999
                except:
                    float_val = 999
                
                if float_val > max_float_m:
                    continue
                
                news_title = get_news_title(symbol)
                
                new_item = {
                    "Ticker": symbol,
                    "Price": price,
                    "% Gain": change,
                    "Volume": f"{volume:,}",
                    "Float (M)": round(float_val, 1),
                    "RVOL (approx)": rvol,
                    "News Catalyst": news_title[:90] + "..." if len(news_title) > 90 else news_title,
                    "Time": datetime.now().strftime("%H:%M:%S")
                }
                
                # Add to top of list
                st.session_state.qualified.insert(0, new_item)
            
            # Keep only the last 20 entries (rolling effect)
            st.session_state.qualified = st.session_state.qualified[:20]
        
        # Display the rolling table
        if st.session_state.qualified:
            display_df = pd.DataFrame(st.session_state.qualified)
            st.dataframe(display_df, use_container_width=True, height=600)
        else:
            st.info("Waiting for stocks that match your current filters...")
        
        time.sleep(refresh_seconds)
