import re
import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

# We need the custom exception from utils
from utils import (
    get_kite_client,
    get_all_stock_symbols,
    get_instrument_token,
    get_historical_data,
    TokenException
)
from strategy import apply_indicators, check_signal
from backtest import backtest

# ======================================================================================
# --- TOKEN GENERATION LOGIC ---
# This block handles the redirect from Kite after a successful login.
# ======================================================================================
query_params = st.query_params
if "request_token" in query_params:
    request_token = query_params["request_token"]

    st.set_page_config(page_title="Generating Token...", layout="centered")
    st.title("🔑 Kite Access Token Generator")
    st.success(f"✅ Request Token Received: `{request_token}`")

    try:
        is_deployed = os.getenv("STREAMLIT_SERVER_RUNNING_ON_CLOUD") == "true"
        if is_deployed:
            api_key = st.secrets.get("KITE_API_KEY")
            api_secret = st.secrets.get("KITE_API_SECRET")
        else:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("KITE_API_KEY")
            api_secret = os.getenv("KITE_API_SECRET")

        if not api_key or not api_secret:
            st.error("KITE_API_KEY or KITE_API_SECRET not found in your configuration.")
        else:
            kite = KiteConnect(api_key=api_key)
            with st.spinner("Generating session... Please wait."):
                session = kite.generate_session(request_token, api_secret=api_secret)
                access_token = session["access_token"]

            st.success("🎉 **SUCCESS! Your Access Token has been generated.** 🎉")
            st.code(access_token)
            st.markdown("""
            **👇 NEXT ACTION 👇**
            1. **Copy this new token.**
            2. **Update the `KITE_ACCESS_TOKEN` value in your Streamlit Secrets or .env file.**
            """)
            st.warning("IMPORTANT: You must update your secrets or .env file before returning to the app.", icon="⚠️")
            
            # --- NEW: Redirect Button ---
            st.link_button("✅ Go Back to Main App", "/", use_container_width=True, type="primary")

    except Exception as e:
        st.error(f"❌ An error occurred during session generation: {e}")
        st.info("Please ensure your API Key and Secret are correct in your app's configuration.")

    st.stop()

