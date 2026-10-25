import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings

logger = logging.getLogger(__name__)


def send_verification_email(email: str, name: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.error("Verification email delivery is not configured")
        return
    url = f"{settings.public_base_url.rstrip('/')}/#/verify/{token}"
    message = EmailMessage()
    message["Subject"] = "Verify your ResearchBridge account"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        f"Hello {name},\n\nVerify your ResearchBridge account using this link:\n{url}\n\n"
        "If you did not request this account, you can ignore this message."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # Do not fail account creation or log the verification token.
        logger.exception("ResearchBridge verification email delivery failed")
