
# import streamlit as st
# import pandas as pd
# import altair as alt
# from utils import get_kite_client, get_all_nse_symbols, get_historical_data
# from strategy import apply_indicators, check_signal
# from backtest import backtest

# # --- 1. Streamlit App Configuration ---
# st.set_page_config(page_title="RSI Trading Dashboard", layout="wide")
# st.title("📈 RSI + Multi-Indicator Algo Trading Dashboard")

# # --- 2. Kite API Initialization ---
# try:
#     kite = get_kite_client()
# except Exception as e:
#     st.error(f"Failed to initialize Kite client. Please check your credentials. Error: {e}")
#     st.stop()

# # --- 3. Load NSE Symbols (Cached for performance) ---
# @st.cache_data
# def load_symbols(_kite_client):
#     return get_all_nse_symbols(_kite_client)

# try:
#     all_symbols = load_symbols(kite)
#     st.caption(f"✅ Loaded {len(all_symbols)} NSE equity symbols.")
# except Exception as e:
#     st.error(f"Failed to load stock symbols from Kite. Error: {e}")
#     st.stop()

# # --- 4. Sidebar for All Parameters ---
# st.sidebar.header("⚙️ Data & Strategy Parameters")
# interval_options = {
#     "Daily": "day", "60 Minute": "60minute", "15 Minute": "15minute",
#     "5 Minute": "5minute", "Minute": "minute"
# }
# selected_interval_label = st.sidebar.selectbox("Select Chart Interval", options=list(interval_options.keys()))
# interval = interval_options[selected_interval_label]

# st.sidebar.header("📊 Indicator Parameters")
# rsi_period = st.sidebar.slider("RSI Period", min_value=5, max_value=30, value=14)
# ema_period = st.sidebar.slider("EMA Period (for crossover)", min_value=10, max_value=100, value=50)
# sma_period = 200
# rsi_buy = st.sidebar.slider("RSI Buy Threshold (Enter when RSI is below)", min_value=10, max_value=50, value=30)
# rsi_sell = st.sidebar.slider("RSI Sell Threshold (Exit when RSI is above)", min_value=50, max_value=90, value=70)

# st.sidebar.header("🔧 Optional Filters")
# adx_thresh = st.sidebar.slider("ADX Minimum Strength", min_value=10, max_value=50, value=20)
# use_sma = st.sidebar.checkbox("Use 200-Day SMA Filter (Price > SMA)", value=True)
# use_macd = st.sidebar.checkbox("Use MACD Filter (MACD > Signal)", value=True)


# # --- 5. Main Content: Symbol Selection ---
# selected_label = st.selectbox(
#     "🔍 Search & Select NSE Stock Symbol",
#     options=all_symbols,
#     index=None,
#     placeholder="Start typing a symbol like RELIANCE, INFY, TCS...",
# )

# if not selected_label:
#     st.info("Please select a stock to begin analysis.")
#     st.stop()

# symbol = selected_label.split(" ")[0]

# # --- 6. Data Fetching and Analysis ---
# try:
#     if interval == "day":
#         days_to_fetch = 540
#     else:
#         days_to_fetch = 60
#         st.info(f"For intraday intervals like '{selected_interval_label}', data is shown for the last {days_to_fetch} days.")
    
#     df = get_historical_data(kite, symbol, days=days_to_fetch, interval=interval)
    
#     if df.empty:
#         st.error(f"No historical data returned for {symbol} at the '{selected_interval_label}' interval. The stock may be new, illiquid, or data may be unavailable for this timeframe.")
#         st.stop()

#     # ==============================================================================
#     # --- NEW: ADDED A GUARD CLAUSE TO CHECK DATAFRAME SIZE ---
#     # ==============================================================================
#     if len(df) < sma_period:
#         st.warning(f"Not enough historical data to compute indicators (requires at least {sma_period} data points, but only found {len(df)}).")
#         st.warning("Please select a longer time interval (like 'Daily') or a different stock.")
#         st.stop()


