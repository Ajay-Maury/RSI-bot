import re
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

from utils import (
    get_kite_client,
    get_all_stock_symbols,
    get_instrument_token,
    get_historical_data,
)
from strategy import apply_indicators, check_signal
from backtest import backtest

# --- 1) Streamlit App Config ---
st.set_page_config(page_title="RSI Trading Dashboard", layout="wide")
st.title("📈 RSI + Multi-Indicator Algo Trading Dashboard")

# --- 2) Kite API Initialization ---
try:
    kite = get_kite_client()
except Exception as e:
    st.error(f"Failed to initialize Kite client. Please check your credentials. Error: {e}")
    st.stop()

# --- 3) Load NSE + BSE Symbols (Cached) ---
@st.cache_data(ttl=3600)
def load_symbols():
    # note: relies on outer 'kite'. OK since we set a TTL
    return get_all_stock_symbols(kite)

try:
    all_symbols = load_symbols()
    st.caption(f"✅ Loaded {len(all_symbols)} NSE + BSE equity symbols.")
except Exception as e:
    st.error(f"Failed to load stock symbols from Kite. Error: {e}")
    st.stop()

# --- 4) Sidebar Parameters ---
st.sidebar.header("⚙️ Data & Strategy Parameters")
interval_options = {
    "Daily": "day",
    "60 Minute": "60minute",
    "15 Minute": "15minute",
    "5 Minute": "5minute",
    "Minute": "minute",
}
selected_interval_label = st.sidebar.selectbox(
    "Select Chart Interval",
    options=list(interval_options.keys()),
    index=0,
)
interval = interval_options[selected_interval_label]

st.sidebar.header("📊 Indicator Parameters")
rsi_period = st.sidebar.slider("RSI Period", min_value=5, max_value=30, value=14)
ema_period = st.sidebar.slider("EMA Period (for crossover)", min_value=10, max_value=100, value=50)
sma_period = 200
rsi_buy = st.sidebar.slider("RSI Buy Threshold (Enter when RSI is below)", min_value=10, max_value=50, value=30)
rsi_sell = st.sidebar.slider("RSI Sell Threshold (Exit when RSI is above)", min_value=50, max_value=90, value=70)

st.sidebar.header("🔧 Optional Filters")
adx_thresh = st.sidebar.slider("ADX Minimum Strength", min_value=10, max_value=50, value=20)
use_sma = st.sidebar.checkbox("Use 200-Day SMA Filter (Price > SMA)", value=True)
use_macd = st.sidebar.checkbox("Use MACD Filter (MACD > Signal)", value=True)

# --- 5) Symbol Selection ---
selected_label = st.selectbox(
    "🔍 Search & Select NSE/BSE Stock",
    options=all_symbols,
    index=None,
    placeholder="Start typing: RELIANCE, INFY, TCS…",
)

if not selected_label:
    st.info("Please select a stock to begin analysis.")
    st.stop()

# Safe parse of "Name - (EXCHANGE) - (SYMBOL)"
m = re.match(r"^(.*?)\s*-\s*\((.*?)\)\s*-\s*\((.*?)\)\s*$", selected_label)
if not m:
    st.error("Symbol format not recognized. Please reselect.")
    st.stop()

company_name, exchange, symbol = m.groups()
exchange = exchange.upper().strip()
symbol = symbol.upper().strip()

