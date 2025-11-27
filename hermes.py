"""
Hermes is the messenger application for Prodigy.
It will import messaging capabilities from modules declared in the same scope.
These capabilities are email and whatsapp (for now)
"""
from flask import Flask, request, jsonify

import oreiades

TELEGRAM_BOT_TOKEN = oreiades.environmentals("TELEGRAM_BOT_TOKEN", "changeme")
# Optionally a secret token like ?token=XYZ to make URL hard to guess
HERMES_SECRET = oreiades.environmentals("TELEGRAM_WEBHOOK_SECRET", "changeme")

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    try:
        health_check = oreiades.health_check()
        return jsonify({"status": f"{'ok' if health_check else 'sick'}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


@app.route("/messages", methods=["POST"])
def enqueue_message():
    raw = request.get_json(force=True) or {}
    try:
        payload = oreiades.MessageCreate(**raw)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400

    with oreiades.get_connection() as conn:
        try:
            msg_row = oreiades.create_message(conn, payload)
        except Exception as e:
            return jsonify({"detail": f"Failed to enqueue message: {e}"}), 500

    resp = oreiades.MessageResponse(**msg_row).asdict() if msg_row else {}
    return jsonify(resp), 202

@app.route("/webhooks/telegram", methods=["POST"])
def telegram_webhook():
    # Optional simple shared-secret check (e.g. /webhooks/telegram?token=XYZ)
    try:
        if request.args.get("token") != HERMES_SECRET: return "forbidden", 403
    except Exception: return "forbidden", 403

    update = request.get_json(force=True, silent=True) or {}

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Could also handle callbacks etc, but skip for now
        return "ok", 200

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text") or ""

    if not chat_id or not isinstance(text, str):
        return "ok", 200

    parts = text.split(maxsplit=1)
    command_name = parts[0]
    command_text = parts[1] if len(parts) > 1 else ""
    command_payload = {
        "chat_id": chat_id,
        "text": command_text,
    }
    payload = oreiades.bot_commands(command_name, command_payload)

    with oreiades.get_connection() as conn:
        try:
            msg_row = oreiades.create_message(conn, payload)
        except Exception as e:
            return jsonify({"detail": f"Failed to enqueue message: {e}"}), 500
    resp = oreiades.MessageResponse(**msg_row).asdict() if msg_row else {}
    return jsonify(resp), 202

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
