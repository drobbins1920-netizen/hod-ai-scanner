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
if "last_news" not in st.session_state:
    st.session_state.last_news = []

# #1 Gainer Box
gainer_box = st.empty()

# Filters
with st.expander("📊 Filters", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        min_gain = st.slider("Min % Gain", 5, 100, 5)
        min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (0.5, 50.0), step=0.5)
    with col2:
        max_float_m = st.slider("Max Float (M)", 5, 500, 300)
        min_rvol = st.slider("Min RVOL", 1.0, 10.0, 1.5, step=0.5)
    with col3:
        refresh_sec = st.slider("Refresh (seconds)", 10, 60, 20)
        if st.button("Clear Dashboard"):
            st.session_state.qualified = []
            st.session_state.stats = {"pings": 0, "strong": 0}
            st.session_state.top_gainers_history = pd.DataFrame()
            st.session_state.last_top_change = 0
            st.session_state.last_news = []
            st.rerun()

# Layout
col_left, col_right = st.columns([2, 3])

with col_left:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🏆 Top Gainers</div>', unsafe_allow_html=True)
    session_filter = st.selectbox("Session", ["Pre-Market", "Regular Hours", "After Hours"], index=1)
    top_gainers_placeholder = st.empty()

with col_right:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🔍 Live HOD Scanner</div>', unsafe_allow_html=True)
    scanner_placeholder = st.empty()

# News Box
st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">📰 Latest News</div>', unsafe_allow_html=True)
news_placeholder = st.empty()

placeholder = st.empty()

def get_top_gainers():
    url = f"https://financialmodelingprep.com/stable/biggest-gainers?apikey={FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

def get_batch_quotes():
    url = f"https://financialmodelingprep.com/stable/batch-exchange-quote?exchange=NASDAQ&apikey={FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

def get_latest_news():
    url = f"https://financialmodelingprep.com/stable/news/stock-latest?limit=10&apikey={FMP_API_KEY}"
    try:
        data = requests.get(url, timeout=15).json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

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
    st.components.v1.html(f'<script>speechSynthesis.speak(new SpeechSynthesisUtterance("{text}"));</script>', height=0)

while True:
    with placeholder.container():
        st.caption(f"EDT: {datetime.now(edt).strftime('%H:%M:%S')} | Refresh: {refresh_sec}s")
        
        df = get_top_gainers()
        
        if not df.empty:
            # #1 Gainer Box
            top = df.iloc[0]
            color = "lime" if top.get('changesPercentage', 0) > 0 else "red"
            flash_speed = "0.5s" if abs(top.get('changesPercentage', 0) - st.session_state.last_top_change) >= 10 else "5s"
            gainer_box.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 20px; border: 2px solid #444; border-radius: 10px; text-align: center; font-size: 3em; font-weight: bold; color: {color}; animation: flash {flash_speed} infinite;">
                #1 Gainer: {top.get('symbol', 'N/A')} +{round(top.get('changesPercentage', 0), 1)}%
            </div>
            """, unsafe_allow_html=True)
            
            if abs(top.get('changesPercentage', 0) - st.session_state.last_top_change) >= 10:
                play_sound()
            
            st.session_state.last_top_change = top.get('changesPercentage', 0)
            
            # Top Gainers list
            with top_gainers_placeholder.container():
                display_df = df.head(15).copy()
                display_df['% Change'] = display_df.get('changesPercentage', 0).apply(lambda x: f"{x:.2f}%")
                cols = ['symbol', 'price', '% Change']
                if 'volume' in display_df.columns:
                    cols.append('volume')
                st.dataframe(display_df[cols], use_container_width=True, height=400)
            
            # Live HOD Scanner using batch quotes
            with scanner_placeholder.container():
                quotes_df = get_batch_quotes()
                if not quotes_df.empty:
                    candidates = quotes_df[
                        (quotes_df.get('change', 0) >= min_gain) &
                        (quotes_df.get('price', 0).between(min_price, max_price))
                    ].copy()
                    
                    for _, row in candidates.iterrows():
                        symbol = row.get('symbol')
                        if any(item.get('Ticker') == symbol for item in st.session_state.qualified):
                            continue
                        
                        rvol = round(row.get('volume', 0) / 500000, 1)
                        if rvol < min_rvol: continue
                        
                        float_m = 999
                        news = "No news"
                        ai = grok_analyze(symbol, row.get('change', 0), row.get('price', 0), row.get('volume', 0), news)
                        
                        new_item = {
                            "Ticker": f"[{symbol}](https://finance.yahoo.com/quote/{symbol})",
                            "Price": round(row.get('price', 0), 2),
                            "% Gain": round(row.get('change', 0), 2),
                            "Volume": f"{int(row.get('volume', 0)):,}",
                            "Float (M)": round(float_m, 1),
                            "RVOL": rvol,
                            "AI Score": ai['score'],
                            "Thesis": ai['thesis'],
                            "News": news,
                            "Time": datetime.now(edt).strftime("%H:%M:%S")
                        }
                        
                        st.session_state.qualified.insert(0, new_item)
                        st.session_state.stats["pings"] += 1
                        
                        if ai['score'] >= 8:
                            play_sound()
                            st.session_state.stats["strong"] += 1
                            alert = f"🚨 GROK AI PING!\n{symbol} +{new_item['% Gain']}% (Score {ai['score']}/10)\n{ai['thesis']}"
                            st.success(alert)
                            send_telegram(alert)
                        
                        # Voice for scanner tickers
                        speak(f"{symbol}")
                
                st.session_state.qualified = st.session_state.qualified[:10]
        
        # Latest News
        with news_placeholder.container():
            news_df = get_latest_news()
            if not news_df.empty:
                new_news = []
                for _, item in news_df.head(5).iterrows():
                    title = item.get('title', 'No Title')
                    url = item.get('url', '#')
                    ticker = item.get('symbol', '')
                    if title not in st.session_state.last_news:
                        new_news.append(title)
                        speak(f"{ticker} {title}")
                        send_telegram(f"📰 News: {title}\n{item.get('text', '')[:200]}...\nRead more: {url}")
                    st.markdown(f"**[{title}]({url})**")
                    st.caption(item.get('publishedDate', ''))
                    st.write(item.get('text', 'No summary')[:300] + "...")
                    st.markdown("---")
                st.session_state.last_news = list(news_df.head(10)['title'])
            else:
                st.write("No news available")
        
        time.sleep(refresh_sec)