# --- 6) Data Fetching ---
try:
    # Safer days-to-fetch per interval to respect Kite candle limits
    if interval == "day":
        days_to_fetch = 540
    elif interval in {"60minute", "15minute", "5minute"}:
        days_to_fetch = 120
        st.info(
            f"For intraday intervals like '{selected_interval_label}', "
            f"data is shown for the last {days_to_fetch} days."
        )
    else:  # "minute"
        days_to_fetch = 7
        st.info("For 1-minute interval, showing last 7 days to stay within API limits.")

    df = get_historical_data(kite, symbol, days=days_to_fetch, interval=interval, exchange=exchange)
    if df.empty:
        st.error(
            f"No historical data for {symbol} at '{selected_interval_label}'. "
            "The stock may be new/illiquid or this timeframe is unavailable."
        )
        st.stop()

    # --- 7) Key Metrics + Price Chart ---
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
            st.metric(label="Last Price", value=f"₹{current_price:,.2f}", delta=f"{price_change:,.2f} ({pct_change:.2f}%)")
        else:
            st.metric(label="Last Price", value=f"₹{current_price:,.2f}")

    # Altair line w/ hover
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

    # --- 8) Performance & Price Vitals ---
    st.subheader("Performance & Price Vitals")

    # helper for safe number formatting
    def fmt(val, prefix="₹", nd=2):
        try:
            return f"{prefix}{float(val):,.{nd}f}"
        except Exception:
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
            else:
                st.info("Today's range data is not available yet.")

            # 52-week range (use daily candles)
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

    # --- 9) Indicators + Signals + Detailed Charts ---
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

        # Date range picker
        # --- Default date values ---
        today = datetime.today()
        default_start = today - timedelta(days=365)  # 1 year back
        default_end = today

        # --- Separate date pickers ---
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            min_value=datetime(2000, 1, 1),
            max_value=today
        )

        end_date = st.date_input(
            "End Date",
            value=default_end,
            min_value=start_date,
            max_value=today
        )

        # Convert to datetime for backtest
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())

        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            stop_loss = st.number_input("Stop Loss %", min_value=0.5, max_value=20.0, value=2.0, step=0.5) / 100
        with col_bt2:
            take_profit = st.number_input("Take Profit %", min_value=1.0, max_value=50.0, value=4.0, step=0.5) / 100

        force_signal_mode = st.checkbox("Force Signal Mode (Always Produce Trades)", value=False)

        if st.button("🚀 Run Backtest on Historical Data"):
            with st.spinner("Simulating trades..."):
                df_with_ind = apply_indicators(
                    df.copy(),
                    rsi_period=rsi_period,
                    ema_period=ema_period,
                    sma_period=sma_period
                )

                result = backtest(
                    df=df_with_ind.copy(),
                    rsi_period=rsi_period,
                    ema_period=ema_period,
                    rsi_buy=rsi_buy,
                    rsi_sell=rsi_sell,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    adx_thresh=adx_thresh,
                    use_sma=use_sma,
                    use_macd=use_macd,
                    start_date=start_date,
                    end_date=end_date,
                    force_signal=force_signal_mode
                )

                # Handle both DataFrame-only and (DataFrame, dict) returns
                if isinstance(result, tuple) and len(result) == 2:
                    trades_df, debug_counts = result
                else:
                    trades_df = result
                    debug_counts = {}

            # # Show debug counts if available
            # if debug_counts:
            #     with st.sidebar:
            #         st.write("### Backtest Debug Info")
            #         for k, v in debug_counts.items():
            #             st.write(f"{k}: {v}")

            # Validate trades_df
            if trades_df is None or not isinstance(trades_df, pd.DataFrame) or trades_df.empty:
                st.warning("No trades found.")
            elif "return_pct" not in trades_df.columns:
                st.error("Backtest completed but 'return_pct' column is missing.")
            else:
                st.success(f"✅ {len(trades_df)} trades simulated.")
                st.dataframe(
                    trades_df.style.format({
                        "entry_price": "₹{:.2f}",
                        "exit_price": "₹{:.2f}",
                        "return_pct": "{:.2f}%"
                    })
                )

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
        # Display the warning if there's not enough data for the full analysis
        st.warning(f"Not enough historical data to compute indicators and signals (requires at least {sma_period} data points, but only found {len(df)}).")
        st.warning("The price chart is shown above, but strategy analysis and backtesting are disabled.")

except Exception as e:
    st.error(f"An error occurred: {e}")
    st.exception(e)
