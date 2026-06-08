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
    ├── aicore_connector.py      ← OAuth + VCAP + Destination + AI Core API call
    └── aicore_model.py          ← smolagents-compatible GPT-4o model wrapper
```

---

## Credential Resolution — How It Works

**No secrets are ever hardcoded.** Every credential is resolved in this order:

```
1. Explicit env var in .env           ← always wins
         ↓  (only if still None)
2. VCAP_SERVICES (BTP Cloud Foundry)  ← auto-injected when service is bound
         ↓  (only if still None)
3. RuntimeError — with a clear message listing exactly what is missing
```

On BTP Cloud Foundry, bind your services and restage — no .env needed at all:
```bash
cf bind-service <your-app> <aicore-instance>
cf bind-service <your-app> <destination-instance>   # if using Destination mode
cf restage <your-app>
```

---

## Connection Modes

Two modes, auto-detected. **All 4 vars** of a mode must be present to activate it.
Direct mode is checked first; Destination mode is the fallback.

### Mode A — DIRECT  *(local dev / testing)*
Calls AI Core directly using an AI Core service key.

| Env Var | Where to find it |
|---|---|
| `AICORE_API_URL` | Service key → `serviceurls.AI_API_URL` |
| `AICORE_AUTH_URL` | Service key → `url` + `/oauth/token` |
| `AICORE_CLIENT_ID` | Service key → `clientid` |
| `AICORE_SECRET` | Service key → `clientsecret` |

### Mode B — DESTINATION  *(recommended for BTP production)*
Routes through BTP Destination Service — credentials never leave BTP.

| Env Var | Where to find it |
|---|---|
| `DEST_SERVICE_URL` | Destination service key → `uri` |
| `DEST_AUTH_URL` | Destination service key → `tokenurl` |
| `DEST_CLIENT_ID` | Destination service key → `clientid` |
| `DEST_SECRET` | Destination service key → `clientsecret` |

**Also create a BTP Destination:**
```
Name           : SAP_AI_CORE_GPT4O   (or set DESTINATION_NAME in .env)
Type           : HTTP
URL            : your AI Core API URL
Authentication : OAuth2ClientCredentials
Client ID/Secret + Token URL : from AI Core service key
Additional properties:
  AI-Resource-Group : default
  DeploymentID      : your GPT-4o deployment ID
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
# Edit .env — fill in one of Mode A or Mode B above,
# plus AICORE_DEPLOYMENT_ID, AICORE_RESOURCE_GROUP, AICORE_API_VERSION
```

### 3. Find your GPT-4o Deployment ID
```
SAP AI Launchpad → ML Operations → Deployments
  → find your GPT-4o deployment → copy the Deployment ID
```

### 4. Set up Teams Webhook
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
- Posted to your Teams channel as an Adaptive Card
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
Action:    Start a program
Program:   python
Arguments: C:\path\to\sap_ai_weekly\app.py
Trigger:   Weekly, Monday, 08:00
```

### Azure Functions (Timer Trigger)
```json
{ "schedule": "0 0 8 * * 1" }
```

---

## Domain Rotation

The agent auto-rotates its deep-dive domain focus every week by ISO week number:

| Week % 4 | Domain Focus |
|---|---|
| 0 | Finance & Controlling — FI/CO, Treasury, GRC, Audit |
| 1 | Supply Chain & Logistics — IBP, EWM, TM, MM, Ariba |
| 2 | Human Capital — SuccessFactors all modules, Fieldglass |
| 3 | Platform & Data — BTP, AI Core, Datasphere, MDG, SAC, CX |

---

## Article Structure (every issue)

```
🔔  Headline
⚡  This Week in 90 Seconds (4–5 bullets)
── Main Sections (4–5) ──
    🤖 The AI Development
    🏢 The SAP Connection
    🔄 Integration Flow (numbered steps with real SAP object names)
    🔧 For Architects & BTP Developers
    💼 For Functional Consultants
    ⚡ Readiness Check (Native / Complexity / Impact / Horizon)
🧭  Architect's Corner
🚨  Watch Out — Common Pitfalls
✅  This Week's Action Items (one per role)
📌  Resources Worth Bookmarking
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AI Core not configured` error | Check all 4 vars of one mode are set, or VCAP_SERVICES is bound |
| `401 Unauthorized` from AI Core | Token URL or client credentials wrong — recheck service key |
| `404` on deployment endpoint | Wrong `AICORE_DEPLOYMENT_ID` — verify in AI Launchpad → Deployments |
| Destination returns no `authTokens` | Destination auth type must be `OAuth2ClientCredentials` |
| Teams post `400` error | `TEAMS_WEBHOOK_URL` must be the full webhook URL |
| Article too short (<500 chars) | Raise `max_steps` in CodeAgent or check token limits |
| `No AI/SAP news found` | DDG rate limit — agent falls back to internal SAP knowledge. Normal. |
