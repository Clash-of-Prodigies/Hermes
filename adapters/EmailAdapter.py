import os
import ssl
import smtplib
from email.message import EmailMessage
import oreiades

class GmailEmailAdapter:
    def __init__(self):
        host, port, user, password = oreiades.environmentals(
            "EMAIL_SMTP_HOST,EMAIL_SMTP_PORT,EMAIL_USER,EMAIL_APP_PASSWORD"
        ).split(",")
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password

    def render_template(self, data: dict, template_name: str = "default.html",) -> str:
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

    def send(self, to: str, subject: str, data: dict, template_name: str):
        msg = EmailMessage()
        msg["From"] = f'Prodigy <{self.user}>'
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content("This email requires an HTML viewer.")
        html_body = self.render_template(data=data, template_name=template_name)
        msg.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls(context=context)
            server.login(self.user, self.password)
            server.send_message(msg)