#     df_with_indicators = apply_indicators(df.copy(), rsi_period, ema_period, sma_period)
    
#     # --- 7. Display Key Metrics and Price Chart ---
#     st.markdown("---")
    
#     last_row = df_with_indicators.iloc[-1]
#     prev_row = df_with_indicators.iloc[-2]
#     current_price = last_row['close']
#     price_change = current_price - prev_row['close']
#     pct_change = (price_change / prev_row['close']) * 100

#     col1, col2 = st.columns([2, 1])
#     with col1:
#         st.subheader(f"{selected_label}")
#     with col2:
#         st.metric(label="Last Price", value=f"₹{current_price:.2f}", delta=f"{price_change:.2f} ({pct_change:.2f}%)")

#     # --- ALTAIR CHART ---
#     base = alt.Chart(df_with_indicators).encode(alt.X('date:T', axis=alt.Axis(title='Date')))
#     line = base.mark_line(color='#0068c9').encode(alt.Y('close:Q', axis=alt.Axis(title='Close Price (₹)')))
#     nearest = alt.selection_point(nearest=True, on='mouseover', fields=['date'], empty='none')

#     selectors = base.mark_point().encode(
#         opacity=alt.value(0),
#         tooltip=alt.Tooltip('custom_tooltip:N', title="Details")
#     ).add_params(nearest).transform_calculate(
#         custom_tooltip = "'₹' + format(datum.close, ',.2f') + ' (' + timeFormat(datum.date, '%b %d, %Y') + ')'"
#     )
    
#     points = line.mark_point(color='#0068c9').encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
#     rule = base.mark_rule(color='gray').encode(x='date:T').transform_filter(nearest)
    
#     layered_chart = alt.layer(line, selectors, points, rule).interactive().properties(height=400)
#     st.altair_chart(layered_chart, use_container_width=True, theme="streamlit")

#     # --- 8. Display Current Signal and Detailed Charts ---
#     signal = check_signal(df_with_indicators, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)
#     if signal == 'BUY': st.success(f"📢 Current Signal for Your Strategy: **{signal}**")
#     elif signal == 'SELL': st.error(f"📢 Current Signal for Your Strategy: **{signal}**")
#     else: st.info(f"📢 Current Signal for Your Strategy: **{signal}**")
#     with st.expander("Show Detailed Indicator Charts (RSI, EMA, ADX, MACD)"):
#         st.line_chart(df_with_indicators.set_index('date')[['close', 'ema', 'sma']], use_container_width=True)
#         st.line_chart(df_with_indicators.set_index('date')['rsi'], use_container_width=True)
#         st.line_chart(df_with_indicators.set_index('date')[['adx']], use_container_width=True)
#         st.line_chart(df_with_indicators.set_index('date')[['macd', 'macd_signal']], use_container_width=True)

#     # --- 9. Backtesting Section ---
#     st.markdown("---")
#     st.header("🔁 Backtest Your Strategy")
#     col_bt1, col_bt2 = st.columns(2)
#     with col_bt1:
#         stop_loss = st.number_input("Stop Loss %", min_value=0.5, max_value=20.0, value=2.0, step=0.5) / 100
#     with col_bt2:
#         take_profit = st.number_input("Take Profit %", min_value=1.0, max_value=50.0, value=4.0, step=0.5) / 100
#     if st.button("🚀 Run Backtest on Historical Data"):
#         with st.spinner("Simulating trades..."):
#             trades_df = backtest(df.copy(), rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd)
#         if trades_df.empty:
#             st.warning("No trades were generated for this configuration.")
#         else:
#             st.success(f"✅ {len(trades_df)} trades simulated.")
#             st.dataframe(trades_df.style.format({'entry_price': "₹{:.2f}", 'exit_price': "₹{:.2f}",'return_pct': "{:.2f}%"}))
#             win_rate = (trades_df['return_pct'] > 0).mean() * 100
#             avg_return = trades_df['return_pct'].mean()
#             total_return = (1 + trades_df['return_pct'] / 100).prod() - 1
#             st.subheader("Performance Metrics")
#             m_col1, m_col2, m_col3 = st.columns(3)
#             m_col1.metric("🏆 Win Rate", f"{win_rate:.2f}%")
#             m_col2.metric("📈 Avg. Return/Trade", f"{avg_return:.2f}%")
#             m_col3.metric("💰 Total Return", f"{total_return * 100:.2f}%")
#             trades_df['equity_curve'] = (1 + trades_df['return_pct'] / 100).cumprod()
#             st.line_chart(trades_df.set_index('date')['equity_curve'])

