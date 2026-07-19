# Deploying Jobsk to Vercel — step by step

This project is now set up as ONE Vercel project that serves both the
frontend (`public/`) and the Flask backend (`backend/app.py`) from the
same domain. Read "What Vercel actually is" below before you start —
it explains why a couple of extra steps (Postgres, external cron) are
required and not optional.

---

## 0. What Vercel actually is (read this first)

Vercel does not keep a Python process running 24/7 like a normal
server. Every request spins up your Flask app fresh, answers it, and
the instance can disappear right after. Two consequences:

1. **SQLite breaks.** A SQLite file written during one request is not
   guaranteed to exist for the next one. You must use a real hosted
   Postgres database (step 2) — this is not optional on Vercel.
2. **The in-process "check every 1 minute" scheduler breaks.** There is
   no long-lived process for `scheduler.py`'s background thread to run
   in. Instead, a free external cron service pings a URL on your app
   every few minutes, and that request is what actually checks for new
   jobs and sends email alerts (step 6). This is genuinely how
   "serverless + scheduled jobs" is done — it's not a workaround.

Everything else (login, search, chat, CV upload) works completely
normally on Vercel, on demand, the instant a user requests it.

---

## 1. Push the project to GitHub

1. Go to [github.com](https://github.com) and log in (or create a free account).
2. Click the **+** icon top-right → **New repository**.
3. Repository name: `jobsk` (or anything you like). Keep it **Private** if you don't want the code public. Do NOT check "Add a README" — you already have one. Click **Create repository**.
4. GitHub will show you a page with commands. On your own computer, open a terminal **inside the unzipped project folder** (the one containing `backend/`, `public/`, `vercel.json`) and run, one at a time:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/jobsk.git
   git push -u origin main
   ```
   Replace `YOUR-USERNAME` with your actual GitHub username, and the URL with the exact one GitHub showed you.
5. If you don't have `git` installed on Windows, install it from [git-scm.com](https://git-scm.com/download/win) first, then re-open your terminal (VS Code's terminal works fine) and retry.
6. Refresh the GitHub page — you should see `backend/`, `public/`, `vercel.json`, etc.

**Check `.gitignore` did its job:** on GitHub, open the repo and confirm there is **no** `backend/.env` file listed. If you do see it, you accidentally committed your real secrets — delete the repo, remove `.env` locally, and redo this step. `.gitignore` in this project is already set up to prevent this as long as you never `git add -f` it.

---

## 2. Create a free hosted Postgres database

Pick ONE — both have permanent free tiers:

### Option A: Neon
1. Go to [neon.tech](https://neon.tech) → sign up free (GitHub sign-in is fastest).
2. Click **Create a project**. Any name/region is fine. Click **Create**.
3. On the project page, find the **Connection string** box. Copy the full string — it looks like `postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require`.
4. Keep this tab open — you'll paste this string into Vercel in step 4.

### Option B: Supabase
1. Go to [supabase.com](https://supabase.com) → sign up free.
2. **New project** → set a database password (write it down) → wait ~2 minutes for it to provision.
3. Go to **Project Settings → Database → Connection string → URI**. Copy it, and replace `[YOUR-PASSWORD]` in the string with the password you set.

Either way, you now have one Postgres connection string — this is your `DATABASE_URL`.

---

## 3. Import the project into Vercel

1. Go to [vercel.com](https://vercel.com) → sign up / log in (use **"Continue with GitHub"** — this is what lets Vercel see your repos).
2. Click **Add New... → Project**.
3. Find your `jobsk` repo in the list and click **Import**.
4. Vercel auto-detects it as a Python/Flask project from `requirements.txt` and `pyproject.toml`. Leave Framework Preset, Build Command, and Output Directory on their defaults — don't touch them.
5. **Before clicking Deploy**, open the **Environment Variables** section on this same screen and add the variables in the next step.

---

## 4. Set your Environment Variables in Vercel

Still on the import screen (or later under **Project → Settings → Environment Variables** if you already deployed), add each of these as a Name/Value pair. Apply each to **Production, Preview, and Development** (Vercel shows checkboxes for this — check all three).

| Name | Value |
|---|---|
| `DATABASE_URL` | The Postgres connection string from step 2 |
| `EMAIL_ADDRESS` | Your Gmail address, e.g. `youragent@gmail.com` |
| `EMAIL_PASSWORD` | A Gmail **App Password** — see step 5 below, NOT your normal Gmail password |
| `CRON_SECRET` | Any random string you make up, e.g. `jobsk-cron-9f3k2` |
| `DISABLE_SCHEDULER` | `1` |
| `GOOGLE_CLIENT_ID` | Your Google OAuth Client ID, if you use "Sign in with Google" (optional) |
| `ANTHROPIC_API_KEY` | Only if you want the chatbot to use a real Claude model (optional) |

Click **Deploy**. First deploys take 1-3 minutes. When it finishes, Vercel gives you a live URL like `https://jobsk-yourname.vercel.app` — open it, you should see the login page.

---

## 5. Get a Gmail App Password (this is the #1 cause of "email doesn't send")

Gmail will silently refuse your normal account password from any script — it requires a special 16-character **App Password**, and that only exists once 2-Step Verification is turned on.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security).
2. Under "How you sign in to Google", turn ON **2-Step Verification** if it isn't already (follow Google's prompts — phone number or authenticator app).
3. Once that's on, go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Under "App name", type `Jobsk` → click **Create**.
5. Google shows a 16-character password in a yellow box, in 4 groups of 4 letters (e.g. `abcd efgh ijkl mnop`). Copy it.
6. Paste it as the `EMAIL_PASSWORD` Vercel environment variable (step 4). Spaces are fine either way — `emailer.py` in this project strips them automatically.
7. Redeploy (Vercel → your project → **Deployments** → ⋯ on the latest → **Redeploy**) so the new environment variable takes effect — Vercel does NOT hot-reload env vars into an already-running deployment.

