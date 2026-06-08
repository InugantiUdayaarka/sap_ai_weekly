"""
SAP AI Weekly Enterprise Brief — app.py
========================================
Generates a weekly AI × SAP article and posts it to Microsoft Teams.

Connection modes (auto-detected from .env):
  1. BTP Destination Service  → set BTP_DESTINATION_URL + BTP_* vars
  2. Direct AI Core credentials → set AICORE_* vars

Run:
  python app.py

Schedule (cron example — every Monday 8AM):
  0 8 * * 1 /usr/bin/python3 /path/to/sap_ai_weekly/app.py
"""

import os
import datetime
from dotenv import load_dotenv
from smolagents import CodeAgent
from tools.final_answer import FinalAnswerTool
from tools.search_tool import search_latest_ai_news, search_latest_sap_news
from tools.teams_poster import post_to_teams
from tools.aicore_model import AICoreGPT4oModel

load_dotenv()

# ──────────────────────────────────────────────────────────────
# DOMAIN ROTATION WHEEL
# Ensures every SAP domain gets deep-dive coverage across 4 weeks.
# Auto-selects based on ISO week number.
# ──────────────────────────────────────────────────────────────
ROTATION_WHEEL = [
    "Deep-dive focus this week: Finance & Controlling — "
    "S/4HANA FI/CO, Treasury, Financial Close, GRC, Internal Audit, FSCM",

    "Deep-dive focus this week: Supply Chain & Logistics — "
    "SAP IBP, EWM, TM, MM, PP/DS, Ariba Procurement, SRM, Supplier Collaboration",

    "Deep-dive focus this week: Human Capital Management — "
    "SuccessFactors EC, RCM, LMS, Succession, Compensation, "
    "People Analytics, Fieldglass, Time & Attendance",

    "Deep-dive focus this week: Platform, Data & Analytics — "
    "SAP BTP AI Core, Datasphere, MDG, SAC, Build Code, "
    "Integration Suite, ABAP Environment, SAP CX/C4C",
]

week_number   = datetime.date.today().isocalendar()[1] % 4
current_focus = ROTATION_WHEEL[week_number]
today_str     = datetime.date.today().strftime("%B %d, %Y")
iso_week      = datetime.date.today().isocalendar()[1]

print("\n" + "=" * 70)
print(f"  SAP AI Weekly Brief Generator")
print(f"  Date: {today_str}  |  Week: {iso_week}")
print(f"  Focus: {current_focus}")
print("=" * 70 + "\n")

# ──────────────────────────────────────────────────────────────
# TOOLS & MODEL
# ──────────────────────────────────────────────────────────────
final_answer = FinalAnswerTool()

model = AICoreGPT4oModel(
    max_tokens=7000,
    temperature=0.65
)

agent = CodeAgent(
    model=model,
    tools=[final_answer, search_latest_ai_news, search_latest_sap_news, post_to_teams],
    max_steps=16,
    verbosity_level=2,
)

