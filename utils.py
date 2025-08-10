# import os
# import streamlit as st
# from kiteconnect import KiteConnect
# from dotenv import load_dotenv
# import pandas as pd
# import datetime

# # --- NEW: Load environment variables from .env file for local development ---
# load_dotenv()

# # --- MODIFIED: get_kite_client handles both deployment and local environments ---
# def get_kite_client():
#     """
#     Initializes KiteConnect by checking for a specific Streamlit Cloud environment variable
#     to differentiate between deployed and local environments.
#     """
#     # --- THIS IS THE CORRECTED LOGIC ---
#     # Check if the app is running on Streamlit Cloud
#     # This environment variable is set automatically by Streamlit's cloud platform
#     is_deployed = os.getenv('STREAMLIT_SERVER_RUNNING_ON_CLOUD') == 'true'

#     if is_deployed:
#         # Deployed on Streamlit Cloud: use st.secrets
#         print("Authentication: Using Streamlit Secrets (deployment mode).")
#         api_key = st.secrets.get("KITE_API_KEY")
#         api_secret = st.secrets.get("KITE_API_SECRET")
#         access_token = st.secrets.get("KITE_ACCESS_TOKEN")
#     else:
#         # Running on a local development server: use .env file
#         print("Authentication: Using local .env file (development mode).")
#         api_key = os.getenv("KITE_API_KEY")
#         api_secret = os.getenv("KITE_API_SECRET")
#         access_token = os.getenv("KITE_ACCESS_TOKEN")

#     if not all([api_key, api_secret, access_token]):
#         st.error("❌ API key/secret or Access Token is missing. Check your Streamlit Secrets (if deployed) or .env file (if local).")
#         st.stop()

#     kite = KiteConnect(api_key=api_key)

#     try:
#         kite.set_access_token(access_token)
#         kite.profile() # A quick check to validate the token
#     except Exception as e:
#         st.error("🔐 Session expired or token is invalid.")
#         st.info("On deployment, update the KITE_ACCESS_TOKEN in Secrets. Locally, update it in your .env file and restart the app.")
#         st.stop()
        
#     return kite
# # --- UNCHANGED: Other utility functions remain the same ---

# def get_instrument_token(kite, symbol, exchange="NSE"):
#     """
#     Returns the instrument token for a given symbol.
#     """
#     instruments = kite.instruments(exchange)
#     df = pd.DataFrame(instruments)
#     row = df[df['tradingsymbol'].str.upper() == symbol.upper()]
#     if not row.empty:
#         return int(row.iloc[0]['instrument_token'])
#     return None

# def get_daily_data(kite, symbol, days=200):
#     """
#     Fetches daily OHLCV historical data for the past `days` for the given symbol.
#     """
#     to_date = datetime.datetime.now()
#     from_date = to_date - datetime.timedelta(days=days)

#     token = get_instrument_token(kite, symbol)
#     if token is None:
#         raise ValueError(f"❌ Symbol '{symbol}' not found in instrument list.")

#     data = kite.historical_data(token, from_date, to_date, interval="day")
#     return pd.DataFrame(data)

# def get_all_nse_symbols(kite):
#     """
#     Fetches clean list of NSE EQ stock symbols with company names.
#     """
#     instruments = kite.instruments("NSE")
#     df = pd.DataFrame(instruments)

#     eq_df = df[
#         (df['instrument_type'] == 'EQ') &
#         (df['segment'] == 'NSE') &
#         (df['name'].notna()) &
#         (df['name'].str.strip() != "") &
#         (df['name'].str.len() > 2)
#     ]

#     eq_df = eq_df[eq_df['tradingsymbol'].str.match(r'^[A-Z]{2,}$')]
#     symbol_list = sorted([f"{row['tradingsymbol']} ({row['name']})" for _, row in eq_df.iterrows()])
#     return symbol_list

# # Note: The `save_token` and `TOKEN_PATH` related logic from the original file can now be removed 
# # as token handling is managed via st.secrets or the .env file. Your `generate_token.py` script
# # will simply print the access token to the console for you to copy.


import os
import streamlit as st
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import pandas as pd
import datetime

# --- Load environment variables from .env file for local development ---
load_dotenv()

