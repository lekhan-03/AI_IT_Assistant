<div align="center">

# 🧠 Triage / Console

### AI-Powered Internal IT Support Triage Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vite.dev)
[![Gemini](https://img.shields.io/badge/Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Groq](https://img.shields.io/badge/Groq-API-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)

**Triage/console** is a production-grade, full-stack AI agent that accepts raw IT support tickets and instantly returns a structured triage: category, priority, what context is missing, a concrete next step, and the model's reasoning — all powered by a dual-AI consensus engine with an always-on rule-engine fallback.

[Live Demo](#) · [API Reference](#-api-reference) · [Deployment Guide](#-deployment)

</div>

---

## 📸 Overview

The system runs **two AI models simultaneously** (Google Gemini + Groq) and fuses their outputs into a single **consensus result** using Gemini as the synthesizer. If both models fail or are not configured, a deterministic **Rule Engine** takes over — meaning the app never goes down.

```
Employee Ticket (text)
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                    Triage Service                       │
│                                                         │
│   ┌──────────────┐    ┌──────────────┐                 │
│   │ Gemini Flash │    │   Groq OSS   │  ← Parallel     │
│   │  (analyze)   │    │  (analyze)   │    execution     │
│   └──────┬───────┘    └──────┬───────┘                 │
│          │                   │                          │
│          └────────┬──────────┘                         │
│                   ▼                                     │
│          ┌────────────────┐                            │
│          │ Gemini (synth) │  ← Consensus / fusion      │
│          └────────┬───────┘                            │
│                   │     on any failure                  │
│                   └────────► Rule Engine (fallback)     │
└───────────────────────────────────────────────────────┘
        │
        ▼
 Structured JSON Result
 {category, priority, missing_info,
  next_step, reasoning, confidence, kb_reference}
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Dual-AI Consensus** | Gemini + Groq run in parallel; outputs are synthesized into one master result |
| **Rule Engine Fallback** | Deterministic, keyword-weighted triage that works with zero API keys |
| **BM25 RAG** | In-memory knowledge base retrieval using industry-standard BM25 scoring |
| **Follow-up Flow** | Asks exactly one targeted question when the ticket is too vague to diagnose |
| **Priority Detection** | Weighs technical severity *and* business impact (deadline detection, multi-system signals) |
| **KB References** | Surfaces matching internal articles by ID (e.g. KB-001) with every result |
| **Token-Optimized** | Compressed prompts, top-k=1 RAG injection, history truncation — minimal API cost |
| **Modern React UI** | Glassmorphism dark-mode SPA with ambient animations and micro-interactions |

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Runtime |
| **Flask** | 3.0.3 | REST API + static file server |
| **Gunicorn** | 22.0.0 | Production WSGI server |
| **Google Gemini** | `gemini-2.0-flash` (free tier) | Primary AI engine + Synthesizer |
| **Groq** | `openai/gpt-oss-120b` (free tier) | Secondary AI engine |
| **Pydantic** | 2.x | Structured output validation |
| **BM25** | Custom (pure Python) | In-memory knowledge base search |
| **ThreadPoolExecutor** | stdlib | Concurrent multi-model execution |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **React** | 19 | UI framework |
| **Vite** | 8.3 | Build tool + dev server |
| **lucide-react** | 1.47 | Icon library |
| **Vanilla CSS** | — | Glassmorphism design system |

---

## 📁 Project Structure

```
it-triage-assistant/
│
├── backend/
│   ├── app.py               # Flask app — 2 API endpoints + static server
│   ├── engine.py            # Core triage logic:
│   │                        #   RuleEngine, GeminiEngine, GroqEngine,
│   │                        #   TriageService (orchestrator + synthesizer)
│   ├── rag.py               # BM25 retrieval engine over knowledge_base.json
│   ├── knowledge_base.json  # Internal IT KB articles (KB-001 … KB-004)
│   ├── demo_cli.py          # CLI runner — no server needed
│   └── requirements.txt
│
├── ui/
│   ├── src/
│   │   ├── App.jsx          # Main SPA — state, API calls, result rendering
│   │   └── index.css        # Global design system (dark mode, glassmorphism)
│   ├── dist/                # Production build (served by Flask)
│   ├── vite.config.js       # Proxy /api → localhost:5000 in dev mode
│   └── package.json
│
├── .env                     # API keys (never commit this!)
├── .env.example             # Template for environment variables
├── .gitignore
├── Procfile                 # Render / Heroku start command
└── README.md
```

---

## ⚡ Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/it-triage-assistant.git
cd it-triage-assistant
```

### 2. Set up the backend

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
# From the project root:
cp .env.example .env
```

Edit `.env` and add your free-tier API keys:

```env
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
PORT=5000
```

> **No keys? No problem.** The app works fully offline with the built-in Rule Engine. The status indicator in the UI will show `engine: rules-only` instead of `engine: panel of experts`.

### 4. Build the frontend

```bash
cd ../ui
npm install
npm run build
cd ..
```

### 5. Run the server

```bash
python backend/app.py
```

Open **http://localhost:5000** in your browser. That's it! ✅

---

## 🧑‍💻 Development Mode (Hot Reload)

To actively work on the React frontend with instant hot-reload:

**Terminal 1 — Backend**
```bash
python backend/app.py
```

**Terminal 2 — Frontend dev server**
```bash
cd ui
npm run dev
```

Open **http://localhost:5173** — the Vite dev server automatically proxies all `/api` calls to Flask on port 5000.

---

## 🔌 API Reference

### `GET /api/status`

Returns the currently active engine mode.

**Response**
```json
{
  "mode": "panel of experts (gemini, groq)"
}
```

---

### `POST /api/triage`

Analyzes a support ticket and returns a structured triage result.

**Request Body**
```json
{
  "ticket_text": "My Outlook keeps asking for my password after I changed it.",
  "history": []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `ticket_text` | `string` | ✅ | The raw support ticket text |
| `history` | `array` | ❌ | Prior follow-up Q&A pairs: `[{"question": "...", "answer": "..."}]` |

**Response**
```json
{
  "results": [
    {
      "category": "Account",
      "priority": "High",
      "missing_info": [],
      "next_step": "Do NOT reset the password. Open Windows Credential Manager...",
      "reasoning": "Classic stale-credential signature after a password change.",
      "needs_followup": false,
      "follow_up_question": null,
      "confidence": "high",
      "engine": "llm (gemini)",
      "kb_reference": "KB-002"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `category` | `string` | `Network`, `Account`, `Application`, `Device`, or `Other` |
| `priority` | `string` | `Low`, `Medium`, `High`, or `Critical` |
| `missing_info` | `string[]` | List of facts that would improve confidence |
| `next_step` | `string` | Concrete action for the support engineer |
| `reasoning` | `string` | Evidence-based explanation of the diagnosis |
| `needs_followup` | `bool` | `true` if ticket is too vague for a diagnosis |
| `follow_up_question` | `string\|null` | The one targeted question to ask the employee |
| `confidence` | `string` | `low`, `medium`, or `high` |
| `engine` | `string` | Which engine produced this result |
| `kb_reference` | `string\|null` | Matching KB article ID, e.g. `"KB-002"` |

---

## 🌐 Deployment

### Render.com (Recommended — Free Tier)

1. Push your repo to GitHub (ensure `.env` is in `.gitignore`)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `gunicorn --bind 0.0.0.0:$PORT backend.app:app`
5. Add Environment Variables: `GEMINI_API_KEY`, `GROQ_API_KEY`
6. Click **Deploy** — your live URL will be `https://your-app.onrender.com` ✅

### Railway.app

1. New Project → Deploy from GitHub
2. Add env vars: `GEMINI_API_KEY`, `GROQ_API_KEY`
3. Railway auto-detects Python — done.

### Docker / Self-hosted

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r backend/requirements.txt
EXPOSE 5000
ENV PORT=5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "backend.app:app"]
```

```bash
docker build -t triage-console .
docker run -p 5000:5000 --env-file .env triage-console
```

---

## 🧪 Running Tests

A comprehensive load & stress test suite is included:

```bash
# Make sure the server is running first, then:
python tests/load_test.py
```

**Covers:**
- ✅ BM25 RAG unit tests (relevance, empty query, gibberish)
- ✅ Rule Engine unit tests (all 6 ticket types, priority, follow-up)
- ✅ API endpoint tests (status, frontend, triage, malformed inputs)
- ✅ Concurrency load test (15 requests × 5 concurrent workers)
- ✅ Edge cases (emoji, non-English, SQL injection, bad schema)

**Load test results (baseline):**
- Avg response: ~5.5s | Max: ~14s | Min: ~3s
- 0 server errors under full concurrent load
- 93–100% pass rate

---

## 🧠 Design Decisions

**Why a Rule Engine alongside AI?**
A triage tool that occasionally halluccinates a diagnosis is worse than useless to a support team. The Rule Engine is the trustworthy, fully-explainable backbone. The AI layer adds nuance — better-phrased reasoning, edge-case handling — without replacing the underlying policy.

**Why ask a question instead of guessing?**
Both the Rule Engine and AI follow the same policy: *only recommend a concrete next step when there's enough information; otherwise ask exactly one well-targeted question.* This mirrors how a real L1 engineer handles a two-word ticket.

**Why BM25 over a Vector Database?**
BM25 is the industry standard for keyword search (used by Elasticsearch under the hood). For an internal KB with tens to hundreds of articles, in-memory BM25 is faster, completely free, and requires zero infrastructure. A Vector DB is only warranted at the thousands-of-documents scale.

**Why token-optimize the prompts?**
Free-tier APIs have rate limits measured in tokens-per-minute. The system is deliberately engineered to use the minimum viable context: compressed system prompt, top-1 RAG injection, last-2-history truncation, and minified synthesizer payloads. This means faster responses and higher throughput within free limits.

---

## 🗺️ Knowledge Base

The internal KB is stored in `backend/knowledge_base.json` and searched using BM25 on every request. Add new articles by appending objects with this schema:

```json
{
  "id": "KB-005",
  "title": "Short, descriptive title",
  "content": "Symptom: ... Cause: ... Fix: ...",
  "tags": ["keyword1", "keyword2"]
}
```

No restart needed — the KB is loaded fresh on server start.

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Optional | Google AI Studio free-tier key |
| `GROQ_API_KEY` | Optional | Groq Cloud free-tier key |
| `PORT` | Optional | Server port (default: `5000`) |

---

## 📜 License

MIT — free to use, modify, and distribute.

---

<div align="center">

Built with ❤️ by the team · Powered by Google Gemini + Groq + React

</div>
