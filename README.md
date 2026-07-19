# Jobsk v3 — what changed and why

This is a rebuild of your app that fixes the bugs you described and a few
more of the same kind that I found while going through the code. Read
this top section before you run anything — it explains *why* things were
broken, not just that they're fixed, because a couple of these will come
back if you deploy carelessly.

---

## 1. "I have to make an account every time"

**Root cause, most likely:** v2 stored every account in a plain
`users.json` file on the server's local disk. Free hosting tiers (Render
free web services, in particular) do **not** have persistent disk — the
server "sleeps" after ~15 minutes idle, and when it wakes back up (or
redeploys), any files it wrote locally are gone. `users.json` silently
went back to empty, so every returning visitor looked like a brand-new
user. This is invisible in local testing (your own machine keeps the
file) and only shows up once deployed — which matches "every time" being
confusing rather than obviously broken.

**Second contributing cause:** if the backend was briefly unreachable
(e.g. a free Render service waking up, which can take 30–60 seconds),
v2's frontend silently fell back to a **fake "demo mode" login** that
was never a real account. That's a second, sneakier way to end up
"logged in" with nothing real behind it.

**What I changed:**
- Real database (`backend/models.py`, SQLite by default) instead of
  JSON files. See §5 below for the one thing you still need to do to
  make this bulletproof on a free host.
- Removed the silent demo-mode fallback. If the backend can't be
  reached, you now get a clear "could not reach the server" message
  instead of a fake session.
- Added `/api/auth/verify`, called once when the app loads, so if the
  server ever *does* lose its session data, you get signed out cleanly
  with an explanation instead of the app half-working with stale data.

## 2. Settings said "saved" but nothing changed

This was real, and it wasn't just Settings. **Every one of these buttons
called nothing but `showToast(...)` — no backend request at all:**

- Settings → Save profile
- Settings → Save agent settings
- Job Alerts → Save alert settings
- Search History → Clear history (only cleared the on-screen list, not
  your account)
- Notifications → Mark all read
- CV upload (`processCVFile`) — showed a fake "10 skills detected" toast
  after a `setTimeout()`, uploaded nothing, called no real endpoint, even
  though a real `/api/cv/analyze` endpoint already existed and was just
  never wired up
- **Login page → "Forgot password?"** — showed "reset link sent to your
  email" and sent nothing. Same bug, different screen.

**What I changed:** every one of these now calls a real backend endpoint
that writes to the database, and the frontend reflects the actual saved
values on load instead of showing hardcoded placeholder data
("Ali Hassan", "ali@email.com", a fixed 87% match score, etc.). I also
built out the password reset flow for real: `/api/auth/forgot-password`
emails a real one-time link, and `public/pages/reset-password.html` is
a new page that completes it.

## 3. "Connect it to real freelancing platform APIs"

**The honest answer:** Upwork, Fiverr, and LinkedIn do not give
individual developers open, instant, free access to their job listings.

| Platform | Status |
|---|---|
| Upwork | Job-search API access now requires an approved partner/agency relationship — not available to individual developers |
| Fiverr | No public API for gigs or buyer requests, period |
| LinkedIn | Jobs API requires LinkedIn's partner approval process (weeks, usually only granted to ATS vendors) |
| Freelancer.com | Has an API, but it's scoped to their own affiliates with limited/rate-capped project search |

The only way to make v2's promise of live Upwork/Fiverr/LinkedIn data
literally true would be scraping those sites, which breaks their Terms
of Service. I didn't build that.

**What I did instead:** wired up real, free, keyless job-search APIs so
the app shows genuinely live data:

- **Remotive** — `https://remotive.com/api/remote-jobs`
- **RemoteOK** — `https://remoteok.com/api`
- **Arbeitnow** — `https://www.arbeitnow.com/api/job-board-api`

The Platforms screen now honestly labels these three "Live" and labels
Upwork/Fiverr/LinkedIn/etc. "Guide only" — you still get real,
substantive how-to guides for those platforms (unchanged from v2, that
content was genuine), just not a fake live feed.

**To add more real sources:** Adzuna and Jooble both have free-tier API
keys and much larger catalogs. There's a ready-to-uncomment
`fetch_adzuna()` function at the bottom of `backend/job_matcher.py` —
add your key to `.env` and register it in the `SOURCES` dict.

## 4. Real notifications — email, and text, even when the site is closed

v2's "auto-refresh" was a `setInterval()` running in your browser tab.
Close the tab, and it stopped completely — nothing was ever running
server-side on its own.

**What I changed:**
- `backend/scheduler.py` runs a background job **inside the Flask
  process itself**, on a timer (default every 1 minute, per your
  request), checking every user with alerts enabled for new job matches
  and emailing them automatically.
- Real email sending was already correctly implemented in v2's
  `emailer.py` (Gmail SMTP) — it just needed credentials and something
  to actually call it. Now the scheduler calls it.
- **SMS is new.** `backend/notifier.py` supports Twilio (small cost
  after free trial credit — this is the reliable way to do SMS) or free
  carrier email-to-SMS gateways (unofficial, can break, but genuinely
  free). See `.env.example` for setup.

**The catch you need to know about:** this only works while the backend
**process** is alive. On your own machine, that's only while
`python app.py` is running. On a free host, the process itself sleeps
after ~15 minutes idle — so a scheduled check 40 minutes later on a
sleeping free instance just won't fire until something wakes it up.

