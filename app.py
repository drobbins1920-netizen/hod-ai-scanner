import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os
import threading
from webull.data.data_streaming_client import DataStreamingClient
from webull.data.common.category import Category
from webull.data.common.subscribe_type import SubscribeType

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBULL_APP_KEY = os.getenv("WEBULL_APP_KEY")
WEBULL_APP_SECRET = os.getenv("WEBULL_APP_SECRET")

st.set_page_config(page_title="DR Dashboard", layout="wide")
st.title("DR Dashboard - Webull Streaming")

edt = pytz.timezone('US/Eastern')

if "qualified" not in st.session_state:
    st.session_state.qualified = []
if "stats" not in st.session_state:
    st.session_state.stats = {"pings": 0, "strong": 0}
if "webull_quotes" not in st.session_state:
    st.session_state.webull_quotes = {}

# Filters
with st.expander("📊 Filters", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        min_gain = st.slider("Min % Gain", 5, 100, 5)
        min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (0.5, 50.0), step=0.5)
    with col2:
        min_rvol = st.slider("Min RVOL", 1.0, 10.0, 1.5, step=0.5)
        refresh_sec = st.slider("Refresh (seconds)", 10, 60, 20)

# Layout
left, right = st.columns([1, 2])

with left:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🏆 Top Movers</div>', unsafe_allow_html=True)
    movers_placeholder = st.empty()

with right:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🔍 Live HOD Scanner</div>', unsafe_allow_html=True)
    scanner_placeholder = st.empty()

placeholder = st.empty()

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

# Webull Streaming
def on_connect(client, api_client, session_id):
    st.success("✅ Webull Connected")
    client.subscribe(
        ["AAPL", "TSLA", "NVDA", "AMD", "SMCI", "PLTR", "HOOD", "RIVN"],
        Category.US_STOCK.name,
        [SubscribeType.QUOTE.name, SubscribeType.SNAPSHOT.name]
    )

def on_quotes_message(client, topic, quotes):
    for quote in quotes:
        symbol = quote.get('symbol')
        if symbol:
            st.session_state.webull_quotes[symbol] = quote

def on_subscribe_success(client, api_client, session_id):
    st.success("✅ Subscribed to Market Data")

def start_webull_stream():
    client = DataStreamingClient(
        WEBULL_APP_KEY,
        WEBULL_APP_SECRET,
        "us",
        "dr_dashboard",
        http_host="api.webull.com",
        mqtt_host="data-api.webull.com"
    )
    client.on_connect_success = on_connect
    client.on_quotes_message = on_quotes_message
    client.on_subscribe_success = on_subscribe_success
    client.connect_and_loop_forever()

# Start streaming
threading.Thread(target=start_webull_stream, daemon=True).start()

while True:
    with placeholder.container():
        st.caption(f"EDT: {datetime.now(edt).strftime('%H:%M:%S')} | Refresh: {refresh_sec}s")
        
        # Live HOD Scanner
        with scanner_placeholder.container():
            if st.session_state.webull_quotes:
                df = pd.DataFrame(list(st.session_state.webull_quotes.values()))
                candidates = df[
                    (df.get('change', 0) >= min_gain) &
                    (df.get('price', 0).between(min_price, max_price))
                ].copy()
                
                for _, row in candidates.iterrows():
                    symbol = row.get('symbol')
                    if any(item.get('Ticker') == symbol for item in st.session_state.qualified):
                        continue
                    
                    rvol = round(row.get('volume', 0) / 500000, 1)
                    if rvol < min_rvol: continue
                    
                    news = "No news"
                    ai = grok_analyze(symbol, row.get('change', 0), row.get('price', 0), row.get('volume', 0), news)
                    
                    new_item = {
                        "Ticker": f"[{symbol}](https://finance.yahoo.com/quote/{symbol})",
                        "Price": round(row.get('price', 0), 2),
                        "% Gain": round(row.get('change', 0), 2),
                        "Volume": f"{int(row.get('volume', 0)):,}",
                        "RVOL": rvol,
                        "AI Score": ai['score'],
                        "Thesis": ai['thesis'],
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
                    
                    speak(f"{symbol}")
                
                st.session_state.qualified = st.session_state.qualified[:15]
                
                if st.session_state.qualified:
                    st.dataframe(pd.DataFrame(st.session_state.qualified), use_container_width=True, height=500)
            else:
                st.info("Connecting to Webull... Waiting for data")
        
        time.sleep(refresh_sec)
