"""
JOBSK CHATBOT (v3)

WORTH KNOWING: the "AI Agent Chat" in this app has always been a
rule-based keyword matcher, not a real language model — fast, free, and
works offline, but if you're going to market this as an "AI/ML agent"
(e.g. to sell it), that's worth being upfront about, or worth upgrading.

This version keeps the free rule-based replies as the default (so the
app still works with zero setup / zero cost), and adds a genuinely real
option: if you set ANTHROPIC_API_KEY in .env, it calls the real Claude
API instead, so the chatbot gives real, dynamic answers instead of
canned text.

    pip install anthropic   (already in requirements.txt)
    backend/.env:  ANTHROPIC_API_KEY=sk-ant-...

Note this has a real per-message cost once you add a key — small, but
not zero, so it's opt-in.
"""

import os

RESPONSES = {
    "upwork": """To win on Upwork:

1. Complete your profile 100% — photo, bio, skills, portfolio
2. Start with smaller jobs ($50-200) to build your first reviews
3. Write personalized proposals — never copy-paste templates
4. Reference something specific from each job post
5. Respond to messages within 1 hour

Tip: After 5 reviews you can raise your rate significantly.""",

    "fiverr": """To succeed on Fiverr:

1. Create 3-5 gigs in your niche, not just one
2. Use strong keyword-rich titles
3. Start pricing lower ($5-15) to get initial orders and reviews
4. Check Buyer Requests daily — clients post what they need there
5. Deliver before the deadline every time

Tip: After 10 reviews, raise your prices by 20-30%.""",

    "linkedin": """To get hired on LinkedIn:

1. Use a professional headshot — profiles with photos get 21x more views
2. Write a headline with your top 3 skills
3. Turn on "Open to Work" — recruiters filter by this
4. Connect with 50+ people in your industry
5. Post once a week to stay visible

Tip: Message recruiters directly with a short, polite note.""",

    "cv": """A great CV:

1. Keep it to 1-2 pages maximum
2. Put a clear skills section at the top
3. For each job: what you did + the result with numbers
4. Add links to GitHub, portfolio, or LinkedIn
5. Save as PDF — never send Word
6. Match keywords from the job description exactly

Tip: Tailor your CV for each application — it doubles your response rate.""",

    "proposal": """Writing winning proposals:

1. First line: reference something specific from the job post
2. Explain exactly how you will solve their problem
3. Mention one relevant past project briefly
4. End with a smart question about their project

Tip: Never start with "Dear Sir" or "I am writing to apply".""",

    "rate": """Typical freelance rates by skill:

- Python / ML / AI: $40-80/hr
- Web Development: $25-60/hr
- Mobile App Dev: $35-75/hr
- Graphic Design: $20-50/hr
- Content Writing: $15-40/hr
- Video Editing: $20-45/hr

Tip: Start lower, build reviews, then raise your rate every 3 months.""",

    "default": """I can help with:
- Finding jobs across all platforms
- Fiverr and Upwork tips
- Writing your CV
- Crafting proposals
- Setting your freelance rate

What would you like to know more about?"""
}


def _rule_based_response(message):
    msg = message.lower()
    if any(word in msg for word in ["upwork", "contract", "bid on"]):
        return RESPONSES["upwork"]
    if any(word in msg for word in ["fiverr", "gig", "buyer request"]):
        return RESPONSES["fiverr"]
    if any(word in msg for word in ["linkedin", "recruiter", "profile"]):
        return RESPONSES["linkedin"]
    if any(word in msg for word in ["cv", "resume"]):
        return RESPONSES["cv"]
    if any(word in msg for word in ["proposal", "cover letter"]):
        return RESPONSES["proposal"]
    if any(word in msg for word in ["rate", "charge", "salary", "pay", "earn"]):
        return RESPONSES["rate"]
    return RESPONSES["default"]


def _claude_response(message):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=("You are the Jobsk AI agent, a helpful assistant for freelancers. "
                "Give practical, specific advice about finding freelance jobs, "
                "writing CVs and proposals, and succeeding on freelance platforms. "
                "Keep answers concise and actionable."),
        messages=[{"role": "user", "content": message}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def get_chatbot_response(message):
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            return _claude_response(message)
        except Exception as e:
            print(f"[chatbot] Claude API call failed, falling back to rule-based: {e}")
    return _rule_based_response(message)