# ======================================================================================
# --- Main Dashboard Function ---
# This function wraps all the main logic and is called only on successful login.
# ======================================================================================
def run_main_dashboard(kite):
    """
    This function contains the entire UI and logic for the main trading dashboard.
    It only runs if the kite client is successfully authenticated.
    """
    # --- Load Symbols ---
    @st.cache_data(ttl=3600)
    def load_symbols():
        return get_all_stock_symbols(kite)
    
    all_symbols = load_symbols()
    st.caption(f"✅ Loaded {len(all_symbols)} NSE + BSE equity symbols. Session is active.")

    # --- Sidebar Parameters ---
    st.sidebar.header("⚙️ Data & Strategy Parameters")
    interval_options = {"Daily": "day", "60 Minute": "60minute", "15 Minute": "15minute", "5 Minute": "5minute", "Minute": "minute"}
    selected_interval_label = st.sidebar.selectbox("Select Chart Interval", options=list(interval_options.keys()), index=0)
    interval = interval_options[selected_interval_label]

    st.sidebar.header("📊 Indicator Parameters")
    rsi_period = st.sidebar.slider("RSI Period", 5, 30, 14)
    ema_period = st.sidebar.slider("EMA Period (for crossover)", 10, 100, 50)
    sma_period = 200
    rsi_buy = st.sidebar.slider("RSI Buy Threshold", 10, 50, 30)
    rsi_sell = st.sidebar.slider("RSI Sell Threshold", 50, 90, 70)

    st.sidebar.header("🔧 Optional Filters")
    adx_thresh = st.sidebar.slider("ADX Minimum Strength", 10, 50, 20)
    use_sma = st.sidebar.checkbox("Use 200-Day SMA Filter (Price > SMA)", True)
    use_macd = st.sidebar.checkbox("Use MACD Filter (MACD > Signal)", True)

    # --- Symbol Selection in Main Panel ---
    selected_label = st.selectbox("🔍 Search & Select NSE/BSE Stock", options=all_symbols, index=None, placeholder="Start typing: RELIANCE, INFY, TCS…")

    if not selected_label:
        st.info("Please select a stock to begin analysis.")
        st.stop()

    m = re.match(r"^(.*?)\s*-\s*\((.*?)\)\s*-\s*\((.*?)\)\s*$", selected_label)
    if not m:
        st.error("Symbol format not recognized. Please reselect.")
        st.stop()

    company_name, exchange, symbol = m.groups()
    exchange = exchange.upper().strip()
    symbol = symbol.upper().strip()

    # --- Main App Logic (Charts, Backtesting, etc.) ---
    if interval == "day": days_to_fetch = 540
    elif interval in {"60minute", "15minute", "5minute"}: days_to_fetch = 120
    else: days_to_fetch = 7

    df = get_historical_data(kite, symbol, days=days_to_fetch, interval=interval, exchange=exchange)
    
    if df.empty:
        st.error(f"No historical data for {symbol} at '{selected_interval_label}'.")
        st.stop()

    st.markdown("---")
    current_price = float(df.iloc[-1]["close"])
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"{company_name} — ({exchange}:{symbol})")
    with col2:
        if len(df) > 1:
            prev_price = float(df.iloc[-2]["close"])
            price_change = current_price - prev_price
            pct_change = (price_change / prev_price) * 100 if prev_price else 0.0
            st.metric(f"Last Price", f"₹{current_price:,.2f}", f"{price_change:,.2f} ({pct_change:.2f}%)")
        else:
            st.metric(f"Last Price", f"₹{current_price:,.2f}")

    # Altair Chart
    base = alt.Chart(df).encode(alt.X("date:T", axis=alt.Axis(title="Date")))
    line = base.mark_line().encode(alt.Y("close:Q", axis=alt.Axis(title="Close Price (₹)")))
    nearest = alt.selection_point(nearest=True, on="mouseover", fields=["date"], empty="none")
    selectors = base.mark_point().encode(
        opacity=alt.value(0),
        tooltip=alt.Tooltip("custom_tooltip:N", title="Details"),
    ).add_params(nearest).transform_calculate(
        custom_tooltip = "'₹' + format(datum.close, ',.2f') + ' (' + timeFormat(datum.date, '%b %d, %Y') + ')'"
    )
    points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    rule = base.mark_rule().encode(x="date:T").transform_filter(nearest)
    layered_chart = alt.layer(line, selectors, points, rule).interactive().properties(height=400)
    st.altair_chart(layered_chart, use_container_width=True, theme="streamlit")

    # Performance & Price Vitals
    st.subheader("Performance & Price Vitals")
    def fmt(val, prefix="₹", nd=2):
        try:
            return f"{prefix}{float(val):,.{nd}f}"
        except (ValueError, TypeError):
            return "—"
    
    try:
        quote_key = f"{exchange}:{symbol}"
        full_quote = kite.quote(quote_key)
        quote_data = full_quote.get(quote_key)
        if not quote_data:
            st.warning(f"Quote data not found for {quote_key}.")
        else:
            today_ohlc = quote_data.get("ohlc", {}) or {}
            today_low = today_ohlc.get("low")
            today_high = today_ohlc.get("high")
            last_price = quote_data.get("last_price", current_price)
            if all(v is not None for v in [today_low, today_high, last_price]) and today_high > today_low:
                st.write("**Today's Range**")
                pos_today = (last_price - today_low) / (today_high - today_low)
                st.progress(max(0.0, min(1.0, float(pos_today))))
                p_col1, p_col2, p_col3 = st.columns(3)
                p_col1.metric("Low", fmt(today_low))
                p_col2.metric("Last Price", fmt(last_price))
                p_col3.metric("High", fmt(today_high))

            df_52w = get_historical_data(kite, symbol, days=365, interval="day", exchange=exchange)
            if not df_52w.empty:
                w_low = float(df_52w["low"].min())
                w_high = float(df_52w["high"].max())
                if w_high > w_low:
                    st.write("**52-Week Range**")
                    pos_52 = (last_price - w_low) / (w_high - w_low)
                    st.progress(max(0.0, min(1.0, float(pos_52))))
                    w_col1, w_col2, w_col3 = st.columns(3)
                    w_col1.metric("52-Week Low", fmt(w_low))
                    w_col2.metric("Last Price", fmt(last_price))
                    w_col3.metric("52-Week High", fmt(w_high))

            st.write("**Market Vitals**")
            v1, v2, v3, v4, v5 = st.columns(5)
            v1.metric("Open Price", fmt(today_ohlc.get("open")))
            prev_close = last_price - (quote_data.get("change") or 0)
            v2.metric("Previous Close", fmt(prev_close))
            v3.metric("Volume", f"{quote_data.get('volume'):,}" if quote_data.get("volume") is not None else "—")
            v4.metric("Lower Circuit", fmt(quote_data.get("lower_circuit_limit")))
            v5.metric("Upper Circuit", fmt(quote_data.get("upper_circuit_limit")))
    except Exception as e:
        st.error(f"An error occurred while fetching quote data: {e}")

    # Indicators + Signals + Detailed Charts
    if len(df) >= sma_period:
        df_ind = apply_indicators(df.copy(), rsi_period, ema_period, sma_period)
        signal = check_signal(df_ind, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)

        if signal == "BUY":
            st.success(f"📢 Current Signal: **{signal}**")
        elif signal == "SELL":
            st.error(f"📢 Current Signal: **{signal}**")
        else:
            st.info(f"📢 Current Signal: **{signal}**")

        with st.expander("Click to view detailed Indicator Charts (RSI, EMA/SMA, ADX, MACD)"):
            st.line_chart(df_ind.set_index("date")[["close", "ema", "sma"]], use_container_width=True)
            st.line_chart(df_ind.set_index("date")[["rsi"]], use_container_width=True)
            st.line_chart(df_ind.set_index("date")[["adx"]], use_container_width=True)
            st.line_chart(df_ind.set_index("date")[["macd", "macd_signal"]], use_container_width=True)

        st.markdown("---")
        st.header("🔁 Backtest Your Strategy")

        today = datetime.today().date()
        default_start = today - timedelta(days=365)
        start_date = st.date_input("Start Date", value=default_start, min_value=datetime(2000, 1, 1).date(), max_value=today)
        end_date = st.date_input("End Date", value=today, min_value=start_date, max_value=today)

        start_date_dt = datetime.combine(start_date, datetime.min.time())
        end_date_dt = datetime.combine(end_date, datetime.max.time())

        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            stop_loss = st.number_input("Stop Loss %", min_value=0.5, max_value=20.0, value=2.0, step=0.5) / 100
        with col_bt2:
            take_profit = st.number_input("Take Profit %", min_value=1.0, max_value=50.0, value=4.0, step=0.5) / 100

        force_signal_mode = st.checkbox("Force Signal Mode (For Debugging)", value=False)
        if st.button("🚀 Run Backtest on Historical Data"):
            with st.spinner("Simulating trades..."):
                df_with_ind = apply_indicators(df.copy(), rsi_period=rsi_period, ema_period=ema_period, sma_period=sma_period)
                result = backtest(
                    df=df_with_ind.copy(), rsi_period=rsi_period, ema_period=ema_period,
                    rsi_buy=rsi_buy, rsi_sell=rsi_sell, stop_loss=stop_loss, take_profit=take_profit,
                    adx_thresh=adx_thresh, use_sma=use_sma, use_macd=use_macd,
                    start_date=start_date_dt, end_date=end_date_dt, force_signal=force_signal_mode
                )
                if isinstance(result, tuple) and len(result) == 2:
                    trades_df, debug_counts = result
                else:
                    trades_df, debug_counts = result, {}

            if trades_df is None or not isinstance(trades_df, pd.DataFrame) or trades_df.empty:
                st.warning("No trades were generated for this configuration.")
            else:
                st.success(f"✅ {len(trades_df)} trades simulated.")
                st.dataframe(trades_df.style.format({"entry_price": "₹{:.2f}", "exit_price": "₹{:.2f}", "return_pct": "{:.2f}%"}))

                win_rate = (trades_df["return_pct"] > 0).mean() * 100
                avg_return = trades_df["return_pct"].mean()
                total_return = (1 + trades_df["return_pct"] / 100).prod() - 1

                st.subheader("Performance Metrics")
                m1, m2, m3 = st.columns(3)
                m1.metric("🏆 Win Rate", f"{win_rate:.2f}%")
                m2.metric("📈 Avg. Return/Trade", f"{avg_return:.2f}%")
                m3.metric("💰 Total Return", f"{total_return * 100:.2f}%")
                
                trades_df['equity_curve'] = (1 + trades_df['return_pct'] / 100).cumprod()
                st.line_chart(trades_df.set_index('date')['equity_curve'])
    else:
        st.warning(f"Not enough historical data to compute indicators (requires at least {sma_period} data points, but only found {len(df)}).")
        st.info("Strategy analysis and backtesting are disabled. Please choose a longer chart interval or a different stock.")

