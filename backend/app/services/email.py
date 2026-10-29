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


def send_resource_notification_email(
    to_email: str,
    student_name: str,
    faculty_name: str,
    project_title: str,
    resource_title: str,
    resource_type: str,
    project_id: int,
) -> None:
    """Send email notification to enrolled student when faculty adds or uploads a resource."""
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("SMTP host not configured; recorded resource email dispatch to %s", to_email)
        return
    workspace_url = f"{settings.public_base_url.rstrip('/')}/workspace?project={project_id}"
    message = EmailMessage()
    message["Subject"] = f"New Resource Shared in {project_title}: {resource_title}"
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(
        f"Hello {student_name},\n\n"
        f"{faculty_name} has shared a new {resource_type.lower()} in your research project '{project_title}':\n\n"
        f"  * Title: {resource_title}\n"
        f"  * Type: {resource_type}\n\n"
        f"You can view and download this resource directly in your ResearchBridge project workspace:\n"
        f"{workspace_url}\n\n"
        f"Best regards,\n"
        f"The ResearchBridge Team"
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        logger.info("Resource notification email successfully sent to %s", to_email)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Resource notification email delivery failed for %s: %s", to_email, exc)
