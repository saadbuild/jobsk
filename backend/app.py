"""
JOBSK BACKEND SERVER v3
========================
What changed from v2 (see README.md for the full writeup):
  - Real database (models.py) instead of JSON files -> accounts and
    settings actually persist.
  - Settings screens (profile / agent prefs / alerts) now have real
    endpoints that save to the database, instead of just showing a toast.
  - Job search hits real, free job APIs instead of a hardcoded list.
  - A background scheduler (scheduler.py) checks for new matches and
    emails/texts users automatically, independent of the browser.
  - CV upload actually reads PDF/DOCX/TXT and runs real TF-IDF matching.
  - Facebook/Instagram/YouTube "social scanning" removed entirely.

To run locally:
    cd backend
    pip install -r ../requirements.txt
    python app.py
Server starts at http://127.0.0.1:5000

To run on Vercel: see DEPLOY_VERCEL.md in the project root. Vercel runs
this file as a serverless function (it imports `app` from here — it
never runs the `if __name__ == "__main__":` block below). Set
DISABLE_SCHEDULER=1 in your Vercel project's Environment Variables so
the in-process scheduler guard right below knows not to start it there.
"""

import os
import sys

# Vercel's Python runtime resolves this module as "backend.app", with the
# working directory set to the project root — NOT this file's own folder.
# The sibling imports below (models, auth, chatbot, ...) use bare names
# like "from models import ...", so this folder must be on sys.path for
# those imports to resolve, both locally and on Vercel.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

from models import init_db
from chatbot import get_chatbot_response
from job_matcher import search_jobs, calculate_cv_match, rank_jobs_for_cv
from emailer import send_job_alert_email, send_welcome_email, send_password_reset_email, send_test_email
from scheduler import start_scheduler, run_alert_check
import auth

app = Flask(__name__)
CORS(app)

init_db()

# On Vercel (serverless), a background thread that ticks every minute
# does NOT work — a Vercel Function only runs while it's actively
# handling a request, then freezes or shuts down entirely, so a
# BackgroundScheduler started inside it just dies. Set DISABLE_SCHEDULER=1
# as an Environment Variable in your Vercel project (see DEPLOY_VERCEL.md)
# so this line is skipped there; leave it unset locally / on a host that
# keeps one process running 24/7, where the in-process scheduler is fine.
# On Vercel, /api/cron/run-alerts (below) is what actually checks for new
# jobs and emails users, triggered by a free external pinger on a schedule.
if not os.environ.get("DISABLE_SCHEDULER"):
    start_scheduler()

CRON_SECRET = os.getenv("CRON_SECRET", "")


def get_user_from_request():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return auth.get_user_from_token(token)


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    result = auth.register_user(
        name=data.get("name"), email=data.get("email"), phone=data.get("phone", ""),
        dob=data.get("dob"), password=data.get("password"), skills=data.get("skills", "")
    )
    if result["success"]:
        send_welcome_email(data.get("email"), data.get("name"))
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    result = auth.login_user(
        identifier=data.get("identifier"), method=data.get("method", "email"),
        password=data.get("password")
    )
    return jsonify(result), (200 if result["success"] else 401)


@app.route("/api/auth/verify", methods=["GET"])
def verify_session():
    """Frontend calls this once on load. If the token is invalid/expired,
    it means the server-side session is gone (e.g. after a redeploy that
    lost the database — see README) and the user needs to sign in again,
    rather than the app silently behaving as if they're logged in."""
    user = get_user_from_request()
    if not user:
        return jsonify({"valid": False}), 401
    return jsonify({"valid": True, "user": user.to_public_dict()})


