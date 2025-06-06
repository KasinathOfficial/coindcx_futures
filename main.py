import streamlit as st
import requests
import pandas as pd
import numpy as np

# Constants
COINDCX_API = "https://api.coindcx.com/exchange/ticker"

# App Title
st.set_page_config(page_title="CoinDCX Futures Trading Assistant", layout="centered")
st.title("📈 CoinDCX Futures Trading Assistant")
st.markdown("""
<style>
.big-font {
    font-size:24px !important;
}
.metric-box {
    padding: 10px;
    border-radius: 10px;
    background-color: #f9f9f9;
    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

# User Inputs
st.sidebar.header("💼 Trading Goals")
capital = st.sidebar.number_input("Enter your current capital (₹):", value=1000, step=100)
target = st.sidebar.number_input("Enter your profit target for the day (₹):", value=10000, step=100)

# Advanced Metrics Input
st.sidebar.header("📊 Risk/Reward Parameters")
high_target = st.sidebar.slider("High Reward Target %", min_value=1, max_value=20, value=5)
high_risk = st.sidebar.slider("High Loss Limit %", min_value=1, max_value=10, value=2)
leverage = st.sidebar.slider("Leverage", min_value=1, max_value=20, value=10)

# Long/Short Toggle
position_type = st.sidebar.radio("📉 Select Trade Direction", ["Long", "Short"])

# Extra Info Metrics
target_to_loss_ratio = round(high_target / high_risk, 2)
break_even_rate = round(100 / (1 + target_to_loss_ratio))
trades_required = int(np.ceil((target / (capital * (high_target / 100) * leverage))))

# Ratio Highlights
st.sidebar.markdown("---")
st.sidebar.header("📈 Trading Probability Zones")
st.sidebar.markdown(f"**Risk/Reward Ratio:** {target_to_loss_ratio} : 1")
st.sidebar.markdown(f"**Break-Even Win Rate Needed:** ~{break_even_rate}%")
st.sidebar.markdown(f"**Trades Needed to Hit Daily Target:** {trades_required}")

if target_to_loss_ratio >= 3:
    st.sidebar.success("Excellent R:R Setup")
elif target_to_loss_ratio >= 2:
    st.sidebar.info("Good R:R, trade with confirmation")
else:
    st.sidebar.warning("⚠️ Risky Setup, be cautious")

# Fetch live data from CoinDCX
@st.cache_data(ttl=60)
def get_market_data():
    try:
        response = requests.get(COINDCX_API)
        data = response.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# Filter futures pairs only
def filter_futures(df):
    return df[df['market'].str.contains("_PERP")]

# Golden Candle Detector (based on candle breakout and type)
def find_breakout_candle(df, direction="Long"):
    df = df.copy()
    df["spread"] = abs(df["ask"] - df["bid"])
    df = df[(df["volume"] > 100000) & (df["spread"] < 0.2)]  # reduced strictness
    df["change"] = df["last_price"].astype(float) - df["open"]
    df["candle_body"] = abs(df["last_price"].astype(float) - df["open"])
    df["candle_range"] = abs(df["high"] - df["low"])
    df["body_ratio"] = df["candle_body"] / df["candle_range"]

    if direction == "Long":
        df = df[(df["change"] > 0) & (df["body_ratio"] > 0.4)]
    else:
        df = df[(df["change"] < 0) & (df["body_ratio"] > 0.4)]

    return df.sort_values("volume", ascending=False).head(1)

# Display metrics function
def display_metrics(symbol, price, target_price, stop_loss_price, leverage, position_size, expected_profit):
    st.markdown(f"### ✅ Golden Candle Trade: `{symbol}`")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Entry Details")
        st.markdown(f"**Entry Price**: ₹{price:,.2f}")
        st.markdown(f"**Target Price**: ₹{target_price:,.2f}")
        st.markdown(f"**Stop Loss**: ₹{stop_loss_price:,.2f}")
        st.markdown(f"**Leverage**: {leverage}x")
        st.markdown(f"**Position Size**: ₹{position_size:,.2f}")
        st.markdown(f"**Expected Profit**: ₹{expected_profit:,.2f}")
    with col2:
        st.markdown("#### Strategy Analysis")
        st.markdown(f"""
        | Parameter                | Value                           |
        |--------------------------|---------------------------------|
        | Strategy Type            | Breakout Candle (Momentum)     |
        | Risk Level               | {high_risk}% Stop Loss         |
        | Reward Potential         | {high_target}% Gain            |
        | Reward:Risk Ratio        | {target_to_loss_ratio}:1       |
        | Break-Even Win Rate      | ~{break_even_rate}%            |
        | Recommended Win %        | 35%+                            |
        | Confirmation             | Candle Body > 40% of Range     |
        | Daily Trades Needed      | {trades_required}              |
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("Trade only if breakout candles confirm momentum. Don’t chase late.")

# Main Execution
data = get_market_data()
if data.empty:
    st.error("❌ Failed to load data from CoinDCX API.")
else:
    data_filtered = filter_futures(data)
    top_setup = find_breakout_candle(data_filtered, direction=position_type)

    if not top_setup.empty:
        row = top_setup.iloc[0]
        symbol = row['market']
        price = float(row['last_price'])

        position_size = capital * leverage
        target_price = price * (1 + high_target / 100) if position_type == "Long" else price * (1 - high_target / 100)
        stop_loss_price = price * (1 - high_risk / 100) if position_type == "Long" else price * (1 + high_risk / 100)
        expected_profit = abs((target_price - price) * leverage)

        display_metrics(symbol, price, target_price, stop_loss_price, leverage, position_size, expected_profit)
    else:
        st.markdown("### ❕ No Golden Candle Found Today")
        st.info("Please check again later or adjust settings.")

st.markdown("---")
st.caption("Made for real crypto traders building wealth step-by-step 1🚀")
