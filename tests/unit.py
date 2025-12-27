import requests

# -----------------------------------------
# CONFIG
# -----------------------------------------

# External URL, as seen from the internet or your client
# Nginx config: location /messenger { proxy_pass http://hermes:8000; }
BASE_URL = "https://sobbingly-hydrochloric-joel.ngrok-free.dev/messenger"

HERMES_TOKEN = "changeme"

EMAIL_ADDRESS = "oluwajuwonadedowole@gmail.com"
TELEGRAM_CHAT_ID = "6965644872"               # your Telegram chat id
TELEGRAM_BOT_TOKEN = "8574417586:AAHHVuF-grpLXaRKaKoNWvS6_SU1v2pEp5w"  # replace with real token

HEADERS_JSON = {"Content-Type": "application/json"}


# -----------------------------------------
# UTILITIES
# -----------------------------------------

def print_response(resp: requests.Response, label: str = ""):
    """Pretty-print the HTTP response."""
    prefix = f"[{label}] " if label else ""
    print(f"{prefix}Status: {resp.status_code}")
    print(f"{prefix}URL: {resp.url}")
    try:
        print(f"{prefix}JSON body:", resp.json())
    except Exception:
        print(f"{prefix}Text body:", resp.text)
    print("-" * 80)


# -----------------------------------------
# 1. ENQUEUE AN EMAIL
# -----------------------------------------

def enqueue_email():
    """
    Queue an email via Hermes /messenger/enqueue (verification template).
    This hits Nginx, which proxies to the Hermes upstream.
    """
    url = f"{BASE_URL}/enqueue"   # -> /messenger/enqueue on Nginx
    params = {"token": HERMES_TOKEN}
    payload = {
        "channel": "email",
        "sender": "Clash of Prodigies <no-reply@clashofprodigies.org>",
        "to": EMAIL_ADDRESS,
        "subject": "Account Verification",
        "data": {
            "username": "Benjamin",
            "verification_link": "https://prodigy.example/verify?token=test-token",
        },
        "idempotency_key": "email-verification-test-001",
    }

    print("[enqueue_email] About to POST email job to Hermes through Nginx")
    print(f"[enqueue_email] URL: {url}")
    print(f"[enqueue_email] To: {payload['to']}, Subject: {payload['subject']}")
    resp = requests.post(url, params=params, headers=HEADERS_JSON, json=payload)
    print_response(resp, "enqueue_email")


# -----------------------------------------
# 2. ENQUEUE A TELEGRAM MESSAGE
# -----------------------------------------

def enqueue_telegram():
    """
    Queue a Telegram message via Hermes /messenger/enqueue using default.md template.
    """
    url = f"{BASE_URL}/enqueue"   # -> /messenger/enqueue
    params = {"token": HERMES_TOKEN}
    payload = {
        "channel": "telegram",
        "sender": "Clash of Prodigies",
        "to": TELEGRAM_CHAT_ID,
        "subject": "default",  # name of the template
        "data": {
            "username": "Benjamin",
            "role": "tester",
        },
        "idempotency_key": "telegram-default-test-001",
    }

    print("[enqueue_telegram] About to POST Telegram job to Hermes through Nginx")
    print(f"[enqueue_telegram] URL: {url}")
    print(f"[enqueue_telegram] Chat ID: {payload['to']}, Template: {payload['subject']}")
    resp = requests.post(url, params=params, headers=HEADERS_JSON, json=payload)
    print_response(resp, "enqueue_telegram")


# -----------------------------------------
# 3. SET TELEGRAM WEBHOOK TO POINT TO NGINX /messenger
# -----------------------------------------

def set_telegram_webhook():
    """
    Tell Telegram to send bot updates to Nginx at /messenger/webhooks/telegram,
    which then proxies to Hermes' /webhooks/telegram upstream.
    """
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"

    # External webhook URL, including the /messenger prefix
    webhook_url = f"{BASE_URL}/webhooks/telegram?token={HERMES_TOKEN}"
    # Example: https://.../messenger/webhooks/telegram?token=...

    print("[set_telegram_webhook] Setting Telegram webhook")
    print(f"[set_telegram_webhook] API URL: {api_url}")
    print(f"[set_telegram_webhook] Webhook URL: {webhook_url}")
    resp = requests.post(api_url, data={"url": webhook_url})
    print_response(resp, "setWebhook")


