"""Optional SMTP adapter; callers should always create the in-app notice first."""

from __future__ import annotations

from email.message import EmailMessage
import os
import smtplib
import ssl


class SMTPNotifier:
    """Best-effort mail transport. Missing settings or mail errors never escape."""

    def send(self, recipient: str, subject: str, body: str) -> bool:
        host = os.getenv("SMTP_HOST")
        sender = os.getenv("SMTP_FROM")
        if not host or not sender or not recipient:
            return False
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            port = int(os.getenv("SMTP_PORT", "587"))
            with smtplib.SMTP(host, port, timeout=5) as client:
                client.starttls(context=ssl.create_default_context())
                username = os.getenv("SMTP_USERNAME")
                password = os.getenv("SMTP_PASSWORD")
                if username and password:
                    client.login(username, password)
                client.send_message(message)
            return True
        except (OSError, smtplib.SMTPException, ValueError):
            return False
