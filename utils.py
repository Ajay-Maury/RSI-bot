import os
import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# --- Load environment variables for local development ---
load_dotenv()

# --- NEW: Custom Exception for Token Errors ---
class TokenException(Exception):
    pass

def get_kite_client():
    """
    Initialize KiteConnect.
    MODIFIED: Raises TokenException on authentication failure instead of stopping the app.
    """
    is_deployed = os.getenv("STREAMLIT_SERVER_RUNNING_ON_CLOUD") == "true"
    if is_deployed:
        api_key = st.secrets.get("KITE_API_KEY")
        api_secret = st.secrets.get("KITE_API_SECRET")
        access_token = st.secrets.get("KITE_ACCESS_TOKEN")
    else:
        api_key = os.getenv("KITE_API_KEY")
        api_secret = os.getenv("KITE_API_SECRET")
        access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not all([api_key, api_secret, access_token]):
        # Raise the custom exception if credentials are not found
        raise TokenException("API key/secret or Access Token is missing. Check your configuration.")

    kite = KiteConnect(api_key=api_key)
    try:
        kite.set_access_token(access_token)
        kite.profile()  # Sanity check to see if the token is valid
    except Exception:
        # Raise the custom exception if the token is expired/invalid
        raise TokenException("Session expired or token is invalid.")
    
    return kite


def get_instrument_token(kite, symbol, exchange="NSE"):
    """
    Return instrument token for an exchange + symbol pair.
    """
    instruments = kite.instruments(exchange)
    df = pd.DataFrame(instruments)
    row = df[df["tradingsymbol"].str.upper() == symbol.upper()]
    if not row.empty:
        return int(row.iloc[0]["instrument_token"])
    return None


def _normalize_hist(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure expected columns and types, sorted by date ascending.
    """
    if df.empty:
        return df
    df = df.copy()
    # Kite returns timezone-aware datetimes; remove tz for easier plotting and ensure ascending
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date")
    # Ensure numeric types
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_historical_data(kite, symbol, days, interval, exchange="NSE") -> pd.DataFrame:
    """
    Fetch historical OHLCV for symbol over 'days' with the given 'interval'.
    """
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=days)
    token = get_instrument_token(kite, symbol, exchange)
    if token is None:
        raise ValueError(
            f"❌ Symbol '{symbol}' not found in instrument list for {exchange}."
        )

    data = kite.historical_data(token, from_date, to_date, interval=interval)
    return _normalize_hist(pd.DataFrame(data))


# # --- get_all_nse_symbols ---

def get_all_nse_symbols(kite):
    """
    Fetches all NSE Equity symbols and sorts them alphabetically.
    This version is fast as it does not require an extra API call for live quotes.
    """
    # 1. Fetch the master list of all instruments
    instruments = kite.instruments("NSE")
    df = pd.DataFrame(instruments)

    # 2. Filter for active, regular equity stocks to keep the list clean and relevant
    eq_df = df[
        (df['instrument_type'] == 'EQ') &
        (df['segment'] == 'NSE') &
        (df['name'].notna()) &
        (df['name'].str.strip() != "") &
        (df['name'].str.len() > 2)
    ]
    eq_df = eq_df[eq_df['tradingsymbol'].str.match(r'^[A-Z]{2,}$')]

    # 3. Create a formatted list and sort it alphabetically
    symbol_list = sorted([
        f"{row['name']} - (NSE) - ({row['tradingsymbol']})" for _, row in eq_df.iterrows()
    ])
    
    return symbol_list


# # --- get all NSE and BSE symbols ---
def get_all_stock_symbols(kite, exchanges=['NSE', 'BSE']):
    """
    Get a clean list of active equity symbols across exchanges.
    Returns: ["Company Name - (NSE) - (RELIANCE)", ...]
    """
    all_instruments = []
    for ex in exchanges:
        try:
            all_instruments.append(pd.DataFrame(kite.instruments(ex)))
        except Exception as e:
            print(f"Could not fetch instruments for {ex}. Error: {e}")

    if not all_instruments:
        return []

    df = pd.concat(all_instruments, ignore_index=True)

    exclude_keywords = [
        r"\bETF\b",
        r"\bLIQUID\b",
        r"\bBEES\b",
        r"\bFUND\b",
        r"\bDEBT\b",
        r"\bNIFTY\b",
        r"\bSENSEX\b",
    ]
    exclude_pattern = "|".join(exclude_keywords)

    eq_df = df[
        (df["instrument_type"] == "EQ")
        & (df["name"].notna())
        & (df["name"].str.strip() != "")
        & (df["name"].str.len() > 2)
        & (df["tradingsymbol"].str.match(r"^[A-Z0-9&.-]{2,}$"))
        # Exclude debt instruments or other non-standard symbols
        & (~df['tradingsymbol'].str.contains('DEBT|ETF'))
        & (~df["name"].str.contains(exclude_pattern, case=False, na=False, regex=True))
        & (
            ~df["tradingsymbol"].str.contains(
                exclude_pattern, case=False, na=False, regex=True
            )
        )
    ].copy()

    # Keep only columns we need
    eq_df["exchange"] = eq_df["exchange"].str.upper()
    eq_df = eq_df.sort_values(by="tradingsymbol")

    symbol_list = [
        f"{row['name']} - ({row['exchange']}) - ({row['tradingsymbol']})"
        for _, row in eq_df.iterrows()
    ]
    return symbol_list
