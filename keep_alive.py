import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ WaifuBot is Online and Awake!"

def run():
    # Render uses the 'PORT' environment variable. 
    # If it doesn't exist (local testing), it defaults to 8080.
    port = int(os.environ.get("PORT", 8080))
    
    # host='0.0.0.0' is required for Render to "see" the app
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """
    Starts the Flask server in a background thread 
    so it doesn't block the Telegram bot from running.
    """
    t = Thread(target=run)
    t.daemon = True  # Ensures the thread closes when the main bot stops
    t.start()
