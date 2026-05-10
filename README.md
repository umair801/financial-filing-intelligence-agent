# Financial Filing Intelligence Agent

> Powered by [Datawebify](https://datawebify.com) | Live API: [filings.datawebify.com/docs](https://filings.datawebify.com/docs)

A production-grade multi-agent system for SEC EDGAR financial filing intelligence. Built with LangGraph, GPT-4o, FastAPI, and PostgreSQL. Designed for financial research automation, hedge fund AI tooling, and investment analysis workflows.

---

## What It Does

- **Ingests** SEC EDGAR filings (8-K, 10-K, 10-Q, 6-K) on a configurable cadence via the EDGAR full-text search API
- **Extracts** structured financial signals via GPT-4o: capital structure changes, contract awards, capex guidance, going-concern flags, and undisclosed counterparties
- **Detects anomalies** across a sector basket: counterparties named in one filing appearing undisclosed in another, going-concern flags across peers
- **Alerts** analysts via Slack with a human-in-the-loop review gate (approve or dismiss each alert)
- **Exports** a refreshed DCF scaffold Excel file per company per filing cycle using openpyxl

---

## Architecture

```
SEC EDGAR Full-Text Search API
            │
            ▼
┌───────────────────┐
│  Ingestion Agent  │   Pipeline 1: Poll EDGAR, parse filings, store to PostgreSQL
└─────────┬─────────┘
          │
          ▼
┌────────────────────┐
│  Extraction Agent  │   Pipeline 2: GPT-4o structured extraction with Pydantic schemas
└─────────┬──────────┘
          │
          ▼
┌────────────────────────┐
│  Comparison Agent      │   Pipeline 3: Cross-entity anomaly detection across sector basket
└─────────┬──────────────┘
          │
          ▼
┌────────────────┐
│  Alert Agent   │   Pipeline 4: Slack webhook + human-in-the-loop review gate
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│  Excel Agent   │   Pipeline 5: openpyxl DCF scaffold builder, timestamped per filing cycle
└────────────────┘

All five pipelines orchestrated by a LangGraph stateful multi-agent graph
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangGraph 0.2.28 |
| AI Model | GPT-4o (OpenAI API) |
| Backend API | FastAPI + Uvicorn |
| Data Extraction | Pydantic structured output schemas |
| Database | PostgreSQL (Supabase) |
| Excel Automation | openpyxl |
| Alerts | Slack API (webhook + interactive messages) |
| Filing Source | SEC EDGAR full-text search API |
| Deployment | Docker + Railway |
| Language | Python 3.12 |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/ingest` | Ingest filings for one or more tickers |
| GET | `/api/v1/filings` | List ingested filings |
| POST | `/api/v1/extract` | Run GPT-4o extraction on pending filings |
| GET | `/api/v1/extractions` | List extraction results |
| POST | `/api/v1/compare` | Run cross-entity anomaly detection |
| GET | `/api/v1/anomalies` | List detected anomalies |
| POST | `/api/v1/alerts/push` | Push anomalies to Slack |
| POST | `/api/v1/alerts/{id}/review` | Analyst approve or dismiss an alert |
| GET | `/api/v1/alerts` | List alert log entries |
| POST | `/api/v1/export/dcf` | Export DCF scaffold Excel file |
| GET | `/api/v1/export/dcf/{ticker}` | Export DCF for a single ticker |
| POST | `/api/v1/run/graph` | Run full LangGraph pipeline end-to-end |
| POST | `/api/v1/run/full` | Run full pipeline via direct calls |

Full interactive docs: [filings.datawebify.com/docs](https://filings.datawebify.com/docs)

---

## Extracted Financial Signals

Each filing is processed by GPT-4o and returns a validated Pydantic schema containing:

| Signal | Description |
|---|---|
| `capital_structure_changes` | Debt, equity, or hybrid changes with amounts and dates |
| `contract_awards` | Named counterparties, contract values, award dates |
| `capex_guidance` | Forward capex amounts and periods |
| `going_concern_flag` | Boolean flag with detailed explanation |
| `undisclosed_counterparties` | Entities mentioned without full relationship disclosure |

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/umair801/financial-filing-intelligence-agent.git
cd financial-filing-intelligence-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Run the API
uvicorn app.main:app --reload --port 8000

# Open interactive docs
# http://localhost:8000/docs
```

---

## Docker Deployment

```bash
# Build image
docker build -t filings-agent .

# Run container
docker run --env-file .env -p 8000:8000 filings-agent
```

---

## Environment Variables

```bash
OPENAI_API_KEY=           # OpenAI API key for GPT-4o extraction
DATABASE_URL=             # PostgreSQL connection string (Supabase transaction pooler)
SLACK_WEBHOOK_URL=        # Slack incoming webhook URL for alerts
SLACK_BOT_TOKEN=          # Slack bot token for interactive messages
```

---

## LangGraph Orchestration

The full pipeline runs as a stateful LangGraph graph. Each pipeline is a node with shared state passed between them. A conditional edge after ingestion skips extraction if no new filings were found, avoiding unnecessary GPT-4o API calls.

```python
from app.pipelines.orchestration_graph import run_graph

result = run_graph(
    tickers=["AAPL", "MSFT", "GOOGL"],
    filing_types=["8-K", "10-K", "10-Q"],
    days_back=30,
    push_slack=True,
    export_excel=True
)
```

---

## Human-in-the-Loop Review

Every anomaly pushed to Slack requires analyst approval before it is considered actioned. Analysts call the review endpoint directly:

```bash
# Approve an alert
POST /api/v1/alerts/{anomaly_id}/review?action=approve

# Dismiss an alert with notes
POST /api/v1/alerts/{anomaly_id}/review?action=dismiss&notes=false_positive
```

Dismissed alerts are logged to PostgreSQL for future model improvement.

---

## Project Structure

```
app/
├── agents/
│   ├── ingestion_agent.py      # Pipeline 1: SEC EDGAR ingestion
│   ├── extraction_agent.py     # Pipeline 2: GPT-4o extraction
│   ├── comparison_agent.py     # Pipeline 3: Cross-entity anomaly detection
│   ├── alert_agent.py          # Pipeline 4: Slack alerts + review gate
│   └── excel_agent.py          # Pipeline 5: DCF scaffold builder
├── api/
│   └── routes.py               # FastAPI route definitions
├── db/
│   └── database.py             # SQLAlchemy engine and session
├── models/
│   └── schemas.py              # Pydantic schemas for all data models
├── pipelines/
│   └── orchestration_graph.py  # LangGraph multi-agent graph
└── main.py                     # FastAPI application entry point
exports/                        # Generated DCF Excel files
Dockerfile
railway.toml
requirements.txt
```

---

## Built By

**Muhammad Umair** — Agentic AI Specialist

[datawebify.com](https://datawebify.com) | [Upwork](https://upwork.com/freelancers/umair801) | [GitHub](https://github.com/umair801)
