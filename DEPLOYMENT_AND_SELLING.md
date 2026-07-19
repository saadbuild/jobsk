# Deploying for free, and what "publish / sell it" realistically means

> **Recommended path:** this project is set up to deploy as ONE Vercel
> project (frontend + backend together, no separate hosts, no CORS to
> configure) — see `DEPLOY_VERCEL.md` for that walkthrough. The option
> below is only useful if you specifically want the frontend and backend
> on two different free hosts instead.

## Part 1 — Deploy for free

### Frontend: Netlify
1. [netlify.com](https://netlify.com) → sign up free
2. Drag your `public` folder onto the Netlify dashboard
3. You get a live URL instantly, e.g. `jobsk.netlify.app`

### Backend: Render
1. Push your `backend` folder (and `requirements.txt`) to a GitHub repo
2. [render.com](https://render.com) → sign up free → "New Web Service"
3. Connect your repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `python app.py`
6. Add your `.env` values as environment variables in Render's dashboard
   (Render doesn't read your local `.env` file — you re-enter them here)
7. Once deployed, edit `BACKEND_URL` in `public/js/config.js` — change
   the final `: ''` to your Render URL (e.g.
   `: 'https://jobsk-backend.onrender.com'`), then re-deploy
   the frontend on Netlify so it points at the live backend

### Make accounts actually persist (do this — see README §5)
Pick one:
- Sign up free at [supabase.com](https://supabase.com) or
  [neon.tech](https://neon.tech), create a Postgres database, copy the
  connection string, and set it as `DATABASE_URL` in Render's environment
  variables. No code changes needed.
- Or deploy the backend somewhere with real persistent disk instead of
  Render's free tier — Fly.io's free allowance includes a small
  persistent volume, which works fine with the default SQLite setup.

### Make alerts fire on schedule even on a sleeping free tier
Free accounts at [cron-job.org](https://cron-job.org) or
[UptimeRobot](https://uptimerobot.com) can hit a URL on a timer for free.
Point one at:
```
https://<your-backend>/api/cron/run-alerts?secret=<your CRON_SECRET>
```
every 1–5 minutes. This is what makes "every minute, even when the site
is closed" actually true on a free host — the in-process scheduler alone
isn't enough once the process itself is allowed to sleep.

---

## Part 2 — "Publish it on Google" — what that actually means

There's no single "publish to Google" button for a web app like this.
Depending on what you actually want:

- **Show up in Google Search:** happens automatically once your Netlify
  URL is live and gets a few inbound links / gets crawled. You can speed
  this up for free via
  [Google Search Console](https://search.google.com/search-console) —
  submit your URL, no approval process, no cost.
- **Publish as an Android app:** wrap the site as a Trusted Web Activity
  (TWA) or PWA and submit to the Google Play Console. This has a
  one-time **$25 registration fee** and a review process (usually a few
  days). Not free, but cheap and realistic.
- **Chrome Web Store:** only relevant if you turn part of this into a
  browser extension, which isn't really what this app is — skip this
  path.

There is no free, official way to get a plain web app "featured" by
Google beyond normal search indexing — be skeptical of anything that
claims otherwise.

## Part 3 — Selling it: realistic options, and the trade-off to understand first

**The core issue:** this app depends on a live backend (job search APIs,
email/SMS sending, a database, a background scheduler). "Selling the
code" and "selling the running product" are different businesses with
very different amounts of work:

### Option A — Sell it as a running service (SaaS), you host it
The standard path for something like this. You keep one deployment
running, add [Stripe](https://stripe.com) for subscriptions (free to
integrate, they take a cut per transaction), and charge monthly access.
This is more realistic than selling the code outright, because you
control uptime, keep the APIs configured, and can price for the value
of "it just works" rather than asking a buyer to run their own backend.

### Option B — Sell the source code itself
Buyers would need to supply their own API keys, email credentials, and
hosting — a much smaller and more technical audience. Realistic
marketplaces for this:
- [Gumroad](https://gumroad.com) — simplest, list it, keep ~90%+ per sale
- [CodeCanyon (Envato)](https://codecanyon.net) — bigger built-in
  audience for app templates, but has a review/approval process and
  takes a larger cut
- [AppSumo](https://appsumo.com) — for lifetime-deal-style sales,
  application/approval process, works better once you have some traction

### Option C — Expose it as an API product
If the CV-matching/search logic is the interesting part rather than the
UI, you could wrap the backend's search+matching endpoints as a paid API
and list it on [RapidAPI](https://rapidapi.com), which handles billing
and key management for you.

### Before selling anything
- **You are not a lawyer, and neither am I** — if you plan to charge
  money, worth having an actual privacy policy and terms of service
  (a generator like [Termly](https://termly.io) has a free tier), since
  you're handling emails, phone numbers, and CVs.
- Get the persistence + scheduler fixes above properly running in
  production *first* — "sell it, then discover accounts don't actually
  persist for paying customers" is the worst possible order.
