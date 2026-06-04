import os
import sys
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not configured in .env")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Usage: python setup_webhook.py <your_pythonanywhere_domain>")
        print("Example: python setup_webhook.py https://username.pythonanywhere.com")
        sys.exit(1)
        
    domain = sys.argv[1].strip().rstrip("/")
    webhook_url = f"{domain}/webhook"
    
    print(f"Registering webhook: {webhook_url}...")
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        print("Telegram Response:")
        print(result)
        if result.get("ok"):
            print("🎉 Webhook registered successfully!")
        else:
            print("❌ Failed to register webhook.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