**Test it directly, independent of everything else:**
```
curl -X POST https://YOUR-APP.vercel.app/api/debug/test-email \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"you@example.com\"}"
```
- `{"success": true, ...}` → Gmail SMTP works. If real alert emails still don't arrive, the cause is upstream of email sending — see step 6 and the checklist below.
- `{"success": false, "message": "..."}` → the message tells you exactly what Gmail rejected. Fix that (usually: 2-Step Verification wasn't actually on yet, or the password has a typo) and try again.

---

## 6. Make alerts actually fire on a schedule (external cron)

Vercel's own free-tier Cron Jobs only run once a day, which isn't
useful for "check every few minutes." Use a free external pinger
instead — it hits your `/api/cron/run-alerts` endpoint on Vercel, which
runs the exact same check-and-email logic as the local scheduler did.

1. Go to [cron-job.org](https://cron-job.org) → sign up free.
2. **Create cronjob**.
3. Title: `Jobsk alert check`.
4. URL:
   ```
   https://YOUR-APP.vercel.app/api/cron/run-alerts?secret=YOUR_CRON_SECRET
   ```
   using the exact `CRON_SECRET` value you set in step 4.
5. Schedule: every 5 minutes (the free tier's minimum interval).
6. Save. cron-job.org will now hit that URL every 5 minutes, 24/7, whether or not anyone has your site open — this is what makes alerts real again on Vercel.

---

## 7. Why an email might still not arrive (checklist, in order)

Assuming step 5's test email succeeded, real job alerts are gated by
several real conditions — if any one is false, no email goes out for a
given user, correctly:

1. **The user uploaded a CV.** No CV → no detected skills → the
   scheduler skips that user entirely (`if not skills: continue` in
   `scheduler.py`). Go to CV Upload in the app and upload one.
2. **Alerts are enabled for that account.** Settings → Job Alerts →
   toggle on, then Save (this calls `/api/user/alerts`, confirm it
   returns `success: true` in the browser's Network tab).
3. **There's an actually-NEW job to alert about.** The app deliberately
   only emails jobs it hasn't already told that user about
   (`seen_urls` in `models.py`) — if nothing new turned up in that scan,
   correctly no email is sent. Uploading a very common-skill CV (e.g.
   "Python") makes a new match much more likely to test with.
4. **The cron pinger from step 6 is actually running.** Check
   cron-job.org's execution history for that job — it shows the HTTP
   status Vercel returned on each run.
5. **Check the Vercel function logs.** Project → your deployment →
   **Logs**, filter for `/api/cron/run-alerts` or `[emailer]` /
   `[scheduler]` — every send attempt prints a line either way.

---

## 8. Redeploying after future code changes

```
git add .
git commit -m "describe what changed"
git push
```
Vercel redeploys automatically on every push to `main` — no manual redeploy step needed except after changing Environment Variables (step 5.7).
