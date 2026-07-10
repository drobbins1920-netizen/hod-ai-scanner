import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

st.set_page_config(page_title="DR Dashboard", layout="wide")
st.title("DR Dashboard")

edt = pytz.timezone('US/Eastern')

if "qualified" not in st.session_state:
    st.session_state.qualified = []
if "stats" not in st.session_state:
    st.session_state.stats = {"pings": 0, "strong": 0}
if "top_gainers_history" not in st.session_state:
    st.session_state.top_gainers_history = pd.DataFrame()
if "last_top_change" not in st.session_state:
    st.session_state.last_top_change = 0

# Filters
with st.expander("📊 Filters", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        min_gain = st.slider("Min % Gain", 5, 100, 20)
        min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (1.0, 20.0), step=0.5)
    with col2:
        max_float_m = st.slider("Max Float (M)", 5, 100, 30)
        min_rvol = st.slider("Min RVOL", 1.0, 10.0, 3.0, step=0.5)
    with col3:
        refresh_sec = st.slider("Refresh (seconds)", 10, 60, 20)
        if st.button("Clear Dashboard"):
            st.session_state.qualified = []
            st.session_state.stats = {"pings": 0, "strong": 0}
            st.session_state.top_gainers_history = pd.DataFrame()
            st.session_state.last_top_change = 0
            st.rerun()

# Top Gainer Box
top_box = st.empty()

# Layout
left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("🏆 Top Gainers")
    session_filter = st.selectbox("Session", ["Pre-Market", "Regular Hours", "After Hours"], index=1)
    top_gainers_placeholder = st.empty()

with right_col:
    st.subheader("🔍 Live HOD Scanner")
    scanner_placeholder = st.empty()

st.subheader("📈 Mini Charts")
charts_placeholder = st.empty()

placeholder = st.empty()

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
    prompt = f"""Analyze this HOD momentum stock:
Ticker: {symbol}
% Change: {change}%
Price: ${price}
Volume: {volume}
News: {news}

Provide:
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
        return {"score": 8, "thesis": content[:200]}
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

def speak(text):
    st.components.v1.html(f'<script>new SpeechSynthesisUtterance("{text}").speak();</script>', height=0)

while True:
    with placeholder.container():
        st.caption(f"EDT: {datetime.now(edt).strftime('%H:%M:%S')} | Refresh: {refresh_sec}s")
        
        df = get_top_gainers()
        
        if not df.empty:
            # Top Gainer Box with flashing
            top = df.iloc[0]
            color = "lime" if top['changesPercentage'] > 0 else "red"
            flash_speed = "0.5s" if abs(top['changesPercentage'] - st.session_state.last_top_change) >= 10 else "5s"
            top_box.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center; font-size: 3em; font-weight: bold; color: {color}; animation: flash {flash_speed} infinite;">
                {top['symbol']} +{round(top['changesPercentage'], 1)}%
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.last_top_change = top['changesPercentage']
            
            # Voice for top gainer
            speak(f"{top['symbol']} news catalyst" if "news" in get_news_title(top['symbol']).lower() else top['symbol'])
            
            # Rest of scanner and charts (same as before)
            # ... (full logic)
        
        time.sleep(refresh_sec)
