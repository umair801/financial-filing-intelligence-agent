"""
Financial Filing Intelligence Agent — FastAPI Entry Point
Datawebify | filings.datawebify.com
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Financial Filing Intelligence Agent",
    description="SEC EDGAR filing ingestion, GPT-4o extraction, cross-entity anomaly detection, Slack alerts, and DCF export. Powered by Datawebify.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Filing Intelligence Agent | Datawebify</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0f1e;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .navbar {
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .logo {
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            letter-spacing: 0.5px;
        }
        .logo span { color: #3b82f6; }
        .nav-link {
            color: #94a3b8;
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s;
        }
        .nav-link:hover { color: #fff; }
        .hero {
            max-width: 860px;
            margin: 80px auto 0;
            padding: 0 40px;
            text-align: center;
        }
        .badge {
            display: inline-block;
            background: rgba(59,130,246,0.15);
            color: #3b82f6;
            border: 1px solid rgba(59,130,246,0.3);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 28px;
        }
        h1 {
            font-size: 52px;
            font-weight: 800;
            line-height: 1.15;
            color: #fff;
            margin-bottom: 20px;
            letter-spacing: -1px;
        }
        h1 span { color: #3b82f6; }
        .subtitle {
            font-size: 18px;
            color: #94a3b8;
            line-height: 1.7;
            max-width: 640px;
            margin: 0 auto 40px;
        }
        .cta-group {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 80px;
        }
        .btn-primary {
            background: #3b82f6;
            color: #fff;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 15px;
            transition: background 0.2s, transform 0.1s;
        }
        .btn-primary:hover { background: #2563eb; transform: translateY(-1px); }
        .btn-secondary {
            background: rgba(255,255,255,0.06);
            color: #e2e8f0;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 15px;
            border: 1px solid rgba(255,255,255,0.12);
            transition: background 0.2s;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); }
        .features {
            max-width: 1000px;
            margin: 0 auto 80px;
            padding: 0 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }
        .feature-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 28px;
            transition: border-color 0.2s;
        }
        .feature-card:hover { border-color: rgba(59,130,246,0.4); }
        .feature-icon {
            font-size: 28px;
            margin-bottom: 14px;
        }
        .feature-title {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 10px;
        }
        .feature-desc {
            font-size: 14px;
            color: #94a3b8;
            line-height: 1.6;
        }
        .stats {
            max-width: 800px;
            margin: 0 auto 80px;
            padding: 0 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 20px;
            text-align: center;
        }
        .stat-card {
            background: rgba(59,130,246,0.08);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 12px;
            padding: 24px;
        }
        .stat-number {
            font-size: 32px;
            font-weight: 800;
            color: #3b82f6;
            margin-bottom: 6px;
        }
        .stat-label {
            font-size: 13px;
            color: #94a3b8;
        }
        .section-title {
            text-align: center;
            font-size: 28px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 40px;
        }
        .footer {
            border-top: 1px solid rgba(255,255,255,0.08);
            padding: 30px 40px;
            text-align: center;
            color: #475569;
            font-size: 13px;
        }
        .footer a { color: #3b82f6; text-decoration: none; }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
    </style>
</head>
<body>

<nav class="navbar">
    <div class="logo">Data<span>webify</span></div>
    <a href="/docs" class="nav-link">API Documentation →</a>
</nav>

<section class="hero">
    <div class="badge"><span class="status-dot"></span>Live & Running — v1.0.0</div>
    <h1>Financial Filing<br><span>Intelligence Agent</span></h1>
    <p class="subtitle">
        Automatically monitors SEC EDGAR filings, extracts financial signals using GPT-4o,
        detects anomalies across sector baskets, and delivers analyst-ready alerts and Excel reports.
    </p>
    <div class="cta-group">
        <a href="/docs" class="btn-primary">View API Docs</a>
        <a href="/api/v1/health" class="btn-secondary">System Health</a>
    </div>
</section>

<div class="stats">
    <div class="stat-card">
        <div class="stat-number">5</div>
        <div class="stat-label">AI Pipelines</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">4</div>
        <div class="stat-label">Filing Types</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">GPT-4o</div>
        <div class="stat-label">Extraction Model</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">Live</div>
        <div class="stat-label">Production Status</div>
    </div>
</div>

<p class="section-title">What It Does</p>
<div class="features">
    <div class="feature-card">
        <div class="feature-icon">📥</div>
        <div class="feature-title">Filing Ingestion</div>
        <div class="feature-desc">Polls SEC EDGAR every 4 hours for 8-K, 10-K, 10-Q, and 6-K filings across your configured ticker basket.</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">🤖</div>
        <div class="feature-title">GPT-4o Extraction</div>
        <div class="feature-desc">Extracts capital structure changes, contract awards, capex guidance, going-concern flags, and undisclosed counterparties from every filing.</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">🔍</div>
        <div class="feature-title">Anomaly Detection</div>
        <div class="feature-desc">Cross-references counterparties across a sector basket. Surfaces entities named in one filing but undisclosed in another.</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">🔔</div>
        <div class="feature-title">Slack Alerts</div>
        <div class="feature-desc">Pushes anomaly reports to Slack with a human-in-the-loop review gate. Analysts approve or dismiss each alert directly.</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">📊</div>
        <div class="feature-title">DCF Excel Export</div>
        <div class="feature-desc">Builds a refreshed DCF scaffold Excel file per company per filing cycle using extracted revenue, capex, and guidance inputs.</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">⚡</div>
        <div class="feature-title">LangGraph Orchestration</div>
        <div class="feature-desc">All five pipelines run as a stateful LangGraph multi-agent graph. One API call triggers the full end-to-end workflow.</div>
    </div>
</div>

<footer class="footer">
    Built by <a href="https://datawebify.com">Datawebify</a> &nbsp;·&nbsp;
    <a href="/docs">API Docs</a> &nbsp;·&nbsp;
    <a href="https://github.com/umair801/financial-filing-intelligence-agent">GitHub</a>
</footer>

</body>
</html>
"""