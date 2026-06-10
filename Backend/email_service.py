from __future__ import annotations

import os
import ssl
import random
import string
from email.message import EmailMessage
import smtplib
from typing import Optional
from datetime import datetime, timezone


SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@scholarship.local")


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _build_message(to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)
    return msg


def send_email(to_email: str, subject: str, body: str, timeout: float = 10.0) -> None:
    if not SMTP_HOST or not SMTP_PORT:
        raise RuntimeError("SMTP configuration is missing (SMTP_HOST/SMTP_PORT).")

    msg = _build_message(to_email, subject, body)

    context = ssl.create_default_context()
    if SMTP_USE_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
            server.starttls(context=context)
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=timeout) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)



def send_reset_email(to_email: str, code: str) -> None:
    subject = "Password reset for Scholarship account"
    body = f"Your password reset code is: {code}\n\nIf you did not request this, please ignore."
    send_email(to_email, subject, body)
