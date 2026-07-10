import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"

st.set_page_config(page_title="Live HOD Scanner", layout="wide")
st.title("🚀 Live HOD Momentum Scanner")
st.caption("Newest at top • Click tickers for charts • Sound on strong matches")

# Sidebar Filters
with st.sidebar:
    st.header("Live Filters")
    min_gain = st.slider("Min % Gain", 5, 100, 20)
    min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (1.0, 20.0), step=0.5)
    max_float_m = st.slider("Max Float (M)", 5, 100, 30)
    min_rvol = st.slider("Min RVOL (approx)", 1.0, 10.0, 3.0, step=0.5)
    refresh_sec = st.slider("Refresh (seconds)", 10, 60, 20)
    
    if st.button("Clear List"):
        if "qualified" in st.session_state:
            st.session_state.qualified = []
        st.rerun()

# Session State for rolling list
if "qualified" not in st.session_state:
    st.session_state.qualified = []

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
        return data[0]['title'] if data else "No news"
    except:
        return "News unavailable"

def play_sound():
    st.components.v1.html("""
        <audio autoplay>
            <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
        </audio>
    """, height=0)

placeholder = st.empty()

while True:
    with placeholder.container():
        st.caption(f"Last scan: {datetime.now().strftime('%H:%M:%S')} | Every {refresh_sec}s")
        
        df = get_top_gainers()
        
        if not df.empty:
            candidates = df[
                (df['changesPercentage'] >= min_gain) &
                (df['price'].between(min_price, max_price))
            ].copy()
            
            for _, row in candidates.iterrows():
                symbol = row['symbol']
                if any(item.get('Ticker') == symbol for item in st.session_state.qualified):
                    continue
                
                # Rough RVOL
                rvol = round(row['volume'] / 500000, 1)
                if rvol < min_rvol:
                    continue
                
                # Float check
                try:
                    fdata = requests.get(f"https://financialmodelingprep.com/api/v3/shares-float?symbol={symbol}&apikey={API_KEY}", timeout=6).json()
                    float_m = fdata[0].get('freeFloat', 999999999) / 1_000_000 if fdata else 999
                except:
                    float_m = 999
                if float_m > max_float_m:
                    continue
                
                news = get_news_title(symbol)
                
                new_item = {
                    "Ticker": f"[{symbol}](https://finance.yahoo.com/quote/{symbol})",
                    "Price": round(row['price'], 2),
                    "% Gain": round(row['changesPercentage'], 2),
                    "Volume": f"{int(row['volume']):,}",
                    "Float (M)": round(float_m, 1),
                    "RVOL": rvol,
                    "News": news[:80] + "..." if len(news) > 80 else news,
                    "Time": datetime.now().strftime("%H:%M:%S")
                }
                
                st.session_state.qualified.insert(0, new_item)
                
                # Sound ping for strong moves
                if row['changesPercentage'] >= 30:
                    play_sound()
                    st.success(f"🚨 STRONG PING: {symbol} +{new_item['% Gain']}%")
        
        # Trim list
        st.session_state.qualified = st.session_state.qualified[:20]
        
        # Display
        if st.session_state.qualified:
            display_df = pd.DataFrame(st.session_state.qualified)
            st.dataframe(display_df, use_container_width=True, height=650)
        else:
            st.info("Scanning... No matches yet with current filters.")
        
        time.sleep(refresh_sec)
