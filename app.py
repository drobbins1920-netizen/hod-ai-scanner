import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Your FMP Key (hardcoded for testing)
API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"

st.set_page_config(page_title="AI HOD Scanner", layout="wide")
st.title("🚀 AI-Enhanced HOD Momentum Scanner")
st.markdown("**FMP + AI-powered day trading scanner** | Refresh for latest data")

# Sidebar
with st.sidebar:
    st.header("Settings")
    tickers_input = st.text_input("Tickers (comma-separated)", "AAPL, NVDA, TSLA, KIDZ, ZCMD, IREN")
    st.caption("Add more tickers or use dynamic scanner later")

tickers = [t.strip().upper() for t in tickers_input.split(",")]

# FMP Functions
def get_batch_quotes(symbols):
    if not symbols:
        return pd.DataFrame()
    url = f"https://financialmodelingprep.com/api/v3/quote/{','.join(symbols)}?apikey={API_KEY}"
    try:
        data = requests.get(url, timeout=10).json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching quotes: {e}")
        return pd.DataFrame()

def get_news(symbol, limit=5):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit={limit}&apikey={API_KEY}"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

# Simple AI Analyzer
def ai_analyze(row, news_items):
    change_pct = row.get('changesPercentage', 0) or row.get('changePercent', 0)
    score = max(1, min(10, int(abs(change_pct) * 0.08 + len(news_items) * 1.5 + 4)))
    sentiment = "Bullish" if change_pct > 5 else "Neutral" if change_pct > 0 else "Bearish"
    
    thesis = f"{len(news_items)} recent news items. "
    if score >= 8:
        thesis += "Strong momentum + catalyst potential."
    elif score >= 6:
        thesis += "Decent volume, watch for continuation."
    else:
        thesis += "Lower conviction setup."
    
    return {
        "ai_score": score,
        "sentiment": sentiment,
        "thesis": thesis[:180] + "..." if len(thesis) > 180 else thesis,
        "risk": "High vol - use tight stops" if score > 7 else "Moderate"
    }

# Run Scan
if st.button("🔄 Run Full Scan Now", type="primary"):
    with st.spinner("Fetching real-time data from FMP..."):
        df = get_batch_quotes(tickers)
        
        if df.empty:
            st.warning("No data returned. Check tickers or your API key limits.")
        else:
            results = []
            for _, row in df.iterrows():
                symbol = row['symbol']
                news = get_news(symbol)
                ai = ai_analyze(row.to_dict(), news)
                
                results.append({
                    "Ticker": symbol,
                    "Price": round(row.get('price', 0), 2),
                    "% Change": round(row.get('changesPercentage', 0), 2),
                    "Volume": f"{int(row.get('volume', 0)):,}",
                    "AI Score": ai['ai_score'],
                    "Sentiment": ai['sentiment'],
                    "Thesis": ai['thesis'],
                    "Risk": ai['risk']
                })
            
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values("AI Score", ascending=False)
            
            st.success(f"✅ Scan complete at {datetime.now().strftime('%H:%M:%S')}")
            st.dataframe(results_df, use_container_width=True, height=500)
            
            st.subheader("📋 AI Insights")
            for _, r in results_df.iterrows():
                with st.expander(f"{r['Ticker']} — AI Score: {r['AI Score']}/10"):
                    st.write(f"**{r['Sentiment']}**")
                    st.write(r['Thesis'])
                    st.write(f"**Risk:** {r['Risk']}")

st.caption("Tested with your FMP key. Next: Add real LLM, charts, or full-market scanning.")
