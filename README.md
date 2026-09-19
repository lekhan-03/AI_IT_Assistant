<div align="center">

# 🧠 Triage Console
### AI-Powered IT Support Triage Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Gemini](https://img.shields.io/badge/Gemini-API-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Groq](https://img.shields.io/badge/Groq-API-F55036?style=flat-square&logo=groq&logoColor=white)](https://groq.com)

Turns a short, often incomplete IT support ticket into a structured triage — category, priority, what's missing, a concrete next step, and the reasoning behind it. Asks a clarifying question instead of guessing when there isn't enough information to diagnose safely.

**[Live Demo](https://ai-it-assistant-by9y.onrender.com/)** &nbsp;·&nbsp; **[API Reference](#api-reference)** &nbsp;·&nbsp; **[Design Decisions](#design-decisions)**

</div>

---

## Overview

Gemini and Groq analyze each ticket in parallel, and Gemini synthesizes both outputs into one consensus result. If either model fails, isn't configured, or the API is unreachable, a deterministic **rule engine** takes over automatically — so the app always responds, with zero required configuration.

```
Employee Ticket
      │
      ▼
┌─────────────────────────────────────────────┐
│ Gemini (analyze)      Groq (analyze)        │  parallel
│         └───────────┬───────────┘           │
│                     ▼                       │
│            Gemini (synthesizer)             │  consensus
│                     │  on failure           │
│                     └─────────► Rule Engine │  fallback
└─────────────────────────────────────────────┘
      │
      ▼
{ category, priority, missing_info,
  next_step, reasoning, confidence, kb_reference }
```

**Core policy, enforced at every layer:** recommend a concrete next step only when there's enough information — otherwise ask exactly one targeted follow-up question.

---

## Features

| | |
|---|---|
| **Dual-AI consensus** | Gemini + Groq run in parallel; outputs are fused into one result |
| **Rule engine fallback** | Deterministic, keyword-weighted, fully explainable — works with zero API keys |
| **Ask, don't guess** | Asks one targeted follow-up question when a ticket is too vague to diagnose |
| **Impact-aware priority** | Weighs technical severity *and* business urgency (deadlines, multi-system scope) |
| **KB-backed reasoning** | BM25 search over an internal knowledge base; results cite a matching article |
| **Token-optimized** | Compressed prompts and truncated history keep it fast and within free-tier limits |

---

## Tech Stack

| Layer | Stack |
|---|---|
| **Backend** | Python 3.11+ · Flask · Gunicorn · Gemini (`gemini-2.0-flash`) · Groq (`gpt-oss-120b`) · Pydantic · custom BM25 |
| **Frontend** | React 19 · Vite · lucide-react · vanilla CSS |

---

## Project Structure

```
AI_IT_Assistant/
├── backend/
│   ├── app.py               # Flask app — API endpoints + static server
│   ├── engine.py              # RuleEngine, GeminiEngine, GroqEngine, TriageService
│   ├── rag.py                  # BM25 retrieval over knowledge_base.json
│   ├── knowledge_base.json     # Internal KB articles (KB-001 … KB-004)
│   ├── demo_cli.py             # Runs sample tickets with no server needed
│   └── requirements.txt
├── ui/
│   ├── src/                    # App.jsx, index.css
│   └── dist/                   # Production build, served by Flask
├── .env.example
├── Procfile                    # Render start command
└── README.md
```

---

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+, npm

```bash
git clone https://github.com/lekhan-03/AI_IT_Assistant.git
cd AI_IT_Assistant

# 1. Backend
cd backend && pip install -r requirements.txt

# 2. API keys (optional)
cp ../.env.example ../.env
# edit .env → GEMINI_API_KEY, GROQ_API_KEY

# 3. Frontend
cd ../ui && npm install && npm run build && cd ..

# 4. Run
python backend/app.py
```
Open **http://localhost:5000**.

> **No API keys? No problem.** The app runs fully on the built-in rule engine — the UI shows `engine: rules-only`. Adding `GEMINI_API_KEY` / `GROQ_API_KEY` switches it to `engine: panel of experts`.

**CLI demo (no server needed):**
```bash
python backend/demo_cli.py
```

**Frontend hot-reload for development:**
```bash
# Terminal 1
python backend/app.py
# Terminal 2
cd ui && npm run dev   # → http://localhost:5173, proxies /api to Flask
```

---

## API Reference

**`POST /api/triage`**

```json
// request
{
  "ticket_text": "Outlook keeps asking for my password since I changed it.",
  "history": []
}

// response
{
  "category": "Account",
  "priority": "High",
  "missing_info": [],
  "next_step": "Update the stored credential in Windows Credential Manager instead of resetting the password again.",
  "reasoning": "Classic stale-credential signature after a password change.",
  "needs_followup": false,
  "confidence": "high",
  "engine": "llm (gemini)",
  "kb_reference": "KB-002"
}
```

| Field | Description |
|---|---|
| `category` | `Network`, `Account`, `Application`, `Device`, or `Other` |
| `priority` | `Low`, `Medium`, `High`, or `Critical` |
| `missing_info` | Facts that would improve diagnostic confidence |
| `needs_followup` / `follow_up_question` | Set when the ticket is too vague to diagnose |
| `confidence` | `low`, `medium`, or `high` |
| `kb_reference` | Matching internal KB article ID, if any |

**`GET /api/status`** → returns the active engine mode.

---

## Design Decisions

**Rule engine alongside the AI models.** A triage tool that occasionally hallucinates a diagnosis from two lines of text is worse than useless to a support team. The rule engine is the explainable backbone — every output traces back to a specific signal in the ticket. The AI layer adds nuance without replacing that underlying policy.

**Ask a question instead of guessing.** Both layers follow the same rule: only recommend a concrete step when there's enough information, otherwise ask one well-targeted question — the way a real L1 engineer works a two-word ticket.

**BM25 over a vector database.** The standard choice for keyword search at this scale (it's what Elasticsearch uses under the hood). For a KB of tens to a few hundred articles, in-memory BM25 is faster, free, and needs no extra infrastructure.

**Token-optimized prompts.** Free-tier APIs are rate-limited by tokens per minute, so the system uses the minimum viable context — compressed prompts, top-1 RAG injection, truncated history — to stay fast and within free-tier limits.

---

## Testing

```bash
python tests/load_test.py
```
Covers BM25 retrieval, rule-engine classification across ticket types, API endpoint behavior including malformed input, and a concurrency load test. Baseline: ~5.5s average response, 0 server errors under load.

---

## Deployment

| Platform | Steps |
|---|---|
| **Render** (free tier) | Connect repo → build `pip install -r backend/requirements.txt` → start `gunicorn --bind 0.0.0.0:$PORT backend.app:app` → set `GEMINI_API_KEY`, `GROQ_API_KEY` |
| **Docker** | `docker build -t triage-console .` → `docker run -p 5000:5000 --env-file .env triage-console` |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Optional | Google AI Studio free-tier key |
| `GROQ_API_KEY` | Optional | Groq Cloud free-tier key |
| `PORT` | Optional | Server port (default `5000`) |

---

<div align="center">

MIT License · Built by Lekhan

</div>
