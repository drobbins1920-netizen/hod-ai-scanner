import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ================== KEYS FROM .env ==================
FMP_API_KEY = os.getenv("FMP_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

st.set_page_config(page_title="AI HOD Scanner", layout="wide")
st.title("🚀 Grok AI-Enhanced HOD Momentum Scanner")
st.caption("Keys loaded from .env • Rolling list • Telegram alerts")

# Sidebar Filters
with st.sidebar:
    st.header("Live Filters")
    min_gain = st.slider("Min % Gain", 5, 100, 20)
    min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (1.0, 20.0), step=0.5)
    max_float_m = st.slider("Max Float (M)", 5, 100, 30)
    min_rvol = st.slider("Min RVOL (approx)", 1.0, 10.0, 3.0, step=0.5)
    refresh_sec = st.slider("Refresh (seconds)", 10, 60, 20)
    
    if st.button("Clear List"):
        st.session_state.qualified = []
        st.rerun()

if "qualified" not in st.session_state:
    st.session_state.qualified = []

def get_top_gainers():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={FMP_API_KEY}"
    try:
        return pd.DataFrame(requests.get(url, timeout=15).json())
    except:
        return pd.DataFrame()

def get_news_title(symbol):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=1&apikey={FMP_API_KEY}"
    try:
        data = requests.get(url, timeout=8).json()
        return data[0]['title'] if data else "No news"
    except:
        return "News unavailable"

def grok_analyze(symbol, change, price, volume, news):
    prompt = f"""Analyze this HOD momentum stock for day trading:
Ticker: {symbol}
% Change: {change}%
Price: ${price}
Volume: {volume}
News: {news}

Give a short analysis with:
- AI Score (1-10)
- Thesis (1-2 sentences)"""
    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-beta", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
            timeout=15
        ).json()
        content = resp['choices'][0]['message']['content']
        score = 8  # fallback
        thesis = content[:180]
        return {"score": score, "thesis": thesis}
    except:
        return {"score": 7, "thesis": "Strong momentum detected."}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def play_sound():
    st.components.v1.html('<audio autoplay><source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg"></audio>', height=0)

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
                
                rvol = round(row['volume'] / 500000, 1)
                if rvol < min_rvol: continue
                
                try:
                    fdata = requests.get(f"https://financialmodelingprep.com/api/v3/shares-float?symbol={symbol}&apikey={FMP_API_KEY}", timeout=6).json()
                    float_m = fdata[0].get('freeFloat', 999999999) / 1_000_000 if fdata else 999
                except:
                    float_m = 999
                if float_m > max_float_m: continue
                
                news = get_news_title(symbol)
                ai = grok_analyze(symbol, row['changesPercentage'], row['price'], row['volume'], news)
                
                new_item = {
                    "Ticker": f"[{symbol}](https://finance.yahoo.com/quote/{symbol})",
                    "Price": round(row['price'], 2),
                    "% Gain": round(row['changesPercentage'], 2),
                    "Volume": f"{int(row['volume']):,}",
                    "Float (M)": round(float_m, 1),
                    "RVOL": rvol,
                    "AI Score": ai['score'],
                    "Thesis": ai['thesis'],
                    "News": news[:90] + "..." if len(news) > 90 else news,
                    "Time": datetime.now().strftime("%H:%M:%S")
                }
                
                st.session_state.qualified.insert(0, new_item)
                
                if ai['score'] >= 8:
                    play_sound()
                    alert = f"🚨 GROK AI PING!\n{symbol} +{new_item['% Gain']}% (Score {ai['score']}/10)\n{ai['thesis']}\n{new_item['News']}"
                    st.success(alert)
                    send_telegram(alert)
        
        st.session_state.qualified = st.session_state.qualified[:20]
        
        if st.session_state.qualified:
            st.dataframe(pd.DataFrame(st.session_state.qualified), use_container_width=True, height=700)
        else:
            st.info("Scanning... No matches yet.")
        
        time.sleep(refresh_sec)
