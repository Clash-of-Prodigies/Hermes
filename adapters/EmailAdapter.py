# app/adapters/email_gmail.py
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

    def send_email(self, to_email: str, subject: str, text_body: str, html_body: str | None = None):
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls(context=context)
            server.login(self.user, self.password)
            server.send_message(msg)