# -----------------------------------------
# 4. CHECK TELEGRAM WEBHOOK STATUS
# -----------------------------------------

def get_telegram_webhook_info():
    """
    Check what Telegram thinks the webhook is set to.
    """
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"

    print("[get_telegram_webhook_info] Fetching current Telegram webhook info")
    print(f"[get_telegram_webhook_info] API URL: {api_url}")
    resp = requests.get(api_url)
    print_response(resp, "getWebhookInfo")


# -----------------------------------------
# 5. GET UPDATES (ONLY IF NO WEBHOOK)
# -----------------------------------------

def get_telegram_updates():
    """
    Poll Telegram for updates.
    Mostly useful when you do not use webhooks, or for debugging.
    """
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    print("[get_telegram_updates] Polling Telegram for updates")
    print(f"[get_telegram_updates] API URL: {api_url}")
    resp = requests.get(api_url)
    print_response(resp, "getUpdates")


# -----------------------------------------
# 6. SIMULATE TELEGRAM WEBHOOK /ping THROUGH NGINX
# -----------------------------------------

def simulate_telegram_webhook_ping():
    """
    Pretend Telegram called /messenger/webhooks/telegram with a /ping command.
    This goes through Nginx, which proxies to Hermes.
    """
    url = f"{BASE_URL}/webhooks/telegram"   # -> /messenger/webhooks/telegram
    params = {"token": HERMES_TOKEN}
    payload = {
        "message": {
            "chat": {"id": TELEGRAM_CHAT_ID, "type": "private"},
            "text": "/ping",
        }
    }

    print("[simulate_telegram_webhook_ping] Simulating Telegram /ping webhook call via Nginx")
    print(f"[simulate_telegram_webhook_ping] URL: {url}")
    print(f"[simulate_telegram_webhook_ping] Chat ID: {TELEGRAM_CHAT_ID}")
    resp = requests.post(url, params=params, headers=HEADERS_JSON, json=payload)
    print_response(resp, "simulate_ping")


# -----------------------------------------
# 7. SIMULATE TELEGRAM WEBHOOK /verify THROUGH NGINX
# -----------------------------------------

def simulate_telegram_verify():
    """
    Pretend Telegram called /messenger/webhooks/telegram with a /verify command.
    """
    url = f"{BASE_URL}/webhooks/telegram"   # -> /messenger/webhooks/telegram
    params = {"token": HERMES_TOKEN}
    payload = {
        "message": {
            "chat": {"id": TELEGRAM_CHAT_ID, "type": "private"},
            "text": "/verify",
        }
    }

    print("[simulate_telegram_verify] Simulating Telegram /verify webhook call via Nginx")
    print(f"[simulate_telegram_verify] URL: {url}")
    print(f"[simulate_telegram_verify] Chat ID: {TELEGRAM_CHAT_ID}")
    resp = requests.post(url, params=params, headers=HEADERS_JSON, json=payload)
    print_response(resp, "simulate_verify")


# -----------------------------------------
# ORCHESTRATION
# -----------------------------------------

if __name__ == "__main__":
    print("=== Hermes remote integration test script (behind Nginx /messenger) ===")
    print(f"Using BASE (public, proxied): {BASE_URL}")
    print("")

    # 1) Configure Telegram webhook to hit Nginx /messenger/webhooks/telegram
    set_telegram_webhook()

    # 2) Check webhook status from Telegram
    get_telegram_webhook_info()

    # 3) Enqueue an email verification message through Nginx -> Hermes
    enqueue_email()

    # 4) Enqueue a Telegram job through Nginx -> Hermes
    enqueue_telegram()

    # 5) Simulate Telegram sending /ping and /verify via Nginx -> Hermes
    simulate_telegram_webhook_ping()
    simulate_telegram_verify()

    # 6) Optionally, poll Telegram updates
    get_telegram_updates()

    print("=== Done ===")
