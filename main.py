import streamlit as st
import requests
import pandas as pd
import numpy as np

# Constants
COINDCX_API = "https://api.coindcx.com/exchange/ticker"

# App Title
st.set_page_config(page_title="CoinDCX Futures Daily Predictor", layout="centered")
st.title("🔍 Daily CoinDCX Futures Trade Prediction")

# Minimal User Inputs
st.sidebar.header("🎯 Daily Trade Goal")
capital = st.sidebar.number_input("Capital (₹):", value=1000, step=100)
target = st.sidebar.number_input("Target (₹):", value=10000, step=100)
position_type = st.sidebar.radio("Position", ["Long", "Short"])

# Constants for Strategy
high_target = 5  # 5%
high_risk = 2    # 2%
leverage = 10

# Derived Metrics
target_to_loss_ratio = round(high_target / high_risk, 2)
break_even_rate = round(100 / (1 + target_to_loss_ratio))
trades_required = int(np.ceil((target / (capital * (high_target / 100) * leverage))))

# API Fetch
@st.cache_data(ttl=60)
def get_market_data():
    try:
        response = requests.get(COINDCX_API)
        data = response.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def filter_futures(df):
    return df[df['market'].str.contains("_PERP")]

def find_breakout_candle(df, direction="Long"):
    df = df.copy()
    df = df[(df["volume"].astype(float) > 100000)]

    if "open" not in df.columns:
        df["open"] = df["last_price"].astype(float) * 0.99

    df["change"] = df["last_price"].astype(float) - df["open"]
    df["candle_body"] = abs(df["last_price"].astype(float) - df["open"])
    df["candle_range"] = abs(df["high"].astype(float) - df["low"].astype(float))
    df["body_ratio"] = df["candle_body"] / df["candle_range"]

    if direction == "Long":
        df = df[(df["change"] > 0) & (df["body_ratio"] > 0.4)]
    else:
        df = df[(df["change"] < 0) & (df["body_ratio"] > 0.4)]

    return df.sort_values("volume", ascending=False).head(1)

# Display Trade Setup

def display_minimal(symbol, price, target_price, stop_loss_price):
    st.success(f"**{symbol}** | Entry: ₹{price:.2f} | Target: ₹{target_price:.2f} | SL: ₹{stop_loss_price:.2f}")
    st.markdown("---")
    st.markdown(f"**Strategy:** Breakout {position_type}")
    st.markdown(f"**Reward:Risk:** {target_to_loss_ratio}:1")
    st.markdown(f"**Win Rate Needed:** ~{break_even_rate}%")
    st.markdown(f"**Trades to Reach ₹{target}:** {trades_required}")

# Main Execution
data = get_market_data()
if data.empty:
    st.error("❌ Failed to load CoinDCX data.")
else:
    data_filtered = filter_futures(data)
    top_setup = find_breakout_candle(data_filtered, direction=position_type)

    if not top_setup.empty:
        row = top_setup.iloc[0]
        symbol = row['market']
        price = float(row['last_price'])
        target_price = price * (1 + high_target / 100) if position_type == "Long" else price * (1 - high_target / 100)
        stop_loss_price = price * (1 - high_risk / 100) if position_type == "Long" else price * (1 + high_risk / 100)

        display_minimal(symbol, price, target_price, stop_loss_price)
    else:
        st.info("No golden candle detected today. Try again later or switch direction.")

st.caption("💡 Clean and sharp daily trades powered by breakout logic.")
