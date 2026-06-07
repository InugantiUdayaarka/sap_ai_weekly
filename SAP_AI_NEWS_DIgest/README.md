# SAP × AI Weekly Enterprise Brief

An AI agent that automatically generates a weekly article linking the latest
AI developments to real SAP business workflows — then posts it to Microsoft Teams.

---

## What It Does

```
search_latest_ai_news()        search_latest_sap_news()
         │                              │
         └──────────┬───────────────────┘
                    ▼
          Relevance Mapping Agent
          (4–5 high-quality AI↔SAP pairs
           across Finance, SCM, HCM,
           Procurement, GRC, MDG, CX, BTP)
                    │
                    ▼
          Article Generator (GPT-4o via SAP AI Core)
          Structured for: Architects · Developers
                          Functional Consultants · Leads
                    │
                    ▼
          post_to_teams() → Teams Adaptive Card
                    │
                    ▼
          sap_ai_brief_YYYY_WNN.txt  (local backup)
```

---

## Project Structure

```
sap_ai_weekly/
├── app.py                      ← Main entry point
├── .env.example                ← Copy to .env and fill in
├── requirements.txt
├── README.md
└── tools/
    ├── __init__.py
    ├── final_answer.py          ← smolagents FinalAnswerTool
    ├── search_tool.py           ← AI + SAP news search (DDG)
    ├── teams_poster.py          ← Teams Adaptive Card poster
    ├── aicore_connector.py      ← OAuth + BTP Destination + AI Core API
    └── aicore_model.py          ← smolagents-compatible GPT-4o model
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials (see options below)
```

### 3. Choose your connection mode

#### Option A — BTP Destination Service *(recommended for enterprise)*

Create a destination in BTP Cockpit:

| Property | Value |
|---|---|
| Name | `SAP_AI_CORE_GPT4O` |
| Type | HTTP |
| URL | Your AI Core API URL |
| Authentication | OAuth2ClientCredentials |
| Client ID | From AI Core service key |
| Client Secret | From AI Core service key |
| Token Service URL | `https://<auth-url>/oauth/token` |
| Additional Property: `AI-Resource-Group` | `default` (or your resource group) |
| Additional Property: `DeploymentID` | Your GPT-4o deployment ID |

Then set in `.env`:
```
BTP_DESTINATION_URL=https://destination-configuration.cfapps.<region>.hana.ondemand.com
BTP_DESTINATION_NAME=SAP_AI_CORE_GPT4O
BTP_UAACLIENTID=...
BTP_UAACLIENTSECRET=...
BTP_UAATOKENURL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token
```

#### Option B — Direct AI Core Credentials *(for local dev/testing)*

Leave `BTP_DESTINATION_URL` blank and set:
```
AICORE_AUTH_URL=...
AICORE_CLIENT_ID=...
AICORE_CLIENT_SECRET=...
AICORE_BASE_URL=...
AICORE_RESOURCE_GROUP=default
AICORE_DEPLOYMENT_ID=...
```

> **Where to find these:**
> BTP Cockpit → Instances → AI Core service instance → Service Keys → View

### 4. Find your GPT-4o Deployment ID

```
SAP AI Launchpad
  └── ML Operations
        └── Deployments
              └── Find your GPT-4o deployment → copy Deployment ID
```

### 5. Set up Teams Webhook

```
Teams Channel → ··· (More options) → Connectors
  → Incoming Webhook → Configure
  → Name: "SAP AI Weekly"
  → Copy webhook URL → paste into .env as TEAMS_WEBHOOK_URL
```

---

## Run

```bash
python app.py
```

Output:
- Printed to console
- Posted to your Teams channel
- Saved as `sap_ai_brief_YYYY_WNN.txt`

---

## Weekly Scheduling

### Linux / macOS (cron)
```bash
# Every Monday at 8:00 AM
0 8 * * 1 cd /path/to/sap_ai_weekly && python app.py >> logs/weekly.log 2>&1
```

### Windows Task Scheduler
```
Action: Start a program
Program: python
Arguments: C:\path\to\sap_ai_weekly\app.py
Trigger: Weekly, Monday, 08:00
```

### Azure Functions (Timer Trigger)
```python
# function.json
{
  "schedule": "0 0 8 * * 1"   # Every Monday 8AM UTC
}
```

---

## Domain Rotation

The agent automatically rotates its deep-dive focus every week:

| Week % 4 | Focus Domain |
|---|---|
| 0 | Finance & Controlling — FI/CO, Treasury, GRC, Audit |
| 1 | Supply Chain & Logistics — IBP, EWM, TM, MM, Ariba |
| 2 | Human Capital — SuccessFactors, Fieldglass |
| 3 | Platform & Data — BTP, Datasphere, MDG, SAC, CX |

---

## Article Structure (every issue)

```
🔔  Headline
⚡  This Week in 90 Seconds (4–5 bullets)
── Main Sections (4–5) ──
    🤖 The AI Development
    🏢 The SAP Connection
    🔄 Integration Flow (step-by-step)
    🔧 For Architects & BTP Developers
    💼 For Functional Consultants
    ⚡ Readiness Check (matrix)
🧭  Architect's Corner
🚨  Watch Out — Common Pitfalls
✅  This Week's Action Items (by role)
📌  Resources Worth Bookmarking
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `No AI/SAP news found` | DDG rate limit — agent falls back to internal knowledge. Normal. |
| `401 Unauthorized` from AI Core | Check AICORE_CLIENT_ID/SECRET or Destination OAuth config |
| `404` on deployment endpoint | Verify AICORE_DEPLOYMENT_ID in AI Launchpad → Deployments |
| Teams post `400` error | Check TEAMS_WEBHOOK_URL is the full webhook URL |
| Article too short (<500 chars) | Increase `max_steps` in CodeAgent or check model token limit |
| Token expired mid-run | Connector auto-refreshes — if persists, check token URL |