@app.route("/api/auth/google", methods=["POST"])
def google_login():
    """SETUP: pip install google-auth, then set GOOGLE_CLIENT_ID below to
    your real client ID from https://console.cloud.google.com"""
    data = request.json or {}
    credential = data.get("credential")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
        name = idinfo.get("name", email.split("@")[0])
        result = auth.login_or_register_google(email, name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": f"Google verification failed: {str(e)}"}), 401


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    """Real password reset (v2's 'Forgot password?' link just showed a
    fake 'link sent' toast and emailed nothing)."""
    data = request.json or {}
    email = (data.get("email") or "").strip()
    frontend_url = (data.get("frontend_url") or "").rstrip("/")

    token = auth.request_password_reset(email)
    if token and frontend_url:
        reset_link = f"{frontend_url}/reset-password.html?token={token}"
        send_password_reset_email(email, reset_link)
    # Always return the same generic message, whether or not the email
    # was registered — this avoids leaking which emails have accounts.
    return jsonify({"success": True, "message": "If that email has an account, a reset link is on its way."})


@app.route("/api/auth/reset-password", methods=["POST"])
def do_reset_password():
    data = request.json or {}
    token = data.get("token")
    password = data.get("password")
    if not token or not password or len(password) < 8:
        return jsonify({"success": False, "message": "Please provide a token and an 8+ character password"}), 400
    result = auth.reset_password(token, password)
    return jsonify(result), (200 if result["success"] else 400)


# ─────────────────────────────────────────────
# PROFILE / SETTINGS ROUTES (missing entirely in v2)
# ─────────────────────────────────────────────

@app.route("/api/user/profile", methods=["PUT"])
def update_profile():
    user = get_user_from_request()
    if not user:
        return jsonify({"success": False, "message": "Not signed in"}), 401
    data = request.json or {}
    result = auth.update_profile(
        email=user.email, name=data.get("name"), new_email=data.get("email"),
        skills=data.get("skills"), new_password=data.get("password") or None,
    )
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/user/agent-prefs", methods=["PUT"])
def update_agent_prefs():
    user = get_user_from_request()
    if not user:
        return jsonify({"success": False, "message": "Not signed in"}), 401
    data = request.json or {}
    result = auth.update_agent_prefs(
        email=user.email, min_rate=data.get("min_rate"),
        job_types=data.get("job_types"), scan_minutes=data.get("scan_minutes"),
    )
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/user/alerts", methods=["PUT"])
def update_alerts():
    user = get_user_from_request()
    if not user:
        return jsonify({"success": False, "message": "Not signed in"}), 401
    data = request.json or {}
    result = auth.update_alert_prefs(
        email=user.email, keywords=data.get("keywords"), min_rate=data.get("min_rate"),
        enabled=data.get("enabled"), sms_enabled=data.get("sms_enabled"), phone=data.get("phone"),
    )
    return jsonify(result), (200 if result["success"] else 400)


# ─────────────────────────────────────────────
# CHATBOT
# ─────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    return jsonify({"response": get_chatbot_response(data.get("message", ""))})


# ─────────────────────────────────────────────
# JOB SEARCH (now hits real sources)
# ─────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def search():
    data = request.json or {}
    query = data.get("query", "")
    platforms = data.get("platforms", [])
    min_rate = data.get("min_rate", 0)
    max_rate = data.get("max_rate", 100000)
    job_type = data.get("job_type", "all")
    email = data.get("email")

    jobs = search_jobs(query, platforms, min_rate, max_rate, job_type)

    user = auth.get_user_from_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if user and user.skills_list():
        jobs = rank_jobs_for_cv(" ".join(user.skills_list()), jobs)

    if email:
        auth.add_search_to_history(email, query, platforms, len(jobs))

    return jsonify({"jobs": jobs, "count": len(jobs)})


@app.route("/api/search/history", methods=["GET"])
def search_history():
    email = request.args.get("email")
    if not email:
        return jsonify({"history": []})
    return jsonify({"history": auth.get_search_history(email)})


@app.route("/api/search/history", methods=["DELETE"])
def delete_search_history():
    user = get_user_from_request()
    if not user:
        return jsonify({"success": False, "message": "Not signed in"}), 401
    auth.clear_search_history(user.email)
    return jsonify({"success": True})


# ─────────────────────────────────────────────
# CV UPLOAD / MATCHING + AUTO-REFRESH SEARCH
# ─────────────────────────────────────────────

@app.route("/api/cv/analyze", methods=["POST"])
def analyze_cv():
    if "cv" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["cv"]
    email = request.form.get("email")
    result = calculate_cv_match(file)
    cv_text = result.pop("cv_text", "")

    if email and result.get("success"):
        auth.save_cv_skills(email, result["skills_detected"])
        auth.add_notification(
            email, "CV analysis complete",
            f"{result['skill_count']} skills detected. Match score: {result['match_score']}%.",
            kind="cv",
        )

    return jsonify(result)


@app.route("/api/cv/auto-search", methods=["POST"])
def auto_search():
    """Kept for the frontend's minute-timer as an immediate on-demand check;
    the real always-on version of this now lives in scheduler.py."""
    data = request.json or {}
    email = data.get("email")
    platforms = data.get("platforms", [])

    user = auth.get_user_from_token(request.headers.get("Authorization", "").replace("Bearer ", "")) \
        or (email and _user_by_email(email))
    skills = user.skills_list() if user else []

    if not skills:
        return jsonify({"jobs": [], "message": "No CV uploaded yet"})

    query = " ".join(skills[:5])
    jobs = search_jobs(query, platforms, 0, 100000, "all")
    jobs = rank_jobs_for_cv(" ".join(skills), jobs)

    return jsonify({"jobs": jobs, "count": len(jobs), "based_on_skills": skills})


def _user_by_email(email):
    from models import get_db, User
    db = get_db()
    try:
        return db.get(User, email)
    finally:
        db.close()



# ─────────────────────────────────────────────
# NOTIFICATIONS (new — previously 100% hardcoded fake data)
# ─────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    user = get_user_from_request()
    if not user:
        return jsonify({"notifications": []})
    return jsonify({"notifications": auth.get_notifications(user.email)})


@app.route("/api/notifications/read", methods=["POST"])
def mark_notifications_read():
    user = get_user_from_request()
    if not user:
        return jsonify({"success": False}), 401
    auth.mark_notifications_read(user.email)
    return jsonify({"success": True})


# ─────────────────────────────────────────────
# EMAIL ALERT ROUTES
# ─────────────────────────────────────────────

@app.route("/api/alerts/send", methods=["POST"])
def send_alert():
    data = request.json or {}
    success = send_job_alert_email(data.get("email"), data.get("jobs", []))
    return jsonify({"success": success})


@app.route("/api/debug/test-email", methods=["POST"])
def debug_test_email():
    """Diagnostic endpoint — sends a plain test email straight through
    emailer.py, bypassing CV upload / alerts-enabled / "new jobs only"
    logic entirely. Use this to check ONLY whether EMAIL_ADDRESS and
    EMAIL_PASSWORD (Gmail App Password) actually work, before worrying
    about whether the scheduler or job matching is the problem.

        curl -X POST https://<your-backend>/api/debug/test-email \
             -H "Content-Type: application/json" \
             -d '{"email":"you@example.com"}'

    Returns success:true only if Gmail's SMTP server actually accepted
    the message; on failure it returns the real exception message from
    smtplib so you can see exactly what Gmail rejected (bad password,
    2-Step Verification not enabled, etc.) instead of guessing.
    """
    data = request.json or {}
    to_email = (data.get("email") or "").strip()
    if not to_email:
        return jsonify({"success": False, "message": "Provide {\"email\": \"you@example.com\"}"}), 400
    result = send_test_email(to_email)
    return jsonify(result), (200 if result["success"] else 500)


# ─────────────────────────────────────────────
# EXTERNAL CRON TRIGGER
# For free hosts whose server sleeps: point an external pinger
# (cron-job.org, UptimeRobot — both free) at this URL every 1-5 minutes.
# It both wakes the server up and force-runs the alert check.
# ─────────────────────────────────────────────

@app.route("/api/cron/run-alerts", methods=["GET", "POST"])
def cron_run_alerts():
    if CRON_SECRET and request.args.get("secret") != CRON_SECRET:
        return jsonify({"success": False, "message": "Invalid secret"}), 403
    run_alert_check()
    return jsonify({"success": True})


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "Jobsk backend v3 is running",
        "database": os.getenv("DATABASE_URL", "sqlite (local file)"),
        "endpoints": [
            "/api/auth/register", "/api/auth/login", "/api/auth/verify", "/api/auth/google",
            "/api/auth/forgot-password", "/api/auth/reset-password",
            "/api/user/profile", "/api/user/agent-prefs", "/api/user/alerts",
            "/api/chat", "/api/search", "/api/search/history",
            "/api/cv/analyze", "/api/cv/auto-search",
            "/api/notifications", "/api/notifications/read",
            "/api/alerts/send", "/api/cron/run-alerts",
        ]
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  JOBSK BACKEND SERVER v3 STARTING")
    print("  Visit: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, use_reloader=False)
