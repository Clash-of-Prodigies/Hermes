import os
import requests
import logging
import oreiades
import time

logger = logging.getLogger(__name__)

SubjectToTemplate = {
        "welcome": "welcome",
        "default": "default",
        "start": "default",
        "ping": "ping",
        "health": "health",
        "password reset": "password_reset",
        "Verify Your Account": "verify"
}

class TelegramAdapter:
    """
    Simple Telegram Bot API adapter.

    For now:
      - expects `to` to be a Telegram chat_id (string or int)
      - sends plain text messages built from template + data
    """

    def __init__(self):
        self.token = oreiades.environmentals("TELEGRAM_BOT_TOKEN", "")
        self.base_url = oreiades.environmentals("TELEGRAM_API_BASE", "https://api.telegram.org")

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN is not set. TelegramAdapter will not be able to send messages.")

    def bot_commands(self, to: str, sender: str, command_name: str, command_payload: dict):
        if command_name == "/ping":
            user_id = command_payload.get("chat_id", "")
            command_payload.clear()
            command_payload["chat_id"] = user_id
        elif command_name == "/verify":
            # resp = requests.post('url', json={''chat_id': command_payload.get('chat_id', '')})
            # if resp.json().get('status', 'failed') == 'success':
            #     command_payload['status'] = 'successful'
            # else: command_payload['status'] = 'unsuccessful'
            # command_payload['message'] = resp.json().get('message', '')
            pass 
        elif command_name == "/welcome":
            prodigy_id = command_payload.get("prodigy_id", "")
            role = command_payload.get("role", "")
            command_payload.clear()
            command_payload["account_id"] = prodigy_id
            command_payload["account_name"] = to
            command_payload["role"] = role
            command_payload["sender"] = sender
        else:
            pass

        return command_payload

    def render_template(self, data: dict, template_name: str) -> str:
        def escape_markdown_v2(text: str) -> str:
            """
            Escape Telegram MarkdownV2 special characters in a value.
            This is for dynamic data, NOT the whole template.
            """
            if text is None: return ""

            specials = r"_*[]()~`>#+-=|{}.!\\"
            escaped = []

            for ch in str(text):
                if ch == "\\":
                    # Backslash must become \\
                    escaped.append("\\\\")
                elif ch in specials:
                    escaped.append("\\" + ch)
                else:
                    escaped.append(ch)

            return "".join(escaped)

        try:
            template_name = os.path.join("templates", "telegram", template_name)
            with open(f"{template_name}.md", "r") as f: template = f.read()
            for key, value in data.items():
                template = template.replace(f"%%{key}%%", escape_markdown_v2(str(value)))
            return template
        except FileNotFoundError:
            raise FileNotFoundError(f"Template {template_name}.md not found.")
        except Exception as e:
            raise RuntimeError(f"Error rendering template: {e}")

    def send(self, to: list[str], sender: str, subject: str, data: dict):
        """
        Sends a message via Telegram Bot API to a given chat_id.
        """
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        url = f"{self.base_url}/bot{self.token}/sendMessage"

        for name in to:
            data = self.bot_commands(name, sender, subject, data)
            text = self.render_template(data or {}, SubjectToTemplate.get(subject.strip('/'), 'default'))
            
            payload = {
                "chat_id": oreiades.get_address_by_name(name, "telegram"),
                "text": text,
                "parse_mode": "MarkdownV2",
            }

            resp = requests.post(url, json=payload, timeout=10)

            try:
                resp.raise_for_status()
            except Exception:
                logger.error("Telegram sendMessage failed: %s", resp.text)
                raise
            time.sleep(0.5)
