import streamlit as st
import pandas as pd
import requests
import time
import websocket
import json
import threading
from datetime import datetime

# ================== YOUR KEYS ==================
FMP_API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"
TELEGRAM_BOT_TOKEN = "8788067448:AAFboEZAZEOLYXxZss2Jk_ZWp83rV26eoHA"
TELEGRAM_CHAT_ID = "7680581613"

st.set_page_config(page_title="WebSocket HOD Scanner", layout="wide")
st.title("🚀 WebSocket Live HOD Momentum Scanner + Telegram")
st.caption("Real-time streaming • Rolling list • Telegram + Sound alerts")

# Sidebar Filters
with st.sidebar:
    st.header("Live Filters")
    min_gain = st.slider("Min % Gain", 5, 100, 20)
    min_price, max_price = st.slider("Price Range ($)", 0.5, 50.0, (1.0, 20.0), step=0.5)
    max_float_m = st.slider("Max Float (M)", 5, 100, 30)
    min_rvol = st.slider("Min RVOL (approx)", 1.0, 10.0, 3.0, step=0.5)
    
    if st.button("Clear List"):
        st.session_state.qualified = []
        st.rerun()

if "qualified" not in st.session_state:
    st.session_state.qualified = []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def play_sound():
    st.components.v1.html('<audio autoplay><source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg"></audio>', height=0)

# WebSocket Handler (FMP)
def on_message(ws, message):
    data = json.loads(message)
    # Process incoming real-time data here
    st.session_state.ws_data = data  # Store for main thread

def on_error(ws, error):
    st.error(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    st.warning("WebSocket closed")

def on_open(ws):
    st.success("WebSocket connected - subscribing to US stocks...")
    # Subscribe to major tickers or all (FMP has limits)
    subscribe_msg = json.dumps({"action": "subscribe", "tickers": "all"})  # Adjust as per FMP docs
    ws.send(subscribe_msg)

# Start WebSocket in background
def start_websocket():
    ws = websocket.WebSocketApp(
        f"wss://ws.financialmodelingprep.com?apikey={FMP_API_KEY}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# Start in thread
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = threading.Thread(target=start_websocket, daemon=True)
    st.session_state.ws_thread.start()

placeholder = st.empty()

while True:
    with placeholder.container():
        st.caption(f"Live WebSocket | Last update: {datetime.now().strftime('%H:%M:%S')}")
        
        # Your polling fallback + filter logic can go here if needed
        # For now, display current qualified list
        if st.session_state.qualified:
            df_display = pd.DataFrame(st.session_state.qualified)
            st.dataframe(df_display, use_container_width=True, height=700)
        else:
            st.info("WebSocket connected. Waiting for market activity matching your filters...")
        
        time.sleep(10)  # Light refresh
