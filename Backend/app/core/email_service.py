import smtplib
from email.message import EmailMessage
from app.config import settings
from app.core.governance import add_audit


def send_email(to, subject, body):
    """Send a plain text email."""
    msg = EmailMessage()
    msg['From'] = settings.email_from
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    
    smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    smtp.send_message(msg)
    smtp.quit()


def claim_received_text(full_name, claim_number, policy_number):
    """Generate claim received email text."""
    subject = f"We received your claim {claim_number}"
    
    body = f"""Hello {full_name},

We have received your insurance claim.

Claim number: {claim_number}
Policy number: {policy_number}
Status: Submitted

You can track your claim and upload documents in your ClaimPilot dashboard.

Thank you for choosing ClaimPilot.
"""
    
    return (subject, body)


def send_claim_received(db, user, claim, policy_number):
    """Send claim received email and log the result."""
    subject, body = claim_received_text(user.full_name, claim.claim_number, policy_number)
    
    try:
        send_email(user.email, subject, body)
        add_audit(db, "system", "email_sent", claim.id, {"to": user.email, "subject": subject})
        return True
    except (OSError, smtplib.SMTPException) as e:
        add_audit(db, "system", "email_failed", claim.id, {"to": user.email, "error": str(e)})
        return False