# ──────────────────────────────────────────────────────────────
# MASTER PROMPT
# ──────────────────────────────────────────────────────────────
WEEKLY_ARTICLE_PROMPT = f"""
You are a principal SAP enterprise architect with 20+ years across the full SAP landscape.
Today is {today_str}. You are writing Issue #{iso_week} of the SAP × AI Weekly Brief.

YOUR AUDIENCE:
  • Senior SAP Architects (S/4HANA, BTP, Datasphere, Integration)
  • SAP Module Leads (FI/CO, MM/SD, PP, HCM, GRC, SCM)
  • BTP & AI Core Developers
  • SAP Functional Consultants
  • SAP CoE Leads and Transformation Program Managers
These people are NOT beginners. They know SAP deeply.
Your job: give them something they didn't already know,
and show them exactly how to apply it in their SAP landscape TODAY.

THIS WEEK'S DOMAIN FOCUS:
{current_focus}
Ensure at least 2 of your 4–5 mapped sections directly relate to this focus.
Remaining sections can span any other SAP domains for breadth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: SEARCH FALLBACK RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If search tools return empty results or errors, DO NOT STOP.
Use your own deep knowledge of the SAP AI landscape to write
a fully grounded, specific, and actionable article.
The article MUST be written regardless of search outcomes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — FETCH AI NEWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call search_latest_ai_news.
Extract top 6 AI developments. For each:
  - Exact capability: agentic, RAG, multimodal, fine-tuning,
    forecasting, NLP classification, computer vision, etc.
  - Model or framework: GPT-4o, Gemini, Mistral, Claude,
    LangGraph, AutoGen, LlamaIndex, Hugging Face, etc.
  - Technical mechanism
  - Enterprise function impacted:
    Finance / Supply Chain / HR / Procurement / Risk / Data / CX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — FETCH SAP NEWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call search_latest_sap_news.
Extract top 6 SAP developments. Cover the FULL application estate:
S/4HANA, SuccessFactors, Ariba, IBP, EWM/TM, GRC, MDG, CX, SAC, BTP.
Do NOT focus only on BTP or Datasphere.

For each:
  - Exact SAP product + module + sub-process
  - User persona impacted (architect, consultant, end user, manager)
  - Current AI readiness: embedded / API-ready / manual today

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — ENTERPRISE-WIDE RELEVANCE MAPPING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Map AI capabilities to SAP applications. Select 4–5 pairs spanning
at least 4 different SAP domains. For each pair validate:
  1. Technical feasibility in that SAP app today
  2. Integration path (Joule / AI Core / BTP extension / ABAP / OData / API)
  3. SAP data objects feeding the AI (BAPI, OData service, CDS view, API)
  4. Before/after process change for the end user
  5. Measurable enterprise ROI (time saved, error rate, cycle time, risk)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — WRITE THE ARTICLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VOICE & TONE:
  - Peer-to-peer. You are one of them.
  - Sharp and opinionated where warranted.
  - Technically precise — use real object names, t-codes, API names,
    service names, BTP service plans, module names.
  - Pair technical depth with plain-language business translation.
  - A touch of dry wit is welcome.
  - Zero filler. Every sentence earns its place.
  - No SAP marketing language. No generic AI hype.

USE THIS EXACT STRUCTURE:

══════════════════════════════════════════════════
🔔 HEADLINE
══════════════════════════════════════════════════
Specific, outcome-focused, slightly provocative.
Must reference a real SAP domain + a real AI capability.
Make it sharp enough that someone forwards it immediately.

══════════════════════════════════════════════════
⚡ THIS WEEK IN 90 SECONDS
══════════════════════════════════════════════════
4–5 punchy bullets. One per mapped pair.
Each = the "so what" in one precise sentence.
Covers the full domain spread of this week's article.

══════════════════════════════════════════════════
MAIN SECTIONS — 4 to 5, one per AI↔SAP pair
══════════════════════════════════════════════════

## [Outcome-Focused Title — SAP domain + AI benefit]

**🤖 The AI Development:**
2–3 sentences. What changed. Name the model/framework.
What is genuinely new vs. incremental.

**🏢 The SAP Connection:**
2–3 sentences. Exact SAP app, module, sub-process.
Integration touch point: Joule, AI Core, OData service name,
BAPI, iFlow, ABAP class, Datasphere view, SuccessFactors API.

**🔄 How It Works — Integration Flow:**
5–7 numbered steps. Concrete whiteboard-level detail.
Use real SAP objects: t-codes, OData service names, BTP service plans,
Datasphere artifact types, SuccessFactors MDF APIs, CDS view names.

**🔧 For SAP Architects & Technical Consultants:**
2–3 specific implementation notes.
BTP services needed, ABAP extensions, AI Core model deployment,
Integration Suite adapters. Realistic effort: days / weeks / sprint.

**💼 For Functional Consultants & Business Process Owners:**
Pure business terms.
What manual step disappears? Which KPI improves?
What does the Fiori tile or SAP screen look like differently?

**⚡ Readiness Check:**
  - SAP Native Support:   [Embedded / Needs BTP Extension / Custom Build]
  - Implementation Effort: [Low / Medium / High]
  - Business Impact:       [High / Medium / Low]
  - Go-Live Horizon:       [Now / H2 2025 / 2026 Roadmap]

══════════════════════════════════════════════════
🧭 ARCHITECT'S CORNER
══════════════════════════════════════════════════
4–6 lines for the most senior architects.
One non-obvious integration pattern, governance risk,
or capability combination to design for now.
Something they can take into their next architecture review.

══════════════════════════════════════════════════
🚨 WATCH OUT — COMMON PITFALLS
══════════════════════════════════════════════════
2–3 frank warnings. Things teams get wrong rushing AI into SAP.
Use real SAP object names and real failure scenarios.
Example tone: "Don't feed raw ACDOCA postings into an LLM without
semantic mapping — the model has no idea what cost element 400000 means."

══════════════════════════════════════════════════
✅ THIS WEEK'S ACTION ITEMS
══════════════════════════════════════════════════
One specific action per role. Name the exact tool, t-code,
BTP service, Discovery Center mission, or Fiori app.

  🔧 Architects & BTP Developers:          [specific task]
  📊 Datasphere & Analytics Specialists:   [specific task]
  📋 Functional Consultants:               [specific task with menu path]
  🏢 Transformation & Program Leads:       [specific task]

══════════════════════════════════════════════════
📌 RESOURCES WORTH BOOKMARKING
══════════════════════════════════════════════════
4–5 real resources. Mix of:
  - SAP Help Portal (specific page URLs)
  - SAP Discovery Center missions
  - SAP Community blog posts
  - SAP AI Core / BTP cockpit paths
  - GitHub SAP-samples repos

Target: 1100–1400 words. Sharp. Specific. Actionable.
Write the article your most respected SAP colleague
would forward to their entire team on Monday morning.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — POST TO TEAMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call post_to_teams with:
  - article = the full article text
  - title   = the exact headline from the article

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — FINAL ANSWER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return the complete article as a clean string using final_answer.
"""

# ──────────────────────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────────────────────
print("🚀 Starting article generation...\n")

result  = agent.run(WEEKLY_ARTICLE_PROMPT)
article = str(result) if result else ""

# Validate output
if not article or len(article) < 500:
    print("\n⚠️  Output too short or empty. Check verbosity logs above.")
else:
    print(f"\n✅ Article generated — {len(article):,} characters\n")
    print("=" * 70)
    print("📰  SAP × AI WEEKLY ENTERPRISE BRIEF")
    print("=" * 70)
    print(article)

    # Save with timestamped filename so weekly runs don't overwrite
    timestamp = datetime.date.today().strftime("%Y_W%W")
    filename  = f"sap_ai_brief_{timestamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(article)

    print(f"\n✅ Saved to {filename}")
