"""
JOBSK — AUTH MODULE (Python)
=============================
This file was missing from the repo entirely — only a same-named
frontend file (backend/auth.js, plain browser JS) had been uploaded
into the backend/ folder by mistake. Since app.py does `import auth`
at the top level, that missing/wrong file crashed every single API
route before it could respond, which is why the frontend showed
"Could not reach the server" for everything, not just login.

This implements every function backend/app.py calls on `auth.*`,
using the exact User/Session/... fields already defined in models.py.

Password hashing uses werkzeug.security, which is already installed
as a dependency of Flask — no new package needed in requirements.txt.
"""

import json
import re
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from models import get_db, User, Session, SearchHistoryItem, Notification, PasswordReset

SESSION_LIFETIME = timedelta(days=30)
RESET_LIFETIME = timedelta(hours=1)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _calculate_age(dob_string):
    try:
        dob = datetime.strptime(dob_string, "%Y-%m-%d")
    except Exception:
        return None
    today = datetime.utcnow()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age


def _create_session(db, email):
    token = secrets.token_urlsafe(32)
    db.add(Session(token=token, email=email, expires_at=datetime.utcnow() + SESSION_LIFETIME))
    db.commit()
    return token


# ─────────────────────────────────────────────
# REGISTER / LOGIN
# ─────────────────────────────────────────────

def register_user(name, email, phone, dob, password, skills=""):
    db = get_db()
    try:
        email = (email or "").strip().lower()
        name = (name or "").strip()

        if not name or not email or not password or not dob:
            return {"success": False, "message": "Please fill in all required fields"}
        if not EMAIL_RE.match(email):
            return {"success": False, "message": "Please enter a valid email address"}
        if len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters"}

        age = _calculate_age(dob)
        if age is None:
            return {"success": False, "message": "Please enter a valid date of birth"}
        if age < 16:
            return {"success": False, "message": "You must be at least 16 years old to create an account"}

        if db.get(User, email):
            return {"success": False, "message": "An account with this email already exists"}

        user = User(
            email=email, name=name, phone=(phone or "").strip(), dob=dob, age=age,
            password_hash=generate_password_hash(password), skills=skills or "",
            provider="email",
        )
        db.add(user)
        db.commit()

        token = _create_session(db, email)
        return {"success": True, "user": user.to_public_dict(), "token": token}
    finally:
        db.close()


def login_user(identifier, method, password):
    db = get_db()
    try:
        identifier = (identifier or "").strip()
        if method == "phone":
            user = db.query(User).filter(User.phone == identifier).first()
        else:
            user = db.get(User, identifier.lower())

        if not user or not user.password_hash or not check_password_hash(user.password_hash, password or ""):
            return {"success": False, "message": "Invalid credentials"}

        token = _create_session(db, user.email)
        return {"success": True, "user": user.to_public_dict(), "token": token}
    finally:
        db.close()


def login_or_register_google(email, name):
    db = get_db()
    try:
        email = (email or "").strip().lower()
        user = db.get(User, email)
        if not user:
            user = User(email=email, name=name or email.split("@")[0], provider="google")
            db.add(user)
            db.commit()
        token = _create_session(db, email)
        return {"success": True, "user": user.to_public_dict(), "token": token}
    finally:
        db.close()


def get_user_from_token(token):
    if not token:
        return None
    db = get_db()
    try:
        session = db.get(Session, token)
        if not session or session.expires_at < datetime.utcnow():
            return None
        return db.get(User, session.email)
    finally:
        db.close()


# ─────────────────────────────────────────────
# PASSWORD RESET
# ─────────────────────────────────────────────

def request_password_reset(email):
    db = get_db()
    try:
        email = (email or "").strip().lower()
        if not db.get(User, email):
            return None  # caller shows a generic message either way
        token = secrets.token_urlsafe(32)
        db.add(PasswordReset(token=token, email=email, expires_at=datetime.utcnow() + RESET_LIFETIME))
        db.commit()
        return token
    finally:
        db.close()


def reset_password(token, password):
    db = get_db()
    try:
        reset = db.get(PasswordReset, token)
        if not reset or reset.used or reset.expires_at < datetime.utcnow():
            return {"success": False, "message": "This reset link is invalid or has expired"}
        user = db.get(User, reset.email)
        if not user:
            return {"success": False, "message": "Account not found"}
        user.password_hash = generate_password_hash(password)
        reset.used = True
        db.commit()
        return {"success": True, "message": "Password updated — you can sign in now"}
    finally:
        db.close()


