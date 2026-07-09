from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import ssl
from smtplib import SMTP, SMTP_SSL
from urllib.parse import urlparse

from fastapi import HTTPException

from config import settings


from .base import MailClientBase


_logger = logging.getLogger(__name__)


class SmtpMailClient(MailClientBase):

    _type = "smtp"

    @staticmethod
    def _connect(smtp_url_parts):
        if not smtp_url_parts.hostname:
            raise ValueError("SMTP host is empty")

        port = smtp_url_parts.port or (465 if smtp_url_parts.scheme in {"smtps", "smtp+ssl"} else 587)
        context = ssl.create_default_context()

        # smtps://host:465 uses implicit TLS. smtp://host:587 must upgrade with
        # STARTTLS and fail if the server does not advertise TLS support.
        if smtp_url_parts.scheme in {"smtps", "smtp+ssl"} or port == 465:
            return SMTP_SSL(smtp_url_parts.hostname, port=port, context=context, timeout=20)

        smtp = SMTP(smtp_url_parts.hostname, port=port, timeout=20)
        try:
            smtp.ehlo()
            if not smtp.has_extn("starttls"):
                raise RuntimeError("SMTP server does not advertise STARTTLS")
            smtp.starttls(context=context)
            smtp.ehlo()
            return smtp
        except Exception:
            smtp.close()
            raise

    @classmethod
    def send_verify_code(cls, email: str, code: str) -> None:
        try:
            smtp_url_parts = urlparse(settings.smtp_url)
            with cls._connect(smtp_url_parts) as smtp:
                smtp.login(smtp_url_parts.username, smtp_url_parts.password)
                message = MIMEMultipart()
                message['From'] = smtp_url_parts.username
                message['To'] = email
                message['Subject'] = "AWSL Verify Code"
                message.attach(MIMEText(f"Your verify code is {code}", 'plain'))
                smtp.sendmail(smtp_url_parts.username, email, message.as_string())
                return
        except Exception as e:
            _logger.error(f"Failed to send verify code: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to send verify code: {e}"
            )
