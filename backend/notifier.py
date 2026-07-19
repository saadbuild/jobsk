"""
JOBSK SMS NOTIFIER (new in v3)

THE HONEST TRUTH ABOUT "free" SMS
───────────────────────────────────
There is no service that sends real SMS texts to any phone, for free,
with no setup, forever. The two realistic options:

OPTION A — Twilio (recommended, small cost after a free trial)
    Twilio gives new accounts a small amount of free trial credit, then
    it's pay-per-text (a fraction of a cent to a few cents per message
    depending on country). This is the standard, reliable way to send SMS
    from an app.
        1. https://www.twilio.com -> sign up, verify a phone number
        2. Get a Twilio phone number (free ones are available on trial)
        3. Copy Account SID + Auth Token from the console
        4. backend/.env:
               TWILIO_ACCOUNT_SID=...
               TWILIO_AUTH_TOKEN=...
               TWILIO_FROM_NUMBER=+1xxxxxxxxxx
        5. pip install twilio (already in requirements.txt)

OPTION B — Carrier email-to-SMS gateways (actually free, but unofficial)
    Every major carrier lets you text a phone by emailing a special
    address, e.g. 5551234567@txt.att.net. This costs nothing beyond the
    email you're already sending, but: it's unofficial (carriers can
    change/block it any time), delivery isn't guaranteed, and you need to
    know the recipient's carrier. Good enough for a personal project;
    don't rely on it for anything critical.

This module tries Twilio first if configured, otherwise falls back to
the carrier-gateway method if you pass a carrier, otherwise does nothing
(and says so, rather than silently pretending to succeed).
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Common US carrier email-to-SMS gateways. Add more as needed.
CARRIER_GATEWAYS = {
    "att": "txt.att.net",
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "boost": "sms.myboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "metropcs": "mymetropcs.com",
    "googlefi": "msg.fi.google.com",
}


def _send_via_twilio(to_phone, message):
    try:
        from twilio.rest import Client
    except ImportError:
        print("[notifier] twilio package not installed — run: pip install twilio")
        return False
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        return False
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_FROM_NUMBER, to=to_phone)
        print(f"[notifier] SMS sent via Twilio to {to_phone}")
        return True
    except Exception as e:
        print(f"[notifier] Twilio send failed: {e}")
        return False


def _send_via_carrier_gateway(to_phone, message, carrier):
    gateway = CARRIER_GATEWAYS.get((carrier or "").lower())
    if not gateway or not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return False
    digits = "".join(ch for ch in to_phone if ch.isdigit())[-10:]
    to_addr = f"{digits}@{gateway}"
    try:
        msg = MIMEText(message)
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_addr
        msg["Subject"] = ""
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[notifier] SMS sent via carrier gateway to {to_addr}")
        return True
    except Exception as e:
        print(f"[notifier] Carrier gateway send failed: {e}")
        return False


def send_sms_alert(to_phone, message, carrier=None):
    if not to_phone:
        return False
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER:
        if _send_via_twilio(to_phone, message):
            return True
    if carrier:
        if _send_via_carrier_gateway(to_phone, message, carrier):
            return True
    print(f"[notifier] SMS not sent to {to_phone} — no SMS method configured "
          f"(set up Twilio, or pass a carrier for the free gateway fallback)")
    return False
