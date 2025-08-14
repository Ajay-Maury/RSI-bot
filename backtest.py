import pandas as pd
import streamlit as st


def backtest(
    df,
    rsi_period,
    ema_period,
    rsi_buy,
    rsi_sell,
    stop_loss,
    take_profit,
    adx_thresh=0,
    use_sma=False,
    use_macd=False,
    start_date=None,
    end_date=None,
    force_signal=False,
):
    # Standardize date column name
    if "Date" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    # Apply date filters
    if start_date:
        df = df[df["Date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["Date"] <= pd.to_datetime(end_date)]

    if df.empty:
        return (
            pd.DataFrame(
                columns=[
                    "date",
                    "entry_price",
                    "exit_price",
                    "return_pct",
                    "equity_curve",
                ]
            ),
            {},
        )

    # --- Debug counts ---
    debug_counts = {}
    rsi_cond_buy = df["rsi"] < rsi_buy
    rsi_cond_sell = df["rsi"] > rsi_sell
    debug_counts["RSI Buy Matches"] = rsi_cond_buy.sum()
    debug_counts["RSI Sell Matches"] = rsi_cond_sell.sum()

    if adx_thresh > 0:
        adx_cond = df["adx"] > adx_thresh
    else:
        adx_cond = pd.Series(True, index=df.index)
    debug_counts["ADX Matches"] = adx_cond.sum()

    if use_sma and "SMA_200" in df.columns:
        sma_cond = df["Close"] > df["SMA_200"]
    else:
        sma_cond = pd.Series(True, index=df.index)
    debug_counts["SMA Matches"] = sma_cond.sum()

    if use_macd and "MACD" in df.columns and "Signal" in df.columns:
        macd_cond = df["MACD"] > df["Signal"]
    else:
        macd_cond = pd.Series(True, index=df.index)
    debug_counts["MACD Matches"] = macd_cond.sum()

    # Backtest loop
    trades = []
    position = None
    entry_price = None
    entry_date = None

    for i in range(len(df)):
        if position is None:
            if (
                rsi_cond_buy.iloc[i]
                and adx_cond.iloc[i]
                and sma_cond.iloc[i]
                and macd_cond.iloc[i]
            ) or force_signal:
                position = "LONG"
                entry_price = df["close"].iloc[i]
                entry_date = df["Date"].iloc[i]
        else:
            exit_now = (
                rsi_cond_sell.iloc[i]
                and adx_cond.iloc[i]
                and sma_cond.iloc[i]
                and macd_cond.iloc[i]
            ) or force_signal
            if exit_now:
                exit_price = df["close"].iloc[i]
                exit_date = df["Date"].iloc[i]
                pct_return = (exit_price - entry_price) / entry_price * 100
                trades.append(
                    {
                        "date": exit_date,  # <- Standardized date for plotting
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return_pct": pct_return,
                    }
                )
                position = None

    trades_df = pd.DataFrame(trades)

    # Ensure required columns exist
    if not trades_df.empty:
        trades_df["equity_curve"] = (1 + trades_df["return_pct"] / 100).cumprod()
    else:
        trades_df = pd.DataFrame(
            columns=["date", "entry_price", "exit_price", "return_pct", "equity_curve"]
        )

    return trades_df, debug_counts
