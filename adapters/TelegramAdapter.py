# adapters/TelegramAdapter.py
import os
import requests
import logging

import oreiades  # for environmentals()

logger = logging.getLogger(__name__)


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

    def render_template(self, subject: str, data: dict, template_name: str) -> str:
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
            data["subject"] = subject
            template_name = os.path.join("templates", "telegram", template_name)
            with open(f"{template_name}.md", "r") as f: template = f.read()
            for key, value in data.items():
                template = template.replace(f"{{{{{key}}}}}", escape_markdown_v2(str(value)))
            return template
        except FileNotFoundError:
            raise FileNotFoundError(f"Template {template_name}.md not found.")
        except Exception as e:
            raise RuntimeError(f"Error rendering template: {e}")

    def send(self, to: str, subject: str, data: dict, template_name: str, ):
        """
        Sends a message via Telegram Bot API to a given chat_id.
        """
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        text = self.render_template(subject, data or {}, template_name)

        url = f"{self.base_url}/bot{self.token}/sendMessage"
        payload = {
            "chat_id": to,
            "text": text,
            "parse_mode": "MarkdownV2",
        }

        resp = requests.post(url, json=payload, timeout=10)

        try:
            resp.raise_for_status()
        except Exception:
            logger.error("Telegram sendMessage failed: %s", resp.text)
            raise

        return resp.json()
