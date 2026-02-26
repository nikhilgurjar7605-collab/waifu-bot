from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ WaifuBot is Online and Awake!"

def run():
    # host='0.0.0.0' allows external access
    # port=8080 is the standard for web pings
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """
    Starts the Flask server in a background thread 
    so it doesn't block the Telegram bot from running.
    """
    t = Thread(target=run)
    t.start()
