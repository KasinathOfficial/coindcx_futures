import streamlit as st
import requests
from collections import Counter
import time
import pandas as pd
import altair as alt
import ta

st.set_page_config(page_title="CoinDCX Buy/Sell Tracker", layout="centered")

st.title("📈CoinDCX Futures Buy/Sell")

# --- Fetch available market pairs ---
@st.cache_data(ttl=3600)
def get_market_pairs():
    try:
        response = requests.get("https://public.coindcx.com/market_data/trade_pairs")
        response.raise_for_status()
        data = response.json()
        futures_pairs = sorted([item['pair'] for item in data if item['pair'].startswith("B-")])
        return futures_pairs
    except Exception as e:
        #st.error(f"Error fetching market pairs: {e}")
        # Fallback to a default list
        print("ok")
        
market_pairs = get_market_pairs()
selected_pair = st.text_input("Enter Futures Market Pair (e.g. B-BTC_USDT):", value="B-BTC_USDT")

# Refresh interval
interval = st.slider("Refresh Interval (seconds):", 5, 60, 10)

# Start button
start = st.button("🔄 Start Tracking")

# Fetch trades
def get_recent_trades(market_pair):
    url = f'https://public.coindcx.com/market_data/trade_history?pair={market_pair}'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch trades: {e}")
        return []

# Count buys/sells
def count_trade_directions(trades):
    counter = Counter()
    for trade in trades:
        if trade.get('m') == True:
            counter['sell'] += 1
        elif trade.get('m') == False:
            counter['buy'] += 1
    return counter

# Fetch OHLCV data for ADX
@st.cache_data(ttl=60)
def get_ohlcv_data(pair):
    url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval=1m&limit=50"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        return df
    except Exception as e:
        st.warning(f"Error fetching OHLCV for ADX: {e}")
        return pd.DataFrame()

# ADX calculation
def get_adx_signal(df):
    if df.empty or len(df) < 20:
        return "⚪️ ADX: Not enough data"
    indicator_adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
    adx_val = indicator_adx.adx().iloc[-1]
    plus_di = indicator_adx.adx_pos().iloc[-1]
    minus_di = indicator_adx.adx_neg().iloc[-1]

    if adx_val > 25:
        if plus_di > minus_di:
            return f"📈 ADX {adx_val:.1f} → Uptrend"
        else:
            return f"📉 ADX {adx_val:.1f} → Downtrend"
    else:
        return f"⚪️ ADX {adx_val:.1f} → Weak / No trend"

# Combined signal logic
def generate_trade_signal(buy_count, sell_count, adx_msg):
    total = buy_count + sell_count
    if total == 0:
        return "⏸ No Activity"

    buy_ratio = buy_count / total

    if "Uptrend" in adx_msg and buy_ratio > 0.65:
        return "🟢 Strong Buy / Long"
    elif "Downtrend" in adx_msg and buy_ratio < 0.35:
        return "🔴 Strong Sell / Short"
    elif buy_ratio > 0.55:
        return "🟡 Weak Buy / Caution"
    elif buy_ratio < 0.45:
        return "🟠 Weak Sell / Caution"
    else:
        return "⚪️ Neutral / Wait"

# Tracking
if start:
    st.success(f"Tracking: {selected_pair}")
    placeholder = st.empty()

    while True:
        trades = get_recent_trades(selected_pair)
        trade_counts = count_trade_directions(trades)
        buy_count = trade_counts['buy']
        sell_count = trade_counts['sell']

        ohlcv_df = get_ohlcv_data(selected_pair)
        adx_status = get_adx_signal(ohlcv_df)

        signal = generate_trade_signal(buy_count, sell_count, adx_status)

        with placeholder.container():
            col1, col2 = st.columns(2)
            col1.metric(label="📥 Buys", value=buy_count)
            col2.metric(label="📤 Sells", value=sell_count)

            df_chart = pd.DataFrame({
                'Type': ['Buys', 'Sells'],
                'Count': [buy_count, sell_count]
            })

            chart = alt.Chart(df_chart).mark_bar(
                size=60,
                cornerRadiusTopLeft=10,
                cornerRadiusTopRight=10
            ).encode(
                x=alt.X('Type', axis=alt.Axis(labelFontSize=16, titleFontSize=18)),
                y=alt.Y('Count', axis=alt.Axis(labelFontSize=14, titleFontSize=16)),
                color=alt.Color('Type', scale=alt.Scale(domain=['Buys', 'Sells'], range=['#34a853', '#ea4335']), legend=None),
                tooltip=['Type', 'Count']
            ).properties(
                width=420,
                height=320,
                title=alt.TitleParams(
                    text="Buy vs Sell Volume",
                    fontSize=22,
                    color='#1a73e8'
                )
            )

            st.altair_chart(chart, use_container_width=True)

            st.markdown(f"##### 🧭 ADX Trend: {adx_status}")
            st.markdown(f"##### 🚦 Trade Signal: {signal}")

        time.sleep(interval)
