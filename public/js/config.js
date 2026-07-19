/* ═══════════════════════════════════════════
   JOBSK — SHARED CONFIG
   auth.js and main.js both read BACKEND_URL from here,
   instead of each having their own copy that could
   drift out of sync.

   On Vercel, the frontend (public/) and the Flask backend
   (backend/app.py) are ONE project on ONE domain, so the
   frontend just calls "/api/..." on itself — no separate
   backend URL, no CORS to configure. Locally, index.html is
   usually opened straight from disk (or a simple static
   server), so it needs the full http://127.0.0.1:5000 address
   of your separately-running `python app.py`. This picks the
   right one automatically based on where the page is loaded
   from, so you never have to remember to change it back and
   forth between local testing and the live Vercel site.
   ═══════════════════════════════════════════ */
const BACKEND_URL =
  (location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:')
    ? 'http://127.0.0.1:5000'
    : '';

// How often the frontend nudges the agent to check for new jobs while
// the tab is open. The real always-on checking happens server-side in
// scheduler.py regardless of this value — see README.
const AUTO_REFRESH_MS = 60 * 1000; // 1 minute
