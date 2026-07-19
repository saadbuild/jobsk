"""
JOBSK EMAILER
Sends real email notifications via Gmail SMTP. This part of v2 was
already genuine (not demo data) — it just needed credentials in .env
and, in v2, nothing ever called it automatically. v3 adds a background
scheduler (see scheduler.py) that calls this on its own, so alerts go
out even while the app is closed, as long as the backend server itself
is running (see README for what "running" means on a free host).

SETUP REQUIRED:
    1. Use a Gmail account (or create one for this app)
    2. https://myaccount.google.com/apppasswords -> generate an App Password
    3. backend/.env:
           EMAIL_ADDRESS=youremail@gmail.com
           EMAIL_PASSWORD=your_16_character_app_password
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "").strip()
# Google's App Passwords page displays the password with spaces in groups
# of 4 (e.g. "abcd efgh ijkl mnop") purely for readability. A very common
# cause of silent email failures is pasting it into .env WITH those
# spaces still in it — Gmail's SMTP login then rejects it. Stripping all
# whitespace here means it works whether it was pasted with or without
# the spaces.
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").replace(" ", "").strip()


def _send(to_email, subject, html_body):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        msg = f"EMAIL_ADDRESS/EMAIL_PASSWORD not set — would have sent '{subject}' to {to_email}"
        print(f"[emailer] {msg}")
        return {"success": False, "message": msg}
    try:
        msg_obj = MIMEMultipart("alternative")
        msg_obj["Subject"] = subject
        msg_obj["From"] = EMAIL_ADDRESS
        msg_obj["To"] = to_email
        msg_obj.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg_obj)
        print(f"[emailer] Sent '{subject}' to {to_email}")
        return {"success": True, "message": f"Sent to {to_email}"}
    except smtplib.SMTPAuthenticationError as e:
        # By far the most common failure: EMAIL_PASSWORD is a normal
        # Google account password instead of a 16-character App Password,
        # or 2-Step Verification isn't turned on for the Gmail account
        # (App Passwords don't exist until it is).
        detail = ("Gmail rejected the login. Make sure 2-Step Verification is ON for "
                  "this Gmail account, then generate a fresh App Password at "
                  "https://myaccount.google.com/apppasswords and put it in EMAIL_PASSWORD "
                  f"(no spaces). Raw error: {e}")
        print(f"[emailer] Auth failed: {e}")
        return {"success": False, "message": detail}
    except Exception as e:
        print(f"[emailer] Send failed: {e}")
        return {"success": False, "message": str(e)}


def send_job_alert_email(to_email, jobs):
    job_list_html = "".join(f"""
        <div style="border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:10px">
            <strong>{j.get('title','Job')}</strong><br/>
            <span style="color:#666">{j.get('platform','')} · {j.get('rate','')}</span><br/>
            <a href="{j.get('url','#')}" style="color:#6c63ff">View and apply →</a>
        </div>
    """ for j in jobs)

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px">
        <div style="max-width:500px;margin:0 auto;background:white;border-radius:14px;padding:24px">
            <h2 style="color:#6c63ff">🤖 Jobsk found {len(jobs)} new match{'es' if len(jobs)!=1 else ''}!</h2>
            <p>Here are jobs that match your CV and preferences:</p>
            {job_list_html}
            <p style="color:#999;font-size:12px;margin-top:20px">
                You're receiving this because you have job alerts enabled on Jobsk.
            </p>
        </div>
    </body></html>
    """
    return _send(to_email, f"Jobsk Alert: {len(jobs)} new job matches found!", html_body)["success"]


def send_welcome_email(to_email, name):
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif">
        <h2>Welcome to Jobsk, {name}!</h2>
        <p>Your agent is now active and will scan for matching jobs in the background.</p>
        <p>Upload your CV in the dashboard to start getting personalized job matches by email
        (and text, if you enable SMS alerts in Settings).</p>
    </body></html>
    """
    return _send(to_email, "Welcome to Jobsk!", html_body)["success"]


def send_password_reset_email(to_email, reset_link):
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px">
        <div style="max-width:500px;margin:0 auto;background:white;border-radius:14px;padding:24px">
            <h2 style="color:#6c63ff">Reset your Jobsk password</h2>
            <p>Click the link below to set a new password. This link expires in 1 hour.</p>
            <p><a href="{reset_link}" style="color:#6c63ff;font-weight:600">Reset my password →</a></p>
            <p style="color:#999;font-size:12px;margin-top:20px">
                If you didn't request this, you can safely ignore this email.
            </p>
        </div>
    </body></html>
    """
    return _send(to_email, "Reset your Jobsk password", html_body)["success"]


def send_test_email(to_email):
    """Diagnostic-only: returns the full {"success", "message"} dict
    (not just a bool) so /api/debug/test-email can show the real
    success/failure reason instead of a plain true/false."""
    html_body = """
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px">
        <div style="max-width:500px;margin:0 auto;background:white;border-radius:14px;padding:24px">
            <h2 style="color:#6c63ff">✅ Jobsk test email</h2>
            <p>If you're reading this, EMAIL_ADDRESS and EMAIL_PASSWORD are
            configured correctly and Gmail SMTP is working.</p>
        </div>
    </body></html>
    """
    return _send(to_email, "Jobsk test email", html_body)