# ─────────────────────────────────────────────
# PROFILE / PREFERENCES
# ─────────────────────────────────────────────

def update_profile(email, name=None, new_email=None, skills=None, new_password=None):
    db = get_db()
    try:
        user = db.get(User, email)
        if not user:
            return {"success": False, "message": "User not found"}

        if name:
            user.name = name
        if skills is not None:
            user.skills = skills
        if new_password:
            if len(new_password) < 8:
                return {"success": False, "message": "Password must be at least 8 characters"}
            user.password_hash = generate_password_hash(new_password)
        if new_email and new_email.strip().lower() != email:
            # email is the primary key, so swapping it means moving rows
            # across every related table. Not worth the risk here —
            # flag it clearly instead of silently doing nothing.
            return {"success": False, "message": "Changing your email isn't supported yet — contact support"}

        db.commit()
        return {"success": True, "user": user.to_public_dict()}
    finally:
        db.close()


def update_agent_prefs(email, min_rate=None, job_types=None, scan_minutes=None):
    db = get_db()
    try:
        user = db.get(User, email)
        if not user:
            return {"success": False, "message": "User not found"}

        if min_rate is not None:
            user.agent_min_rate = int(min_rate)
        if job_types is not None:
            user.agent_job_types = job_types if isinstance(job_types, str) else ",".join(job_types)
        if scan_minutes is not None:
            user.agent_scan_minutes = int(scan_minutes)

        db.commit()
        return {"success": True, "user": user.to_public_dict()}
    finally:
        db.close()


def update_alert_prefs(email, keywords=None, min_rate=None, enabled=None, sms_enabled=None, phone=None):
    db = get_db()
    try:
        user = db.get(User, email)
        if not user:
            return {"success": False, "message": "User not found"}

        if keywords is not None:
            user.alert_keywords = keywords if isinstance(keywords, str) else ",".join(keywords)
        if min_rate is not None:
            user.alert_min_rate = int(min_rate)
        if enabled is not None:
            user.alerts_enabled = bool(enabled)
        if sms_enabled is not None:
            user.alert_sms_enabled = bool(sms_enabled)
        if phone is not None:
            user.alert_phone = phone

        db.commit()
        return {"success": True, "user": user.to_public_dict()}
    finally:
        db.close()


# ─────────────────────────────────────────────
# SEARCH HISTORY
# ─────────────────────────────────────────────

def add_search_to_history(email, query, platforms, result_count):
    db = get_db()
    try:
        db.add(SearchHistoryItem(
            email=email, query=query or "",
            platforms=json.dumps(platforms or []), result_count=result_count or 0,
        ))
        db.commit()
    finally:
        db.close()


def get_search_history(email):
    db = get_db()
    try:
        items = (
            db.query(SearchHistoryItem)
            .filter(SearchHistoryItem.email == email)
            .order_by(SearchHistoryItem.timestamp.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "query": i.query,
                "platforms": json.loads(i.platforms or "[]"),
                "result_count": i.result_count,
                "timestamp": i.timestamp.isoformat(),
            }
            for i in items
        ]
    finally:
        db.close()


def clear_search_history(email):
    db = get_db()
    try:
        db.query(SearchHistoryItem).filter(SearchHistoryItem.email == email).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────
# CV SKILLS
# ─────────────────────────────────────────────

def save_cv_skills(email, skills_detected):
    db = get_db()
    try:
        user = db.get(User, email)
        if user:
            user.last_cv_skills = json.dumps(skills_detected or [])
            db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

def add_notification(email, title, body, kind="info"):
    db = get_db()
    try:
        db.add(Notification(email=email, title=title, body=body, kind=kind))
        db.commit()
    finally:
        db.close()


def get_notifications(email):
    db = get_db()
    try:
        items = (
            db.query(Notification)
            .filter(Notification.email == email)
            .order_by(Notification.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": n.id, "title": n.title, "body": n.body, "kind": n.kind,
                "read": n.read, "created_at": n.created_at.isoformat(),
            }
            for n in items
        ]
    finally:
        db.close()


def mark_notifications_read(email):
    db = get_db()
    try:
        (
            db.query(Notification)
            .filter(Notification.email == email, Notification.read == False)  # noqa: E712
            .update({"read": True}, synchronize_session=False)
        )
        db.commit()
    finally:
        db.close()