# except Exception as e:
#     st.error(f"An error occurred: {e}")
#     st.exception(e)

import streamlit as st
import pandas as pd
import altair as alt
from utils import get_kite_client, get_all_nse_symbols, get_historical_data
from strategy import apply_indicators, check_signal
from backtest import backtest

# --- 1. Streamlit App Configuration ---
st.set_page_config(page_title="RSI Trading Dashboard", layout="wide")
st.title("📈 RSI + Multi-Indicator Algo Trading Dashboard")

# --- 2. Kite API Initialization ---
try:
    kite = get_kite_client()
except Exception as e:
    st.error(f"Failed to initialize Kite client. Please check your credentials. Error: {e}")
    st.stop()

# --- 3. Load NSE Symbols (Cached for performance) ---
@st.cache_data
def load_symbols(_kite_client):
    return get_all_nse_symbols(_kite_client)

try:
    all_symbols = load_symbols(kite)
    st.caption(f"✅ Loaded {len(all_symbols)} NSE equity symbols.")
except Exception as e:
    st.error(f"Failed to load stock symbols from Kite. Error: {e}")
    st.stop()

# --- 4. Sidebar for All Parameters ---
st.sidebar.header("⚙️ Data & Strategy Parameters")
interval_options = {
    "Daily": "day", "60 Minute": "60minute", "15 Minute": "15minute",
    "5 Minute": "5minute", "Minute": "minute"
}
selected_interval_label = st.sidebar.selectbox("Select Chart Interval", options=list(interval_options.keys()))
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


# --- 5. Main Content: Symbol Selection ---
selected_label = st.selectbox(
    "🔍 Search & Select NSE Stock Symbol",
    options=all_symbols,
    index=None,
    placeholder="Start typing a symbol like RELIANCE, INFY, TCS...",
)

if not selected_label:
    st.info("Please select a stock to begin analysis.")
    st.stop()

symbol = selected_label.split(" ")[0]

