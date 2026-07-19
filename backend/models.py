"""
JOBSK DATABASE MODELS
======================
This replaces the old users.json / sessions.json file storage with a real
database (SQLite by default, or Postgres if you set DATABASE_URL).

WHY THIS MATTERS (read this if you're wondering why accounts used to
disappear): the old version stored everything in plain .json files on disk.
That's fine on your own laptop, but almost every free hosting platform
(Render free tier, Railway free tier, etc.) wipes local disk files every
time the server restarts or redeploys — which on a free tier happens
constantly (the server "sleeps" after ~15 minutes of no traffic and loses
its disk when it wakes back up). So every time that happened, users.json
went back to empty and everyone had to sign up again. A database file has
the exact same problem UNLESS it lives on a persistent disk or a hosted
database service — see the README for which free hosts actually keep your
data.

DATABASE_URL env var:
    - Not set -> uses a local SQLite file backend/jobsk.db (great for
      development, and fine for production if your host gives you a
      persistent disk, e.g. Fly.io, Railway with a volume, PythonAnywhere).
    - Set to a Postgres URL (e.g. from Supabase or Neon's free tier) ->
      uses that instead. Free hosted Postgres is the most reliable way to
      make sure accounts survive server restarts on a free host.
"""

import os
import json
from datetime import datetime, timedelta
from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Render/Heroku-style URLs sometimes start with postgres:// which
    # SQLAlchemy's modern driver name no longer accepts directly.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    db_path = os.path.join(os.path.dirname(__file__), "jobsk.db")
    try:
        # On Vercel, the deployed function's own folder is READ-ONLY (only
        # /tmp is writable), so if DATABASE_URL hasn't been set yet, writing
        # here would throw and take the whole app down on every request.
        # This checks writability up front and falls back to /tmp so the
        # app still boots. /tmp on Vercel is wiped between cold starts, so
        # this fallback is NOT persistent storage — it only keeps the site
        # from crashing. Set DATABASE_URL (see DEPLOY_VERCEL.md) for
        # accounts that actually survive between requests.
        with open(db_path, "a"):
            pass
    except OSError:
        db_path = "/tmp/jobsk.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    email = Column(String, primary_key=True)
    name = Column(String, nullable=False, default="")
    phone = Column(String, default="")
    dob = Column(String, default="")
    age = Column(Integer, nullable=True)
    password_hash = Column(String, nullable=True)  # null for Google-only accounts
    skills = Column(Text, default="")
    provider = Column(String, default="email")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Agent / alert preferences (previously hardcoded in the HTML!)
    alerts_enabled = Column(Boolean, default=True)
    alert_keywords = Column(String, default="")
    alert_min_rate = Column(Integer, default=0)
    alert_sms_enabled = Column(Boolean, default=False)
    alert_phone = Column(String, default="")
    agent_min_rate = Column(Integer, default=0)
    agent_job_types = Column(String, default="all")
    agent_scan_minutes = Column(Integer, default=1)

    last_cv_skills = Column(Text, default="[]")   # JSON list
    last_seen_job_urls = Column(Text, default="[]")  # JSON list, used to dedupe alert emails

    def skills_list(self):
        try:
            return json.loads(self.last_cv_skills or "[]")
        except Exception:
            return []

    def seen_urls(self):
        try:
            return json.loads(self.last_seen_job_urls or "[]")
        except Exception:
            return []

    def to_public_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "provider": self.provider,
            "alerts_enabled": self.alerts_enabled,
            "alert_keywords": self.alert_keywords,
            "alert_min_rate": self.alert_min_rate,
            "alert_sms_enabled": self.alert_sms_enabled,
            "alert_phone": self.alert_phone,
            "agent_min_rate": self.agent_min_rate,
            "agent_job_types": self.agent_job_types,
            "agent_scan_minutes": self.agent_scan_minutes,
        }


class Session(Base):
    __tablename__ = "sessions"

    token = Column(String, primary_key=True)
    email = Column(String, ForeignKey("users.email"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class SearchHistoryItem(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, ForeignKey("users.email"), nullable=False)
    query = Column(String, default="")
    platforms = Column(String, default="[]")  # JSON list
    result_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, ForeignKey("users.email"), nullable=False)
    title = Column(String, default="")
    body = Column(Text, default="")
    kind = Column(String, default="info")  # info | match | alert_sent | cv
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)


class PasswordReset(Base):
    """Backs the 'Forgot password?' link, which in v2 just showed a fake
    'reset link sent' toast and did nothing at all."""
    __tablename__ = "password_resets"

    token = Column(String, primary_key=True)
    email = Column(String, ForeignKey("users.email"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    """Call this per-request; caller is responsible for closing it."""
    return SessionLocal()