# --- get_kite_client remains the same ---
def get_kite_client():
    """
    Initializes KiteConnect by checking for a specific Streamlit Cloud environment variable
    to differentiate between deployed and local environments.
    """
    is_deployed = os.getenv('STREAMLIT_SERVER_RUNNING_ON_CLOUD') == 'true'
    if is_deployed:
        print("Authentication: Using Streamlit Secrets (deployment mode).")
        api_key = st.secrets.get("KITE_API_KEY")
        api_secret = st.secrets.get("KITE_API_SECRET")
        access_token = st.secrets.get("KITE_ACCESS_TOKEN")
    else:
        print("Authentication: Using local .env file (development mode).")
        api_key = os.getenv("KITE_API_KEY")
        api_secret = os.getenv("KITE_API_SECRET")
        access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not all([api_key, api_secret, access_token]):
        st.error("❌ API key/secret or Access Token is missing. Check your Streamlit Secrets (if deployed) or .env file (if local).")
        st.stop()

    kite = KiteConnect(api_key=api_key)
    try:
        kite.set_access_token(access_token)
        kite.profile() # A quick check to validate the token
    except Exception as e:
        st.error("🔐 Session expired or token is invalid.")
        st.info("On deployment, update the KITE_ACCESS_TOKEN in Secrets. Locally, update it in your .env file and restart the app.")
        st.stop()
    return kite

# --- get_instrument_token remains the same ---
def get_instrument_token(kite, symbol, exchange="NSE"):
    instruments = kite.instruments(exchange)
    df = pd.DataFrame(instruments)
    row = df[df['tradingsymbol'].str.upper() == symbol.upper()]
    if not row.empty:
        return int(row.iloc[0]['instrument_token'])
    return None

# --- MODIFIED: Renamed get_daily_data and added 'interval' parameter ---
def get_historical_data(kite, symbol, days, interval, exchange="NSE"):
    """
    Fetches historical data for a given symbol, number of days, and interval.
    """
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=days)
    token = get_instrument_token(kite, symbol, exchange)
    if token is None:
        raise ValueError(f"❌ Symbol '{symbol}' not found in instrument list.")
    
    # Use the 'interval' parameter in the API call
    data = kite.historical_data(token, from_date, to_date, interval=interval)
    return pd.DataFrame(data)

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
    Fetches and combines a list of all equity symbols from the specified exchanges.

    Args:
        kite: An initialized KiteConnect object.
        exchanges: A list of exchanges to fetch (e.g., ['NSE', 'BSE']).

    Returns:
        A sorted list of formatted strings for each stock symbol.
    """
    # Create a list to hold the instrument data from each exchange
    all_instruments_df = []
    
    # Loop through each specified exchange
    for exchange in exchanges:
        try:
            instruments = kite.instruments(exchange)
            all_instruments_df.append(pd.DataFrame(instruments))
        except Exception as e:
            print(f"Could not fetch instruments for {exchange}. Error: {e}")

    # Combine all dataframes into one
    if not all_instruments_df:
        return [] # Return empty list if no instruments were fetched
        
    df = pd.concat(all_instruments_df)

    # We use regex word boundaries (\b) to avoid matching parts of words (e.g., 'fund' in 'fundamental')
    exclude_keywords = [
        r'\bETF\b', r'\bLIQUID\b', r'\bBEES\b', r'\bFUND\b', 
        r'\bDEBT\b', r'\bNIFTY\b', r'\bSENSEX\b'
    ]
    exclude_pattern = '|'.join(exclude_keywords)


    # Filter for active equity stocks from all specified exchanges
    eq_df = df[
        (df['instrument_type'] == 'EQ') &
        (df['name'].notna()) &
        (df['name'].str.strip() != "") &
        (df['name'].str.len() > 2) &
        # Match common stock symbol patterns
        (df['tradingsymbol'].str.match(r'^[A-Z0-9&.-]{2,}$')) &
        # Exclude debt instruments or other non-standard symbols
        (~df['tradingsymbol'].str.contains('DEBT|ETF')) &

        # Condition 3: The name should not contain any of the excluded keywords (case-insensitive)
        (~df['name'].str.contains(exclude_pattern, case=True, na=False, regex=True)) &
        
        # Condition 4: The tradingsymbol should not contain any of the excluded keywords
        (~df['tradingsymbol'].str.contains(exclude_pattern, case=True, na=False, regex=True))
   
    ]

    eq_df = eq_df[eq_df['tradingsymbol'].str.match(r'^[A-Z]{2,}$')]

    # Sort by tradingsymbol for a clean, alphabetized list
    eq_df = eq_df.sort_values(by="tradingsymbol")

    # Create "SYMBOL (EXCHANGE) - Name" format for clarity
    symbol_list = [
        f"{row['name']} - ({row['exchange']}) - ({row['tradingsymbol']})" 
        for _, row in eq_df.iterrows()
    ]
    
    return symbol_list