from kiteconnect import KiteConnect
import yaml
import datetime
import pandas as pd

def load_config():
    with open("config.yaml", 'r') as f:
        return yaml.safe_load(f)

def init_kite(api_key, access_token):
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite

def get_daily_data(kite, symbol, days=100):
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=days)
    data = kite.historical_data(kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]['instrument_token'],
                                from_date, to_date, interval="day")
    return pd.DataFrame(data)

def get_ltp(kite, symbol):
    return kite.ltp(f'NSE:{symbol}')[f'NSE:{symbol}']['last_price']

def get_instrument_token(kite, symbol, exchange="NSE"):
    instruments = kite.instruments(exchange)
    df = pd.DataFrame(instruments)
    row = df[df['tradingsymbol'] == symbol]
    if not row.empty:
        return int(row.iloc[0]['instrument_token'])
    else:
        return None
