# import pandas as pd
# from strategy import apply_indicators, check_signal

# def backtest(df, rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd):
#     df = apply_indicators(df)
#     df = df.dropna().reset_index(drop=True)
#     trades = []
#     position = None
#     entry_price = 0

#     for i in range(1, len(df)):
#         sub_df = df.iloc[:i+1]
#         signal = check_signal(sub_df, rsi_buy, rsi_sell, adx_thresh, use_sma, use_macd)
#         row = df.iloc[i]
#         price = row['close']

#         if position is None and signal == 'BUY':
#             position = 'BUY'
#             entry_price = price
#             entry_date = row['date']
#         elif position == 'BUY':
#             pnl = (price - entry_price) / entry_price
#             if pnl >= take_profit or pnl <= -stop_loss or signal == 'SELL':
#                 trades.append({
#                     "entry_date": entry_date,
#                     "exit_date": row['date'],
#                     "entry_price": entry_price,
#                     "exit_price": price,
#                     "return_pct": pnl * 100
#                 })
#                 position = None

#     return pd.DataFrame(trades)

import pandas as pd
from strategy import apply_indicators

def backtest(df, rsi_buy, rsi_sell, stop_loss, take_profit, adx_thresh, use_sma, use_macd):
    # Step 1: Apply indicators ONCE to the entire dataframe before the loop.
    df = apply_indicators(df)
    df = df.dropna().reset_index(drop=True)
    
    trades = []
    position = None
    entry_price = 0
    entry_date = None

    # Step 2: Loop through the pre-calculated data. Start from index 1 to allow for previous row checks.
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        price = row['close']

        # Step 3: Check for entry and exit signals directly inside the loop.
        # --- Entry Signal Logic (from strategy.py) ---
        rsi_crossover_buy = row['rsi'] < rsi_buy and row['close'] > row['ema'] and prev_row['close'] <= prev_row['ema']
        sma_filter = row['close'] > row['sma'] if use_sma else True
        adx_filter = row['adx'] >= adx_thresh
        macd_filter = row['macd'] > row['macd_signal'] if use_macd else True
        
        entry_signal = rsi_crossover_buy and sma_filter and adx_filter and macd_filter

        # --- Exit Signal Logic (from strategy.py) ---
        exit_signal = row['rsi'] > rsi_sell and row['close'] < row['ema']

        # Step 4: Manage trade positions
        if position is None and entry_signal:
            position = 'BUY'
            entry_price = price
            entry_date = row['date']
        
        elif position == 'BUY':
            pnl = (price - entry_price) / entry_price
            # Check for exit conditions: stop loss, take profit, or an explicit SELL signal
            if pnl >= take_profit or pnl <= -stop_loss or exit_signal:
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row['date'],
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return_pct": pnl * 100
                })
                position = None

    return pd.DataFrame(trades)