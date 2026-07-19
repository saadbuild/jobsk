"""
JOBSK BACKGROUND SCHEDULER (new in v3)

This is what actually makes alerts work "even when the website is closed."
In v2, the auto-refresh only ran as a JavaScript setInterval() in the
user's browser tab — close the tab, and it stops completely; nothing was
ever running on the server on its own.

Here, APScheduler runs INSIDE the Flask process itself and fires on a
timer (default: every 1 minute, matching what you asked for) regardless
of whether any browser is open. For each user who has alerts enabled and
has uploaded a CV, it searches real job sources, compares against jobs
that user has already been alerted about, and emails (and optionally
texts) only the new ones.

IMPORTANT — what "runs even when the site is off" actually requires:
This only works while the BACKEND SERVER PROCESS is alive. That's true
of your own computer only while python app.py is running, and true of a
paid/always-on host. Render's FREE web service tier specifically puts
the process to sleep after ~15 minutes with no incoming HTTP traffic —
so on a free Render deploy, this scheduler would also go to sleep, and a
scheduled email 40 minutes later just wouldn't fire until something wakes
the server back up.

The practical free-tier fix: use an external "uptime pinger" like
https://cron-job.org or UptimeRobot (both free) to hit this reliably:
    GET https://<your-backend>/api/cron/run-alerts?secret=YOUR_CRON_SECRET
every 1-5 minutes. That keeps a free Render service awake AND guarantees
the check actually runs on schedule — see /api/cron/run-alerts in app.py
and CRON_SECRET in .env.example.
"""

import json
import os
from apscheduler.schedulers.background import BackgroundScheduler

from models import get_db, User
from job_matcher import search_jobs, rank_jobs_for_cv
from emailer import send_job_alert_email
from notifier import send_sms_alert
from auth import add_notification

SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "1"))

_scheduler = None


def run_alert_check():
    """The core job: for every user with alerts on and a CV uploaded,
    search real sources, filter to genuinely new listings, and notify."""
    db = get_db()
    try:
        users = db.query(User).filter(User.alerts_enabled == True).all()  # noqa: E712
        for user in users:
            skills = user.skills_list()
            if not skills:
                continue

            query = " ".join(skills[:5])
            jobs = search_jobs(query, None, user.alert_min_rate or 0, 100000, "all")
            jobs = rank_jobs_for_cv(" ".join(skills), jobs, top_n=10)

            seen = set(user.seen_urls())
            new_jobs = [j for j in jobs if j["url"] not in seen]

            if new_jobs:
                send_job_alert_email(user.email, new_jobs)
                add_notification(
                    user.email,
                    f"🤖 {len(new_jobs)} new job match{'es' if len(new_jobs)!=1 else ''}",
                    f"Emailed to {user.email}: " + ", ".join(j['title'] for j in new_jobs[:3]),
                    kind="match",
                )
                if user.alert_sms_enabled and user.alert_phone:
                    top = new_jobs[0]
                    send_sms_alert(
                        user.alert_phone,
                        f"Jobsk: new match — {top['title']} ({top['platform']}). "
                        f"Check your email for details.",
                    )

                all_seen = list(seen | {j["url"] for j in new_jobs})
                user.last_seen_job_urls = json.dumps(all_seen[-200:])  # cap growth
                db.commit()
    except Exception as e:
        print(f"[scheduler] run_alert_check failed: {e}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_alert_check, "interval", minutes=SCAN_INTERVAL_MINUTES,
        id="alert_check", replace_existing=True, max_instances=1,
    )
    _scheduler.start()
    print(f"[scheduler] Started — checking for new job matches every {SCAN_INTERVAL_MINUTES} minute(s)")
    return _scheduler
