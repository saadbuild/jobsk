"""
JOBSK JOB MATCHER (v3) — real data, real (small) ML model.

═══════════════════════════════════════════════════════════════════
THE HONEST TRUTH ABOUT "connecting to real freelancing platform APIs"
═══════════════════════════════════════════════════════════════════
Upwork, Fiverr, LinkedIn, and Freelancer.com do NOT give individual
developers open, instant, free access to their job listings:

  - Upwork: closed its public job-search API to new individual developers;
    you now need an approved partner/agency relationship.
  - Fiverr: has no public API for reading gigs or buyer requests at all.
  - LinkedIn: the Jobs API requires an approved partner application
    (weeks of review, usually only granted to larger companies/ATS vendors).
  - Freelancer.com: has a real API, but it requires a registered app,
    OAuth, and is meant for their own affiliates — project-search access
    is limited and rate-capped.

Anything that promised "live Upwork/Fiverr/LinkedIn job feeds" without
one of those official approvals would have to be built by scraping those
sites, which breaks their Terms of Service — I won't build that.

What I DID do instead: wire up real, free, no-approval-needed public job
APIs, so the app now shows genuinely live listings instead of the old
hardcoded DEMO_JOBS list:

  - Remotive       https://remotive.com/api/remote-jobs   (no key)
  - Remote OK       https://remoteok.com/api                (no key)
  - Arbeitnow       https://www.arbeitnow.com/api/job-board-api  (no key)

These are real remote-work/freelance-friendly job boards with genuinely
open APIs. Optional, higher-volume sources you can add with a free key
(see the bottom of this file for exactly where to plug them in):
  - Adzuna   (huge aggregator, free tier key)  https://developer.adzuna.com
  - Jooble   (free key)                         https://jooble.org/api/about

If you later get official Upwork/LinkedIn partner access, add a function
here following the same pattern as fetch_remotive() below and it'll slot
right into search_jobs().
"""

import io
import json
import re
import requests

# ── ML matching (real TF-IDF + cosine similarity, not string.contains) ──
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REQUEST_TIMEOUT = 6  # seconds — free public APIs, keep this snappy

KNOWN_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
    "machine learning", "deep learning", "tensorflow", "pytorch", "nlp",
    "computer vision", "data science", "data analysis", "sql", "postgresql",
    "mongodb", "html", "css", "aws", "azure", "gcp", "docker", "kubernetes",
    "excel", "tableau", "power bi", "writing", "copywriting", "seo",
    "video editing", "premiere pro", "after effects", "photoshop", "figma",
    "ui/ux", "marketing", "wordpress", "shopify", "php", "ruby", "swift",
    "kotlin", "android", "ios", "flutter", "react native", "devops",
    "cybersecurity", "blockchain", "solidity", "scikit-learn", "pandas", "numpy",
]


# ─────────────────────────────────────────────
# REAL DATA SOURCES
# ─────────────────────────────────────────────

def fetch_remotive(query):
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query} if query else {},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])[:25]
        out = []
        for j in jobs:
            out.append({
                "title": j.get("title", "Untitled role"),
                "platform": "Remotive",
                "company": j.get("company_name", ""),
                "rate": j.get("salary") or "Not specified",
                "rate_value": 0,
                "type": j.get("job_type", "remote"),
                "posted": j.get("publication_date", "")[:10],
                "skills": [j.get("category", "").lower()] if j.get("category") else [],
                "description": strip_html(j.get("description", ""))[:400],
                "url": j.get("url", "https://remotive.com"),
            })
        return out
    except Exception as e:
        print(f"[job_matcher] Remotive fetch failed: {e}")
        return []


def fetch_remoteok(query):
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Jobsk-Agent/1.0"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        jobs = data[1:] if data and isinstance(data, list) else []  # index 0 is a disclaimer object
        out = []
        q = (query or "").lower()
        for j in jobs[:60]:
            title = j.get("position", "Untitled role")
            tags = j.get("tags", []) or []
            haystack = (title + " " + " ".join(tags)).lower()
            if q and q not in haystack and not any(w in haystack for w in q.split()):
                continue
            salary_min = j.get("salary_min") or 0
            salary_max = j.get("salary_max") or 0
            rate_str = f"${salary_min:,}–${salary_max:,}/yr" if salary_min else "Not specified"
            out.append({
                "title": title,
                "platform": "RemoteOK",
                "company": j.get("company", ""),
                "rate": rate_str,
                "rate_value": round(salary_max / 2080) if salary_max else 0,  # rough hourly equiv
                "type": "remote",
                "posted": j.get("date", "")[:10],
                "skills": [t.lower() for t in tags],
                "description": strip_html(j.get("description", ""))[:400],
                "url": j.get("url", "https://remoteok.com"),
            })
            if len(out) >= 25:
                break
        return out
    except Exception as e:
        print(f"[job_matcher] RemoteOK fetch failed: {e}")
        return []


