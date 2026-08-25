import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.db.session import SessionLocal
from app.services.settings import get_raw

logger = logging.getLogger(__name__)

BRAND = "Spiritual Hut Academy"


def _wrap_html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f4f1ec;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f1ec;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #eadfd2;">
        <tr>
          <td style="background:#2F002E;color:#ffffff;padding:28px 32px;">
            <div style="font-size:22px;font-weight:bold;letter-spacing:1px;">{BRAND}</div>
            <div style="font-size:13px;opacity:0.85;margin-top:6px;">Vastu Diagnostics &amp; Sacred Geometry</div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;color:#2b2b2b;font-size:15px;line-height:1.6;">
            {body}
          </td>
        </tr>
        <tr>
          <td style="background:#faf7f2;padding:18px 32px;font-size:12px;color:#6b5b4f;text-align:center;">
            This is an automated message from {BRAND}. Please do not reply to this email.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    db = SessionLocal()
    try:
        user = (get_raw(db, "gmail_user") or "").strip()
        password = (get_raw(db, "gmail_app_password") or "").strip()
        if not user or not password:
            logger.warning("Gmail is not configured; skipping email to %s", to_email)
            return False
        if not to_email:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{BRAND} <{user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, [to_email], msg.as_string())
        logger.info("Email sent to %s (%s)", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
    finally:
        db.close()


def send_email_async(to_email: str, subject: str, html_body: str) -> None:
    threading.Thread(
        target=send_email,
        args=(to_email, subject, html_body),
        daemon=True,
    ).start()


def send_registration_email(name: str, to_email: str) -> None:
    display = name or "there"
    body = f"""
      <p>Dear {display},</p>
      <p>Welcome to <b>{BRAND}</b>. Your account has been created successfully.</p>
      <p>You can now log in and complete your plan payment to start creating Vastu projects and generating reports.</p>
      <p>If you did not create this account, please ignore this email or contact us.</p>
      <p style="margin-top:28px;">Warm regards,<br/><b>Team {BRAND}</b></p>
    """
    send_email_async(
        to_email,
        f"Welcome to {BRAND} — account created",
        _wrap_html("Welcome", body),
    )


def send_payment_email(
    name: str,
    to_email: str,
    plan_name: Optional[str] = None,
    amount: Optional[str] = None,
) -> None:
    display = name or "there"
    plan_line = f"<p>Plan: <b>{plan_name}</b></p>" if plan_name else ""
    amount_line = f"<p>Amount paid: <b>₹{amount}</b></p>" if amount else ""
    body = f"""
      <p>Dear {display},</p>
      <p>Thank you. Your payment was received and your subscription is now <b>active</b>.</p>
      {plan_line}
      {amount_line}
      <p>You can now create projects and generate Vastu reports from your dashboard.</p>
      <p style="margin-top:28px;">Warm regards,<br/><b>Team {BRAND}</b></p>
    """
    send_email_async(
        to_email,
        f"Payment successful — {BRAND}",
        _wrap_html("Payment successful", body),
    )
