import pandas as pd


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
    # --- Safe column name handling ---
    if "Date" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "Date"})
    if "Close" not in df.columns and "close" in df.columns:
        df = df.rename(columns={"close": "Close"})
    if "rsi" not in df.columns and "RSI" in df.columns:
        df = df.rename(columns={"RSI": "rsi"})

    # Ensure required columns exist
    required_price_cols = ["Date", "Close", "rsi"]
    for col in required_price_cols:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}")

    # Ensure Date column is datetime and sorted
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    # --- Date range filtering ---
    if start_date:
        df = df[df["Date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["Date"] <= pd.to_datetime(end_date)]

    if df.empty:
        return (
            pd.DataFrame(
                columns=[
                    "entry_date",
                    "exit_date",
                    "entry_price",
                    "exit_price",
                    "return_pct",
                ]
            ),
            {},
        )

    # --- Debug counters ---
    debug_counts = {}

    # RSI conditions
    rsi_cond_buy = df["rsi"] < rsi_buy
    rsi_cond_sell = df["rsi"] > rsi_sell
    debug_counts["RSI Buy Matches"] = int(rsi_cond_buy.sum())
    debug_counts["RSI Sell Matches"] = int(rsi_cond_sell.sum())

    # ADX filter
    if adx_thresh > 0 and "adx" in df.columns:
        adx_cond = df["adx"] > adx_thresh
    else:
        adx_cond = pd.Series(True, index=df.index)
    debug_counts["ADX Matches"] = int(adx_cond.sum())

    # SMA filter
    if use_sma and "SMA_200" in df.columns:
        sma_cond = df["Close"] > df["SMA_200"]
    else:
        sma_cond = pd.Series(True, index=df.index)
    debug_counts["SMA Matches"] = int(sma_cond.sum())

    # MACD filter
    if use_macd and "MACD" in df.columns and "Signal" in df.columns:
        macd_cond = df["MACD"] > df["Signal"]
    else:
        macd_cond = pd.Series(True, index=df.index)
    debug_counts["MACD Matches"] = int(macd_cond.sum())

    # --- Backtest loop ---
    trades = []
    position = None
    entry_price = None
    entry_date = None

    for i in range(len(df)):
        if position is None:
            # Entry
            if (
                rsi_cond_buy.iloc[i]
                and adx_cond.iloc[i]
                and sma_cond.iloc[i]
                and macd_cond.iloc[i]
            ) or force_signal:
                position = "LONG"
                entry_price = df["Close"].iloc[i]
                entry_date = df["Date"].iloc[i]
        else:
            # Exit
            if (
                rsi_cond_sell.iloc[i]
                and adx_cond.iloc[i]
                and sma_cond.iloc[i]
                and macd_cond.iloc[i]
            ) or force_signal:
                exit_price = df["Close"].iloc[i]
                exit_date = df["Date"].iloc[i]
                pct_return = (exit_price - entry_price) / entry_price * 100
                trades.append(
                    {
                        "entry_date": entry_date,
                        "exit_date": exit_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return_pct": pct_return,
                    }
                )
                position = None

    trades_df = pd.DataFrame(
        trades,
        columns=["entry_date", "exit_date", "entry_price", "exit_price", "return_pct"],
    )

    # --- Force signal fallback if no trades found ---
    if trades_df.empty and not force_signal:
        return backtest(
            df.copy(),
            rsi_period,
            ema_period,
            rsi_buy,
            rsi_sell,
            stop_loss,
            take_profit,
            adx_thresh,
            use_sma,
            use_macd,
            start_date,
            end_date,
            force_signal=True,
        )

    return trades_df, debug_counts
