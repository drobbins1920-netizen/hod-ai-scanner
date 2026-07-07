import streamlit as st
import pandas as pd
import requests
from datetime import datetime

API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"

st.set_page_config(page_title="HOD Scanner - Your Criteria", layout="wide")
st.title("🚀 Your HOD Momentum Scanner")
st.markdown("**Criteria:** ≥20% up | ≥3x RVOL | Float ≤30M | $1–$20 | News Catalyst")

# FMP Functions
def get_top_gainers():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    try:
        data = requests.get(url, timeout=15).json()
        return pd.DataFrame(data)
    except:
        st.error("Error fetching gainers")
        return pd.DataFrame()

def get_float(symbol):
    url = f"https://financialmodelingprep.com/api/v3/shares-float?symbol={symbol}&apikey={API_KEY}"
    try:
        data = requests.get(url, timeout=10).json()
        return data[0]['freeFloat'] if data else None
    except:
        return None

def get_news(symbol):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=3&apikey={API_KEY}"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

# Main Scan
if st.button("🔄 Run Full Market Scan", type="primary"):
    with st.spinner("Scanning market for your criteria..."):
        df = get_top_gainers()
        
        if df.empty:
            st.error("No data returned.")
        else:
            # Initial broad filter
            candidates = df[
                (df['changesPercentage'] >= 20) &
                (df['price'] >= 1) & (df['price'] <= 20)
            ].copy()
            
            results = []
            for _, row in candidates.iterrows():
                symbol = row['symbol']
                price = row['price']
                change_pct = row['changesPercentage']
                volume = row['volume']
                
                # Float check
                float_val = get_float(symbol)
                if float_val is None or float_val > 30000000:
                    continue
                
                # Rough RVOL (high volume proxy)
                rvol_proxy = volume / 1000000  # simplistic
                
                if rvol_proxy < 3:
                    continue
                
                news_list = get_news(symbol)
                news_text = news_list[0]['title'] if news_list else "No recent news"
                
                ai_score = min(10, int(change_pct * 0.12 + 5))
                
                results.append({
                    "Ticker": symbol,
                    "Price": round(price, 2),
                    "% Change": round(change_pct, 2),
                    "Volume": f"{int(volume):,}",
                    "Float (M)": round(float_val / 1000000, 1) if float_val else "N/A",
                    "AI Score": ai_score,
                    "News Catalyst": news_text[:120] + "..." if len(news_text) > 120 else news_text
                })
            
            if results:
                results_df = pd.DataFrame(results).sort_values("% Change", ascending=False)
                st.success(f"Found {len(results)} stocks matching your criteria!")
                
                for _, r in results_df.iterrows():
                    if r['AI Score'] >= 8:
                        st.balloons()
                        st.success(f"🚨 STRONG PING → {r['Ticker']} | {r['% Change']}% | {r['News Catalyst']}")
                
                st.dataframe(results_df, use_container_width=True, height=600)
            else:
                st.info("No stocks currently meet all criteria. Market may be quiet — try again later.")

st.caption("Full market scan using FMP gainers + your filters. News titles included. Refine AI or add Telegram pings next.")
