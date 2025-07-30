import pandas as pd
from strategy import apply_indicators, check_signal

def backtest(df, rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd):
    df = apply_indicators(df)
    df = df.dropna().reset_index(drop=True)
    trades = []
    position = None
    entry_price = 0

    for i in range(1, len(df)):
        sub_df = df.iloc[:i+1]
        signal = check_signal(sub_df, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)
        row = df.iloc[i]
        price = row['close']

        if position is None and signal == 'BUY':
            position = 'BUY'
            entry_price = price
            entry_date = row['date']
        elif position == 'BUY':
            pnl = (price - entry_price) / entry_price
            if pnl >= take_profit or pnl <= -stop_loss or signal == 'SELL':
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row['date'],
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return_pct": pnl * 100
                })
                position = None

    return pd.DataFrame(trades)