# --- 6. Data Fetching and Analysis ---
try:
    if interval == "day":
        days_to_fetch = 540
    else:
        days_to_fetch = 60
        st.info(f"For intraday intervals like '{selected_interval_label}', data is shown for the last {days_to_fetch} days.")
    
    df = get_historical_data(kite, symbol, days=days_to_fetch, interval=interval)
    
    if df.empty:
        st.error(f"No historical data returned for {symbol} at the '{selected_interval_label}' interval. The stock may be new, illiquid, or data may be unavailable for this timeframe.")
        st.stop()

    # --- 7. Display Key Metrics and Price Chart (This will now always run if df is not empty) ---
    st.markdown("---")
    
    current_price = df.iloc[-1]['close']
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"{selected_label}")
    with col2:
        # Conditionally calculate and display the daily change if we have more than one day of data
        if len(df) > 1:
            prev_price = df.iloc[-2]['close']
            price_change = current_price - prev_price
            pct_change = (price_change / prev_price) * 100
            st.metric(label="Last Price", value=f"₹{current_price:.2f}", delta=f"{price_change:.2f} ({pct_change:.2f}%)")
        else:
            st.metric(label="Last Price", value=f"₹{current_price:.2f}")

    # --- ALTAIR CHART ---
    base = alt.Chart(df).encode(alt.X('date:T', axis=alt.Axis(title='Date')))
    line = base.mark_line(color='#0068c9').encode(alt.Y('close:Q', axis=alt.Axis(title='Close Price (₹)')))
    nearest = alt.selection_point(nearest=True, on='mouseover', fields=['date'], empty='none')

    selectors = base.mark_point().encode(
        opacity=alt.value(0),
        tooltip=alt.Tooltip('custom_tooltip:N', title="Details")
    ).add_params(nearest).transform_calculate(
        custom_tooltip = "'₹' + format(datum.close, ',.2f') + ' (' + timeFormat(datum.date, '%b %d, %Y') + ')'"
    )
    
    points = line.mark_point(color='#0068c9').encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    rule = base.mark_rule(color='gray').encode(x='date:T').transform_filter(nearest)
    
    layered_chart = alt.layer(line, selectors, points, rule).interactive().properties(height=400)
    st.altair_chart(layered_chart, use_container_width=True, theme="streamlit")

    # --- 8. Conditional Indicator and Backtesting Sections ---
    # Check if we have enough data to calculate all indicators
    if len(df) >= sma_period:
        df_with_indicators = apply_indicators(df.copy(), rsi_period, ema_period, sma_period)
        signal = check_signal(df_with_indicators, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)
        
        if signal == 'BUY': st.success(f"📢 Current Signal for Your Strategy: **{signal}**")
        elif signal == 'SELL': st.error(f"📢 Current Signal for Your Strategy: **{signal}**")
        else: st.info(f"📢 Current Signal for Your Strategy: **{signal}**")

        with st.expander("Show Detailed Indicator Charts (RSI, EMA, ADX, MACD)"):
            st.line_chart(df_with_indicators.set_index('date')[['close', 'ema', 'sma']], use_container_width=True)
            st.line_chart(df_with_indicators.set_index('date')['rsi'], use_container_width=True)
            st.line_chart(df_with_indicators.set_index('date')[['adx']], use_container_width=True)
            st.line_chart(df_with_indicators.set_index('date')[['macd', 'macd_signal']], use_container_width=True)

        st.markdown("---")
        st.header("🔁 Backtest Your Strategy")
        
        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            stop_loss = st.number_input("Stop Loss %", min_value=0.5, max_value=20.0, value=2.0, step=0.5) / 100
        with col_bt2:
            take_profit = st.number_input("Take Profit %", min_value=1.0, max_value=50.0, value=4.0, step=0.5) / 100
        
        if st.button("🚀 Run Backtest on Historical Data"):
            with st.spinner("Simulating trades..."):
                trades_df = backtest(df.copy(), rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd)
            
            if trades_df.empty:
                st.warning("No trades were generated for this configuration.")
            else:
                st.success(f"✅ {len(trades_df)} trades simulated.")
                st.dataframe(trades_df.style.format({'entry_price': "₹{:.2f}", 'exit_price': "₹{:.2f}",'return_pct': "{:.2f}%"}))
                
                win_rate = (trades_df['return_pct'] > 0).mean() * 100
                avg_return = trades_df['return_pct'].mean()
                total_return = (1 + trades_df['return_pct'] / 100).prod() - 1
                
                st.subheader("Performance Metrics")
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("🏆 Win Rate", f"{win_rate:.2f}%")
                m_col2.metric("📈 Avg. Return/Trade", f"{avg_return:.2f}%")
                m_col3.metric("💰 Total Return", f"{total_return * 100:.2f}%")

                trades_df['equity_curve'] = (1 + trades_df['return_pct'] / 100).cumprod()
                st.line_chart(trades_df.set_index('date')['equity_curve'])
    else:
        # Display the warning if there's not enough data for the full analysis
        st.warning(f"Not enough historical data to compute indicators and signals (requires at least {sma_period} data points, but only found {len(df)}).")
        st.warning("The price chart is shown above, but strategy analysis and backtesting are disabled.")

except Exception as e:
    st.error(f"An error occurred: {e}")
    st.exception(e)