**The fix:** point a free external "uptime pinger" —
[cron-job.org](https://cron-job.org) or
[UptimeRobot](https://uptimerobot.com) — at:

```
GET https://<your-backend-url>/api/cron/run-alerts?secret=YOUR_CRON_SECRET
```

every 1–5 minutes. This both keeps a free Render service awake and
force-runs the check on a guaranteed schedule, which is more reliable
than trusting the in-process scheduler alone on a free tier. Set
`CRON_SECRET` in `.env` to anything random so strangers can't trigger it.

## 5. Persistence on free hosting (read this before you deploy)

A real database fixes bug #1 **only if the database file itself lives
somewhere persistent.** SQLite (the default here) is a real database,
but it's still just a file — on Render's free tier, that file resets
exactly like `users.json` did.

Two honest options:

- **Point `DATABASE_URL` at a free hosted Postgres** — Supabase and Neon
  both have permanent free tiers. This is the most reliable free option
  and needs zero code changes (`models.py` already reads `DATABASE_URL`
  and switches drivers automatically).
- **Use a host with a real persistent disk** — Fly.io (free volume),
  Railway, or PythonAnywhere all keep local files across restarts, so
  plain SQLite is fine there.

If you deploy to Render's free tier with no `DATABASE_URL` set, you will
still hit the "accounts disappear" problem — now for a real,
understandable reason instead of a silent one.

## 6. Facebook / Instagram scanning — removed, not faked better

v2's "Social Media Scan" for Facebook and Instagram returned hardcoded
fake posts. I removed both instead of upgrading the fakery, because they
can't be built honestly: Meta's Graph API only lets an app read posts
from Pages/accounts *it owns* — there's no API for scanning arbitrary
public posts or groups. Doing what the UI implied would require
scraping, which violates Meta's ToS.

YouTube is genuinely different — `search.list` in the YouTube Data API
v3 is a real, public, keyless-approval endpoint. That's the one piece
that's now real (add a free `YOUTUBE_API_KEY`, see `.env.example`).

## 7. The chatbot scrollbar

Root cause: `.chat-window` is a CSS Grid row, and `.chat-msgs` inside it
had `overflow-y: auto` — but grid rows (and flex children) default to
`min-height: auto`, which lets content grow past the box's fixed height
instead of scrolling inside it. The message list was pushing the whole
page taller rather than scrolling internally. Fixed in
`public/css/style.css` by adding `min-height: 0` down the chain
(`.chat-layout` → `.chat-window` → `.chat-msgs`) so the fixed height
actually constrains the content and the scrollbar works.

## 8. Removed / relabeled as not real

- The chatbot's own description used to claim "TF-IDF + cosine
  similarity from the Scikit-learn section" — that was **false**; it was
  plain keyword substring matching. I implemented that for real
  (`rank_jobs_for_cv()` in `job_matcher.py`), so the claim is now true.
  It's also what actually ranks your search results now, not a random
  hardcoded "match %".
- Removed the always-fake home-screen stats ("23 jobs matched today",
  "87% CV match score", "Ali Hassan"). They now show real numbers from
  your account (search count, real skill count, real match readiness) or
  an honest empty state if you haven't used those features yet.
- The chatbot is rule-based by default (fast, free, works offline) — it
  was never a real language model even though the UI called it "ML
  powered." I softened that copy, and added a genuinely optional real
  LLM mode: set `ANTHROPIC_API_KEY` in `.env` and it calls the real
  Claude API instead (small per-message cost once enabled).

---

## Setup

### 1. Install requirements
```
pip install -r requirements.txt
```

### 2. Configure (optional but recommended)
```
cd backend
cp .env.example .env
```
Open `.env` and fill in whichever integrations you want — every one is
optional and the app tells you in the logs/UI when something isn't
configured, rather than pretending it worked. At minimum, set
`EMAIL_ADDRESS` / `EMAIL_PASSWORD` (Gmail App Password) if you want real
email alerts.

### 3. Start the backend
```
python app.py
```
Server starts at `http://127.0.0.1:5000` and creates `backend/jobsk.db`
(SQLite) automatically on first run.

### 4. Open the frontend
Open `public/pages/login.html` first, create an account, and you'll be
redirected to `index.html`.

### 5. If you deploy the frontend and backend to different URLs
Update `BACKEND_URL` in **one place only** now: `public/js/config.js`.
(v2 had this duplicated in two files, which is exactly the kind of thing
that causes "it works locally but not deployed" bugs — now there's a
single source of truth.)

---

## Deploying for free, and later publishing/selling it

See **`DEPLOYMENT_AND_SELLING.md`** for the full walkthrough — free
hosting steps for both frontend and backend with the persistence and
scheduler caveats above baked in, plus a realistic (not hyped) breakdown
of what "publish on Google" and "sell this" actually mean and where you
could realistically do either.

---

## Folder structure
```
jobsk3/
├── README.md                      <- you are here
├── DEPLOYMENT_AND_SELLING.md       <- deployment + monetization guide
├── requirements.txt
├── public/                         <- static frontend, served by Vercel's CDN
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── config.js               <- single BACKEND_URL source of truth
│   │   ├── main.js                 <- every screen wired to real data; menu-button sidebar drawer
│   │   └── auth.js                 <- real forgot-password flow
│   └── pages/
│       ├── login.html              <- Jobsk logo + heading, sign in / create account
│       └── reset-password.html     <- completes the password reset flow
└── backend/
    ├── app.py                      <- all API routes
    ├── models.py                   <- real database (SQLite locally, Postgres on Vercel)
    ├── auth.py                     <- register/login/profile/prefs/reset
    ├── job_matcher.py              <- real job-source APIs + real TF-IDF matching
    ├── emailer.py                  <- real Gmail SMTP sending
    ├── notifier.py                 <- SMS via Twilio or carrier gateway
    ├── scheduler.py                <- background alert checking (local) / cron endpoint (Vercel)
    ├── chatbot.py                  <- rule-based default + optional real Claude API
    └── .env.example                <- every environment variable documented
```