# ======================================================================================
# --- Main App Execution Logic ---
# This is the main entry point that controls whether the login view or the main app is shown.
# ======================================================================================

st.set_page_config(page_title="RSI Trading Dashboard", layout="wide")
st.title("📈 RSI + Multi-Indicator Algo Trading Dashboard")

try:
    # --- 1. Attempt to connect to Kite API ---
    kite = get_kite_client()

    # --- 2. If successful, run the FULL app ---
    run_main_dashboard(kite)

except TokenException as e:
    # --- 3. If connection fails, draw the "Login" view ---
    st.error(f"🔐 Authentication Error: {e}")
    st.info("Your session has likely expired. Please generate a new access token to continue.")
    
    st.sidebar.header("🔑 Generate New Access Token")
    st.sidebar.info("Click the link below to log in to Kite, authorize the app, and generate a new access token.")
    
    try:
        is_deployed = os.getenv("STREAMLIT_SERVER_RUNNING_ON_CLOUD") == "true"
        api_key_for_login = st.secrets.get("KITE_API_KEY") if is_deployed else os.getenv("KITE_API_KEY")
        if api_key_for_login:
            kite_login_client = KiteConnect(api_key=api_key_for_login)
            st.sidebar.link_button("🔗 Log in to Kite to Generate Token", kite_login_client.login_url())
        else:
            st.sidebar.warning("KITE_API_KEY not found in configuration.")
    except Exception as link_e:
        st.sidebar.error(f"Could not generate login link: {link_e}")

except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
    st.exception(e)