"""
Hermes is the messenger application for Prodigy.
It will import messaging capabilities from modules declared in the same scope.
These capabilities are email and whatsapp (for now)
"""
from flask import Flask, request, jsonify

import oreiades

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
