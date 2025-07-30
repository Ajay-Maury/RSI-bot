# auto_token_refresh.py

import webbrowser
import threading
import yaml
from flask import Flask, request
from kiteconnect import KiteConnect

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

api_key = config["api"]["api_key"]
api_secret = config["api"]["api_secret"]

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

        # Save back to config
        config["api"]["access_token"] = access_token
        with open("config.yaml", "w") as f:
            yaml.dump(config, f)

        print(f"✅ Access token saved: {access_token}")
        return "✅ Token received and saved. You can close this tab."

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
