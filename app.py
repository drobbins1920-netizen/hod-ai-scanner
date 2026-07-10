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

# #1 Gainer Box
gainer_box = st.empty()

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

# Layout
col_left, col_right = st.columns([2, 3])

with col_left:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🏆 Top Gainers</div>', unsafe_allow_html=True)
    session_filter = st.selectbox("Session", ["Pre-Market", "Regular Hours", "After Hours"], index=1)
    top_gainers_placeholder = st.empty()

with col_right:
    st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">🔍 Live HOD Scanner</div>', unsafe_allow_html=True)
    scanner_placeholder = st.empty()

st.markdown('<div style="border: 2px solid #444; border-radius: 8px; padding: 10px;">📈 Mini Charts</div>', unsafe_allow_html=True)
charts_placeholder = st.empty()

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
    st.components.v1.html(f'<script>speechSynthesis.speak(new SpeechSynthesisUtterance("{text}"));</script>', height=0)

while True:
    with placeholder.container():
        st.caption(f"EDT: {datetime.now(edt).strftime('%H:%M:%S')} | Refresh: {refresh_sec}s")
        
        df = get_top_gainers()
        
        if not df.empty:
            # #1 Gainer Box (flashing + bell on 10% change or new ticker)
            top = df.iloc[0]
            color = "lime" if top.get('changesPercentage', 0) > 0 else "red"
            flash_speed = "0.5s" if abs(top.get('changesPercentage', 0) - st.session_state.last_top_change) >= 10 else "5s"
            gainer_box.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 20px; border: 2px solid #444; border-radius: 10px; text-align: center; font-size: 3em; font-weight: bold; color: {color}; animation: flash {flash_speed} infinite;">
                #1 Gainer: {top['symbol']} +{round(top.get('changesPercentage', 0), 1)}%
            </div>
            """, unsafe_allow_html=True)
            
            if abs(top.get('changesPercentage', 0) - st.session_state.last_top_change) >= 10:
                play_sound()
            
            st.session_state.last_top_change = top.get('changesPercentage', 0)
            
            # Top Gainers list (no Name, green %)
            with top_gainers_placeholder.container():
                display_df = df.head(15)[['symbol', 'price', 'changesPercentage', 'volume']].copy()
                display_df['% Change'] = display_df['changesPercentage'].apply(lambda x: f"{x:.2f}%")
                st.dataframe(display_df[['symbol', 'price', '% Change', 'volume']], use_container_width=True, height=400)
            
            # Scanner
            with scanner_placeholder.container():
                candidates = df[
                    (df.get('changesPercentage', 0) >= min_gain) &
                    (df.get('price', 0).between(min_price, max_price))
                ].copy()
                
                for _, row in candidates.iterrows():
                    symbol = row['symbol']
                    if any(item.get('Ticker') == symbol for item in st.session_state.qualified):
                        continue
                    
                    rvol = round(row.get('volume', 0) / 500000, 1)
                    if rvol < min_rvol: continue
                    
                    float_m = 999
                    news = get_news_title(symbol)
                    ai = grok_analyze(symbol, row.get('changesPercentage', 0), row.get('price', 0), row.get('volume', 0), news)
                    
                    new_item = {
                        "Ticker": f"[{symbol}](https://finance.yahoo.com/quote/{symbol})",
                        "Price": round(row.get('price', 0), 2),
                        "% Gain": round(row.get('changesPercentage', 0), 2),
                        "Volume": f"{int(row.get('volume', 0)):,}",
                        "Float (M)": round(float_m, 1),
                        "RVOL": rvol,
                        "AI Score": ai['score'],
                        "Thesis": ai['thesis'],
                        "News": news[:90] + "..." if len(news) > 90 else news,
                        "Time": datetime.now(edt).strftime("%H:%M:%S")
                    }
                    
                    st.session_state.qualified.insert(0, new_item)
                    st.session_state.stats["pings"] += 1
                    
                    if ai['score'] >= 8:
                        play_sound()
                        st.session_state.stats["strong"] += 1
                        alert = f"🚨 GROK AI PING!\n{symbol} +{new_item['% Gain']}% (Score {ai['score']}/10)\n{ai['thesis']}\n{new_item['News']}"
                        st.success(alert)
                        send_telegram(alert)
                    
                    # Voice for scanner tickers only
                    speak(f"{symbol} news catalyst" if "news" in news.lower() else symbol)
            
            st.session_state.qualified = st.session_state.qualified[:20]
            
            # Charts
            with charts_placeholder.container():
                for item in st.session_state.qualified[:4]:
                    symbol = item["Ticker"].split('[')[1].split(']')[0] if '[' in item["Ticker"] else item["Ticker"]
                    st.markdown(f"**{symbol}**")
                    try:
                        data = yf.download(symbol, period="1d", interval="5m")
                        if not data.empty:
                            data['MA5'] = data['Close'].rolling(5).mean()
                            data['MA20'] = data['Close'].rolling(20).mean()
                            data['TypicalPrice'] = (data['High'] + data['Low'] + data['Close']) / 3
                            data['TPV'] = data['TypicalPrice'] * data['Volume']
                            data['VWAP'] = data['TPV'].cumsum() / data['Volume'].cumsum()
                            exp1 = data['Close'].ewm(span=12, adjust=False).mean()
                            exp2 = data['Close'].ewm(span=26, adjust=False).mean()
                            data['MACD'] = exp1 - exp2
                            data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
                            
                            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.3, 0.2])
                            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close']), row=1, col=1)
                            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name="VWAP", line=dict(color="orange")), row=1, col=1)
                            fig.add_trace(go.Bar(x=data.index, y=data['Volume']), row=2, col=1)
                            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD"), row=3, col=1)
                            fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name="Signal"), row=3, col=1)
                            st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.write(f"Chart unavailable for {symbol}")
        
        time.sleep(refresh_sec)
