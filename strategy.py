from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator

def apply_indicators(df, rsi_period=14, ema_period=50, sma_period=200):
    """
    Adds RSI, EMA, SMA, ADX, MACD & MACD Signal to the dataframe.
    Assumes df has columns: date, open, high, low, close, volume (date ascending).
    """
    df = df.copy()
    df["rsi"] = RSIIndicator(df["close"], window=rsi_period).rsi()
    df["ema"] = EMAIndicator(df["close"], window=ema_period).ema_indicator()
    df["sma"] = SMAIndicator(df["close"], window=sma_period).sma_indicator()

    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["adx"] = adx.adx()

    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    return df

def check_signal(df, rsi_buy, rsi_sell, adx_thresh=20, use_sma=False, use_macd=False):
    """
    Generates one of: 'BUY', 'SELL', or 'HOLD' based on the last two rows.
    - Entry: RSI < rsi_buy AND EMA bullish crossover (close > ema & prev close <= prev ema)
    - Exit:  RSI > rsi_sell AND close < ema
    Optional filters: price > SMA(200), ADX >= thresh, MACD > signal
    """
    if len(df) < 2:
        return "HOLD"

    row = df.iloc[-1]
    prev = df.iloc[-2]

    rsi_entry = (row["rsi"] < rsi_buy) and (row["close"] > row["ema"]) and (prev["close"] <= prev["ema"])
    exit_signal = (row["rsi"] > rsi_sell) and (row["close"] < row["ema"])

    sma_filter = (row["close"] > row["sma"]) if use_sma else True
    adx_filter = (row["adx"] >= adx_thresh)
    macd_filter = (row["macd"] > row["macd_signal"]) if use_macd else True

    if rsi_entry and sma_filter and adx_filter and macd_filter:
        return "BUY"
    elif exit_signal:
        return "SELL"
    return "HOLD"
