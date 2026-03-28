"""
StreetSense -- Notification Service

Sends notifications on complaint lifecycle events:
  - New complaint created -> notify department
  - Status updated -> notify citizen + authority
  - High severity detected -> urgent alert

Channels:
  - Email (SMTP -- real or simulated)
  - SMS (mock API -- logs to console)
  - In-app (stored in database for frontend polling)

Usage:
    from app.services.notification_service import notify

    await notify.on_complaint_created(complaint, location_info)
    await notify.on_status_changed(complaint, old_status, new_status, notes)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from app.core.config import settings


# ===================================================================
# Email Service (SMTP)
# ===================================================================

async def send_email(to: str, subject: str, body: str) -> bool:
    """
    Send an email via SMTP.
    Falls back to console logging if SMTP is not configured.
    """
    if not settings.smtp_user or not settings.smtp_host:
        # Simulate -- log to console
        logger.info(f"[EMAIL SIMULATED] To: {to}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Body: {body[:200]}...")
        return True

    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info(f"[EMAIL SENT] To: {to}, Subject: {subject}")
        return True

    except ImportError:
        logger.warning("aiosmtplib not installed. Email simulated.")
        logger.info(f"[EMAIL SIMULATED] To: {to}, Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL FAILED] To: {to}, Error: {e}")
        return False


# ===================================================================
# SMS Service (Mock API)
# ===================================================================

async def send_sms(phone: str, message: str) -> bool:
    """
    Send an SMS notification.
    This is a mock implementation that logs to console.
    Replace with Twilio/MSG91/other provider in production.
    """
    logger.info(f"[SMS SIMULATED] To: {phone}")
    logger.info(f"  Message: {message[:160]}")

    # Simulate API delay
    await asyncio.sleep(0.1)

    # In production, replace with:
    # response = await httpx.post("https://api.twilio.com/...", ...)
    # return response.status_code == 200

    return True


# ===================================================================
# Notification Templates
# ===================================================================

def build_new_complaint_email(complaint, location_info: dict = None) -> tuple:
    """Build email subject and body for new complaint notification."""
    severity = complaint.severity
    if hasattr(severity, 'value'):
        severity = severity.value
    issue_type = complaint.issue_type
    if hasattr(issue_type, 'value'):
        issue_type = issue_type.value

    subject = f"[StreetSense] New {severity.upper()} severity {issue_type} reported"

    body = f"""
    <html><body style="font-family: sans-serif; color: #333;">
    <h2 style="color: {'#ef4444' if severity == 'high' else '#f59e0b' if severity == 'medium' else '#22c55e'};">
        New Road Issue Detected
    </h2>
    <table style="border-collapse: collapse; width: 100%;">
        <tr><td style="padding: 8px; font-weight: bold;">Type:</td>
            <td style="padding: 8px;">{issue_type.upper()}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Severity:</td>
            <td style="padding: 8px;">{severity.upper()} (score: {complaint.severity_score:.2f})</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Confidence:</td>
            <td style="padding: 8px;">{complaint.confidence:.1%}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Location:</td>
            <td style="padding: 8px;">{complaint.address or f'{complaint.latitude}, {complaint.longitude}'}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Ward:</td>
            <td style="padding: 8px;">{complaint.ward or 'Unknown'}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Department:</td>
            <td style="padding: 8px;">{complaint.department or 'Unassigned'}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Source:</td>
            <td style="padding: 8px;">{complaint.source}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Complaint ID:</td>
            <td style="padding: 8px; font-family: monospace;">{complaint.id}</td></tr>
    </table>
    <p style="margin-top: 20px; color: #666;">
        This is an automated notification from StreetSense AI Road Monitoring System.
    </p>
    </body></html>
    """

    return subject, body


def build_status_update_email(complaint, old_status: str, new_status: str, notes: str = None) -> tuple:
    """Build email for status change notification."""
    issue_type = complaint.issue_type
    if hasattr(issue_type, 'value'):
        issue_type = issue_type.value

    subject = f"[StreetSense] Complaint {str(complaint.id)[:8]}... status: {new_status.upper()}"

    body = f"""
    <html><body style="font-family: sans-serif; color: #333;">
    <h2>Complaint Status Updated</h2>
    <p>
        <strong>{issue_type.upper()}</strong> complaint at
        <strong>{complaint.address or f'{complaint.latitude}, {complaint.longitude}'}</strong>
    </p>
    <p style="font-size: 18px;">
        Status: <span style="text-decoration: line-through; color: #999;">{old_status}</span>
        &rarr; <strong style="color: #16a34a;">{new_status.upper()}</strong>
    </p>
    {f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
    <p style="margin-top: 20px; color: #666; font-family: monospace;">
        ID: {complaint.id}
    </p>
    </body></html>
    """

    return subject, body


def build_sms_new_complaint(complaint) -> str:
    """Build SMS message for new complaint."""
    severity = complaint.severity
    if hasattr(severity, 'value'):
        severity = severity.value
    issue_type = complaint.issue_type
    if hasattr(issue_type, 'value'):
        issue_type = issue_type.value

    addr = complaint.address or f"{complaint.latitude:.4f},{complaint.longitude:.4f}"
    return (
        f"StreetSense Alert: {severity.upper()} {issue_type} "
        f"detected at {addr[:60]}. "
        f"ID: {str(complaint.id)[:8]}"
    )


def build_sms_status_update(complaint, new_status: str) -> str:
    """Build SMS message for status update."""
    return (
        f"StreetSense: Your complaint {str(complaint.id)[:8]} "
        f"status updated to {new_status.upper()}."
    )


# ===================================================================
# In-App Notifications (stored for frontend)
# ===================================================================

# In-memory store (replace with DB table in production)
_notifications = []
MAX_NOTIFICATIONS = 200


def store_notification(
    complaint_id: str,
    title: str,
    message: str,
    severity: str = "info",
    notification_type: str = "status_update",
):
    """Store an in-app notification for the frontend."""
    notif = {
        "id": uuid.uuid4().hex[:12],
        "complaint_id": str(complaint_id),
        "title": title,
        "message": message,
        "severity": severity,
        "type": notification_type,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _notifications.insert(0, notif)

    # Trim old notifications
    if len(_notifications) > MAX_NOTIFICATIONS:
        _notifications[:] = _notifications[:MAX_NOTIFICATIONS]

    return notif


def get_notifications(limit: int = 50, unread_only: bool = False) -> list:
    """Get recent notifications."""
    result = _notifications
    if unread_only:
        result = [n for n in result if not n["read"]]
    return result[:limit]


def mark_notification_read(notification_id: str) -> bool:
    """Mark a notification as read."""
    for n in _notifications:
        if n["id"] == notification_id:
            n["read"] = True
            return True
    return False


def get_unread_count() -> int:
    """Get count of unread notifications."""
    return sum(1 for n in _notifications if not n["read"])


# ===================================================================
# Notification Dispatcher (main entry points)
# ===================================================================

class NotificationDispatcher:
    """Dispatches notifications across all channels."""

    async def on_complaint_created(self, complaint, location_info: dict = None):
        """Trigger notifications when a new complaint is created."""
        severity = complaint.severity
        if hasattr(severity, 'value'):
            severity = severity.value
        issue_type = complaint.issue_type
        if hasattr(issue_type, 'value'):
            issue_type = issue_type.value

        # In-app notification
        store_notification(
            complaint_id=complaint.id,
            title=f"New {issue_type} detected",
            message=f"{severity.upper()} severity at {complaint.address or 'reported location'}",
            severity=severity,
            notification_type="new_complaint",
        )

        # Email to department (if contact available)
        contact_email = ""
        if location_info:
            contact_email = location_info.get("contact_email", "")

        if contact_email:
            subject, body = build_new_complaint_email(complaint, location_info)
            await send_email(contact_email, subject, body)

        # SMS for high severity
        if severity == "high":
            contact_phone = ""
            if location_info:
                contact_phone = location_info.get("contact_phone", "")
            if contact_phone:
                sms_msg = build_sms_new_complaint(complaint)
                await send_sms(contact_phone, sms_msg)

            # Also send urgent email even without specific contact
            subject, body = build_new_complaint_email(complaint, location_info)
            await send_email("alerts@streetsense.app", subject, body)

        logger.info(
            f"[NOTIFY] New complaint: {issue_type} ({severity}) "
            f"at {complaint.address or 'unknown location'}"
        )

    async def on_status_changed(
        self, complaint, old_status: str, new_status: str, notes: str = None
    ):
        """Trigger notifications when complaint status changes."""
        # In-app notification
        store_notification(
            complaint_id=complaint.id,
            title=f"Status: {old_status} -> {new_status}",
            message=notes or f"Complaint updated to {new_status}",
            severity="info",
            notification_type="status_update",
        )

        # Email notification
        subject, body = build_status_update_email(complaint, old_status, new_status, notes)
        await send_email("updates@streetsense.app", subject, body)

        # SMS on resolution
        if new_status in ("resolved", "verified"):
            sms_msg = build_sms_status_update(complaint, new_status)
            await send_sms("citizen-phone", sms_msg)

        logger.info(f"[NOTIFY] Status change: {old_status} -> {new_status} for {complaint.id}")


# Singleton dispatcher
notify = NotificationDispatcher()
