import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import anyio

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class OutgoingEmail:
    to_email: str
    subject: str
    text_body: str


class EmailSender(Protocol):
    async def send(self, message: OutgoingEmail) -> None:
        pass


class ConsoleEmailSender:
    async def send(self, message: OutgoingEmail) -> None:
        logger.info(
            "Email delivery is not configured. Message to %s: subject=%s body=%s",
            message.to_email,
            message.subject,
            message.text_body,
        )


class SMTPEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, message: OutgoingEmail) -> None:
        try:
            await anyio.to_thread.run_sync(self._send_sync, message)
        except Exception as exc:
            raise EmailDeliveryError("Failed to send email") from exc

    def _send_sync(self, message: OutgoingEmail) -> None:
        settings = self._settings

        email_message = EmailMessage()
        email_message["From"] = format_sender(settings)
        email_message["To"] = message.to_email
        email_message["Subject"] = message.subject
        email_message.set_content(message.text_body)

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                self._login_if_needed(smtp)
                smtp.send_message(email_message)
            return

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            self._login_if_needed(smtp)
            smtp.send_message(email_message)

    def _login_if_needed(self, smtp: smtplib.SMTP | smtplib.SMTP_SSL) -> None:
        settings = self._settings

        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.smtp_host and settings.smtp_from_email:
        return SMTPEmailSender(settings)

    return ConsoleEmailSender()


def format_sender(settings: Settings) -> str:
    if settings.smtp_from_name:
        return f"{settings.smtp_from_name} <{settings.smtp_from_email}>"

    return settings.smtp_from_email
