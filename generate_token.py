import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load credentials from your .env file
load_dotenv()

# Fetch API key and secret from environment variables
api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

if not api_key or not api_secret:
    print("❌ Error: KITE_API_KEY or KITE_API_SECRET not found in your .env file.")
    exit()

# Initialize KiteConnect
kite = KiteConnect(api_key=api_key)

# --- Step 1: Generate Login URL ---
print("🚀 Step 1: Please log in using this URL")
print(f"URL: {kite.login_url()}")
print("-" * 50)


# --- Step 2: Get Request Token ---
try:
    request_token = input("🚀 Step 2: After logging in, you will be redirected. Paste the full redirect URL here: ")
    # Extract the actual request_token from the URL query parameters
    request_token = request_token.split('request_token=')[1].split('&')[0]
    print(f"✅ Request Token Extracted: {request_token}")
    print("-" * 50)
except IndexError:
    print("\n❌ Error: Could not find 'request_token' in the URL you pasted. Please try again.")
    exit()


# --- Step 3: Generate Access Token ---
try:
    print("🚀 Step 3: Generating session to get the access token...")
    session = kite.generate_session(request_token, api_secret=api_secret)
    access_token = session["access_token"]
    
    print("\n🎉 SUCCESS! Your Access Token has been generated. 🎉")
    print("-" * 50)
    print(f"🔑 Your Access Token is: {access_token}")
    print("-" * 50)
    print("👇 NEXT ACTION 👇")
    print("Copy this token and paste it into the KITE_ACCESS_TOKEN field in your .env file (for local testing) or in your Streamlit Secrets (for deployment).")

except Exception as e:
    print(f"\n❌ Error during session generation: {e}")