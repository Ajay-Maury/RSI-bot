import webbrowser
import threading
from flask import Flask, request
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv, set_key

# Load env variables
load_dotenv()
ENV_PATH = ".env"

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

kite = KiteConnect(api_key=api_key)
app = Flask(__name__)

@app.route("/")
def login():
    request_token = request.args.get("request_token")
    if not request_token:
        return "❌ No request_token found in URL!"

    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        # Save the new token to .env
        set_key(ENV_PATH, "KITE_ACCESS_TOKEN", access_token)

        print(f"✅ Access token saved to .env: {access_token}")
        return "✅ Token received and saved to .env. You can close this tab."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def run_flask():
    app.run(port=8000)

def start_auto_login():
    threading.Thread(target=run_flask).start()
    login_url = kite.login_url()
    print("🌐 Opening login URL in browser...")
    webbrowser.open(login_url)

if __name__ == "__main__":
    start_auto_login()
