import os
import requests
import logging
import oreiades
import time

logger = logging.getLogger(__name__)

SubjectToTemplate = {
    "start": "welcome",
    "welcome": "welcome",
    "default": "default",
    "test": "test",
    "password reset": "password_reset",
    "Verify Your Account": "verify"
}

class GmailEmailAdapter:
    def __init__(self):
        url, key = oreiades.environmentals("EMAIL_API_URL, EMAIL_API_KEY").split(",")
        self.url = url
        self.key = key
    def render_template(self, data: dict, template_name: str,) -> str:
        try:
            template_name = os.path.join("templates", "email", template_name)
            with open(f"{template_name}.html", "r") as f: template = f.read()
            for key, value in data.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        except FileNotFoundError:
            raise FileNotFoundError(f"Template {template_name} not found.")
        except Exception as e:
            raise RuntimeError(f"Error rendering template: {e}")

    def send(self, to: list[str], sender: str, subject: str, data: dict):
        htmlContent = self.render_template(data, SubjectToTemplate.get(subject, 'default'))
        
        headers = {
            "accept": "application/json",
            "api-key": self.key,
            "content-type": "application/json",
        }
        payload = {
            "sender": {
                "name": sender.split("<")[0].strip(),
                "email": sender.split("<")[-1].strip(" >"),
            },
            "to": [
                {"name": name, "email": oreiades.get_address_by_name(name, "email")}
                for name in to
            ],
            "subject": subject,
            "textContent": "This email requires an HTML viewer.",
            "htmlContent": htmlContent,
        }

        resp = requests.post(self.url, headers=headers, json=payload, timeout=10)

        try:
            resp.raise_for_status()
        except Exception:
            logger.error("Email send failed: %s", resp.text)
            raise
        time.sleep(0.5)

        