def fetch_arbeitnow(query):
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        jobs = r.json().get("data", [])
        out = []
        q = (query or "").lower()
        for j in jobs:
            title = j.get("title", "Untitled role")
            tags = j.get("tags", []) or []
            haystack = (title + " " + " ".join(tags)).lower()
            if q and q not in haystack and not any(w in haystack for w in q.split()):
                continue
            out.append({
                "title": title,
                "platform": "Arbeitnow",
                "company": j.get("company_name", ""),
                "rate": "Not specified",
                "rate_value": 0,
                "type": "remote" if j.get("remote") else "on-site",
                "posted": "",
                "skills": [t.lower() for t in tags],
                "description": strip_html(j.get("description", ""))[:400],
                "url": j.get("url", "https://arbeitnow.com"),
            })
            if len(out) >= 25:
                break
        return out
    except Exception as e:
        print(f"[job_matcher] Arbeitnow fetch failed: {e}")
        return []


SOURCES = {
    "remotive": fetch_remotive,
    "remoteok": fetch_remoteok,
    "arbeitnow": fetch_arbeitnow,
}


def strip_html(text):
    return re.sub("<[^<]+?>", " ", text or "").strip()


def search_jobs(query, platforms=None, min_rate=0, max_rate=100000, job_type="all"):
    """
    Pulls live results from every real source above, then applies the
    same filters the UI exposes (platform, rate, type).

    `platforms` here refers to which of our real sources to query
    (e.g. ["remotive", "remoteok"]) — see note in app.py about the
    difference between "source" (what we can legally query) and the
    old fake per-platform checkboxes ("Upwork", "Fiverr"...) which are
    now informational only (see README).
    """
    active_sources = platforms or list(SOURCES.keys())
    active_sources = [p.lower() for p in active_sources if p.lower() in SOURCES]
    if not active_sources:
        active_sources = list(SOURCES.keys())

    results = []
    for name in active_sources:
        results.extend(SOURCES[name](query))

    filtered = []
    for job in results:
        if job["rate_value"] and (job["rate_value"] < min_rate or job["rate_value"] > max_rate):
            continue
        if job_type != "all" and job_type.lower() not in job["type"].lower():
            continue
        filtered.append(job)

    return filtered


def extract_skills_from_text(text):
    text_lower = (text or "").lower()
    return [skill for skill in KNOWN_SKILLS if skill in text_lower]


def read_cv_file(file_storage):
    """
    Reads the actual bytes of an uploaded CV. Supports .txt natively,
    and .pdf / .docx if PyPDF2 / python-docx are installed (see
    requirements.txt — both are now included).
    """
    filename = (file_storage.filename or "").lower()
    raw = file_storage.read()

    if filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            print(f"[job_matcher] PDF parse failed, falling back to raw decode: {e}")

    if filename.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            print(f"[job_matcher] DOCX parse failed, falling back to raw decode: {e}")

    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def calculate_cv_match(file_storage):
    """Extracts skills from an uploaded CV. Real file reading (PDF/DOCX/TXT),
    not just a bare .decode() like before."""
    content = read_cv_file(file_storage)
    skills = extract_skills_from_text(content)
    base_score = min(95, 50 + len(skills) * 5) if skills else 0
    return {
        "success": True,
        "skills_detected": skills,
        "match_score": base_score,
        "skill_count": len(skills),
        "cv_text": content[:6000],  # kept for ML matching below, not returned to the client
    }


def rank_jobs_for_cv(cv_text, jobs, top_n=25):
    """
    Real ML matching: TF-IDF vectorizes the CV text against each job's
    title+description+skills, then ranks by cosine similarity. This is
    what the chatbot's own description of the product claims it does —
    in the old version that claim was false (it was plain substring
    matching); this makes it true.
    """
    if not jobs:
        return []
    if not cv_text or not cv_text.strip():
        for j in jobs:
            j["match"] = "—"
        return jobs

    corpus = [cv_text] + [
        f"{j['title']} {' '.join(j.get('skills', []))} {j.get('description','')}"
        for j in jobs
    ]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
        matrix = vectorizer.fit_transform(corpus)
        sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    except Exception as e:
        print(f"[job_matcher] TF-IDF matching failed: {e}")
        for j in jobs:
            j["match"] = "—"
        return jobs

    for j, score in zip(jobs, sims):
        j["match"] = f"{round(min(score * 220, 99))}%"  # scaled for a more readable spread
        j["_score"] = float(score)

    jobs.sort(key=lambda j: j.get("_score", 0), reverse=True)
    for j in jobs:
        j.pop("_score", None)
    return jobs[:top_n]


# ─────────────────────────────────────────────
# OPTIONAL: higher-volume sources with a free API key
# Add ADZUNA_APP_ID / ADZUNA_APP_KEY or JOOBLE_API_KEY to your .env,
# then uncomment the matching function and add it to SOURCES above.
# ─────────────────────────────────────────────
"""
import os

def fetch_adzuna(query):
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []
    r = requests.get(
        "https://api.adzuna.com/v1/api/jobs/us/search/1",
        params={"app_id": app_id, "app_key": app_key, "what": query, "results_per_page": 20},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for j in r.json().get("results", []):
        out.append({
            "title": j.get("title", ""),
            "platform": "Adzuna",
            "company": (j.get("company") or {}).get("display_name", ""),
            "rate": f"${j.get('salary_min',0):,.0f}-${j.get('salary_max',0):,.0f}/yr" if j.get("salary_min") else "Not specified",
            "rate_value": round((j.get("salary_max") or 0) / 2080),
            "type": (j.get("contract_time") or "not specified"),
            "posted": j.get("created", "")[:10],
            "skills": [],
            "description": strip_html(j.get("description", ""))[:400],
            "url": j.get("redirect_url", "#"),
        })
    return out
"""
