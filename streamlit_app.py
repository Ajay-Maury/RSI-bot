import streamlit as st
from utils import get_daily_data, init_kite
from strategy import apply_indicators, check_signal
from backtest import backtest
import pandas as pd
from kiteconnect import KiteConnect
import yaml

# Load API keys + access_token
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

api_key = config["api"]["api_key"]
access_token = config["api"]["access_token"]

# Init Kite object
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

st.set_page_config(page_title="RSI + EMA Algo Dashboard", layout="wide")
st.title("📈 RSI + EMA Algo Trading Dashboard")

symbol = st.selectbox("Select Symbol", ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"])
rsi_period = st.slider("RSI Period", 5, 30, 14)
ema_period = st.slider("EMA Period", 10, 100, 50)
sma_period = 200
rsi_buy = st.slider("RSI Buy Threshold", 10, 50, 30)
rsi_sell = st.slider("RSI Sell Threshold", 50, 90, 70)
days = st.slider("Number of Days to Load", 50, 500, 200)
use_sma = st.checkbox("Use SMA Trend Filter (Price > SMA)", value=True)
use_macd = st.checkbox("Use MACD Filter (MACD > Signal)", value=True)
adx_thresh = st.slider("ADX Minimum Trend Strength", 10, 50, 20)

# kite = None  # Replace with init_kite if using live trading
df = get_daily_data(kite, symbol, days=days)
df = apply_indicators(df, rsi_period, ema_period, sma_period)
signal = check_signal(df, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)

st.subheader(f"Current Signal: **{signal}**")
st.line_chart(df.set_index('date')[['close', 'ema']])

with st.expander("📉 RSI Chart"):
    st.line_chart(df.set_index('date')['rsi'])

with st.expander("📉 SMA / ADX / MACD"):
    st.line_chart(df.set_index('date')[['sma', 'ema', 'close']])
    st.line_chart(df.set_index('date')[['adx']])
    st.line_chart(df.set_index('date')[['macd', 'macd_signal']])

st.markdown("---")
st.header("🔁 Backtest Results")

stop_loss = st.number_input("Stop Loss %", value=2.0) / 100
take_profit = st.number_input("Take Profit %", value=4.0) / 100

if st.button("Run Backtest"):
    trades = backtest(df.copy(), rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd)
    if trades.empty:
        st.warning("No trades generated.")
    else:
        st.success(f"{len(trades)} trades simulated.")
        st.dataframe(trades)

        win_rate = (trades['return_pct'] > 0).mean()
        avg_return = trades['return_pct'].mean()
        st.metric("Win Rate", f"{win_rate*100:.2f}%")
        st.metric("Avg Return per Trade", f"{avg_return:.2f}%")
        trades['cumulative_return'] = (1 + trades['return_pct'] / 100).cumprod()
        st.line_chart(trades.set_index('exit_date')['cumulative_return'])