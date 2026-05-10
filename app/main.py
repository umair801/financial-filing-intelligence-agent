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
    <title>Financial Filing Intelligence | Datawebify</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0f1e;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .navbar {
            padding: 18px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .logo { font-size: 18px; font-weight: 700; color: #fff; }
        .logo span { color: #3b82f6; }
        .nav-link {
            color: #94a3b8; text-decoration: none;
            font-size: 13px; transition: color 0.2s;
        }
        .nav-link:hover { color: #fff; }
        .container {
            max-width: 860px;
            margin: 0 auto;
            padding: 60px 24px;
        }
        .hero-text {
            text-align: center;
            margin-bottom: 40px;
        }
        .badge {
            display: inline-block;
            background: rgba(59,130,246,0.15);
            color: #3b82f6;
            border: 1px solid rgba(59,130,246,0.3);
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 20px;
        }
        .status-dot {
            display: inline-block; width: 7px; height: 7px;
            background: #22c55e; border-radius: 50%;
            margin-right: 5px; animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
        }
        h1 {
            font-size: 38px; font-weight: 800;
            color: #fff; margin-bottom: 12px;
            letter-spacing: -0.5px;
        }
        h1 span { color: #3b82f6; }
        .subtitle {
            font-size: 16px; color: #94a3b8; line-height: 1.6;
        }
        .search-box {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 28px;
        }
        .search-row {
            display: flex; gap: 12px; flex-wrap: wrap;
        }
        .ticker-input {
            flex: 1; min-width: 160px;
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            padding: 13px 18px;
            color: #fff; font-size: 15px;
            outline: none; transition: border-color 0.2s;
            text-transform: uppercase;
        }
        .ticker-input::placeholder { color: #475569; text-transform: none; }
        .ticker-input:focus { border-color: #3b82f6; }
        .select-input {
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            padding: 13px 18px;
            color: #fff; font-size: 14px;
            outline: none; cursor: pointer;
        }
        .select-input option { background: #1e293b; }
        .btn-analyze {
            background: #3b82f6; color: #fff;
            border: none; border-radius: 8px;
            padding: 13px 28px; font-size: 15px;
            font-weight: 600; cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            white-space: nowrap;
        }
        .btn-analyze:hover { background: #2563eb; transform: translateY(-1px); }
        .btn-analyze:disabled { background: #1e40af; cursor: not-allowed; transform: none; }
        .loading {
            display: none; text-align: center;
            padding: 40px; color: #94a3b8;
        }
        .spinner {
            width: 36px; height: 36px;
            border: 3px solid rgba(59,130,246,0.2);
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .results { display: none; }
        .result-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
            flex-wrap: wrap; gap: 12px;
        }
        .company-title {
            font-size: 22px; font-weight: 700; color: #fff;
        }
        .filing-meta {
            font-size: 13px; color: #64748b; margin-top: 2px;
        }
        .btn-download {
            background: #059669; color: #fff;
            border: none; border-radius: 8px;
            padding: 10px 20px; font-size: 14px;
            font-weight: 600; cursor: pointer;
            text-decoration: none; display: inline-block;
            transition: background 0.2s;
        }
        .btn-download:hover { background: #047857; }
        .summary-card {
            background: rgba(59,130,246,0.08);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .summary-title {
            font-size: 13px; font-weight: 600;
            color: #3b82f6; text-transform: uppercase;
            letter-spacing: 0.5px; margin-bottom: 12px;
        }
        .summary-text {
            font-size: 15px; color: #e2e8f0;
            line-height: 1.7;
        }
        .signals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px; margin-bottom: 20px;
        }
        .signal-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 18px;
        }
        .signal-label {
            font-size: 11px; font-weight: 600;
            color: #64748b; text-transform: uppercase;
            letter-spacing: 0.5px; margin-bottom: 8px;
        }
        .signal-value {
            font-size: 14px; color: #e2e8f0; line-height: 1.5;
        }
        .signal-value.positive { color: #22c55e; font-weight: 600; }
        .signal-value.warning { color: #f59e0b; font-weight: 600; }
        .signal-value.danger { color: #ef4444; font-weight: 600; }
        .anomalies-section { margin-bottom: 20px; }
        .anomaly-item {
            background: rgba(239,68,68,0.08);
            border: 1px solid rgba(239,68,68,0.2);
            border-radius: 10px; padding: 16px;
            margin-bottom: 10px;
        }
        .anomaly-badge {
            display: inline-block;
            background: rgba(239,68,68,0.15);
            color: #ef4444; border-radius: 4px;
            padding: 2px 8px; font-size: 11px;
            font-weight: 600; margin-bottom: 8px;
        }
        .anomaly-desc { font-size: 14px; color: #cbd5e1; line-height: 1.5; }
        .no-anomalies {
            background: rgba(34,197,94,0.08);
            border: 1px solid rgba(34,197,94,0.2);
            border-radius: 10px; padding: 16px;
            font-size: 14px; color: #22c55e;
        }
        .error-box {
            display: none;
            background: rgba(239,68,68,0.08);
            border: 1px solid rgba(239,68,68,0.2);
            border-radius: 10px; padding: 20px;
            color: #ef4444; font-size: 14px;
            margin-bottom: 20px;
        }
        .footer {
            text-align: center; padding: 40px 24px 24px;
            color: #334155; font-size: 13px;
        }
        .footer a { color: #3b82f6; text-decoration: none; }
    </style>
</head>
<body>

<nav class="navbar">
    <div class="logo">Data<span>webify</span></div>
    <a href="/docs" class="nav-link">API Docs →</a>
</nav>

<div class="container">
    <div class="hero-text">
        <div class="badge"><span class="status-dot"></span>Live Intelligence Engine</div>
        <h1>Financial Filing<br><span>Intelligence Agent</span></h1>
        <p class="subtitle">Enter any US stock ticker to instantly analyze SEC filings,<br>extract financial signals, and download a DCF Excel report.</p>
    </div>

    <div class="search-box">
        <div class="search-row">
            <input
                type="text"
                id="tickerInput"
                class="ticker-input"
                placeholder="Enter ticker symbol (e.g. AAPL, MSFT, TSLA)"
                maxlength="10"
            />
            <select id="filingType" class="select-input">
                <option value="8-K">8-K (Current Events)</option>
                <option value="10-K">10-K (Annual Report)</option>
                <option value="10-Q">10-Q (Quarterly Report)</option>
            </select>
            <select id="daysBack" class="select-input">
                <option value="30">Last 30 days</option>
                <option value="60">Last 60 days</option>
                <option value="90">Last 90 days</option>
            </select>
            <button class="btn-analyze" id="analyzeBtn" onclick="runAnalysis()">
                Analyze
            </button>
        </div>
    </div>

    <div class="error-box" id="errorBox"></div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div id="loadingText">Fetching SEC EDGAR filings...</div>
    </div>

    <div class="results" id="results"></div>
</div>

<footer class="footer">
    Powered by <a href="https://datawebify.com">Datawebify</a> &nbsp;·&nbsp;
    <a href="/docs">API Docs</a> &nbsp;·&nbsp;
    <a href="https://github.com/umair801/financial-filing-intelligence-agent">GitHub</a>
</footer>

<script>
    const loadingMessages = [
        "Fetching SEC EDGAR filings...",
        "Running GPT-4o extraction...",
        "Analyzing financial signals...",
        "Building your report..."
    ];
    let msgIndex = 0;
    let msgInterval;

    function setLoading(show) {
        document.getElementById("loading").style.display = show ? "block" : "none";
        document.getElementById("analyzeBtn").disabled = show;
        document.getElementById("results").style.display = "none";
        document.getElementById("errorBox").style.display = "none";
        if (show) {
            msgIndex = 0;
            document.getElementById("loadingText").textContent = loadingMessages[0];
            msgInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % loadingMessages.length;
                document.getElementById("loadingText").textContent = loadingMessages[msgIndex];
            }, 3000);
        } else {
            clearInterval(msgInterval);
        }
    }

    function showError(msg) {
        const box = document.getElementById("errorBox");
        box.textContent = "⚠ " + msg;
        box.style.display = "block";
    }

    async function runAnalysis() {
        const ticker = document.getElementById("tickerInput").value.trim().toUpperCase();
        const filingType = document.getElementById("filingType").value;
        const daysBack = document.getElementById("daysBack").value;

        if (!ticker) { showError("Please enter a ticker symbol."); return; }

        setLoading(true);

        try {
            // Step 1: Ingest
            await fetch(`/api/v1/ingest?tickers=${ticker}&filing_types=${filingType}&days_back=${daysBack}`, { method: "POST" });

            // Step 2: Extract
            await fetch(`/api/v1/extract`, { method: "POST" });

            // Step 3: Get filings
            const filingsRes = await fetch(`/api/v1/filings?ticker=${ticker}&limit=1`);
            const filingsData = await filingsRes.json();

            // Step 4: Get extractions
            const extRes = await fetch(`/api/v1/extractions?ticker=${ticker}&limit=1`);
            const extData = await extRes.json();

            // Step 5: Get anomalies
            const anomalyRes = await fetch(`/api/v1/anomalies?ticker=${ticker}&limit=5`);
            const anomalyData = await anomalyRes.json();

            setLoading(false);
            renderResults(ticker, filingsData, extData, anomalyData);

        } catch(e) {
            setLoading(false);
            showError("Analysis failed. Please try again or check the ticker symbol.");
        }
    }

    function renderResults(ticker, filingsData, extData, anomalyData) {
        const filing = filingsData.filings?.[0];
        const extraction = extData.extractions?.[0];
        const anomalies = anomalyData.anomalies || [];

        if (!filing) {
            showError("No filings found for " + ticker + " in the selected period. Try a longer date range.");
            return;
        }

        const goingConcern = extraction?.going_concern_flag;
        const gcClass = goingConcern ? "danger" : "positive";
        const gcText = goingConcern ? "⚠ Going Concern Flag Raised" : "✓ No Going Concern Issues";

        const filingDate = filing.filed_date || "N/A";
        const filingType = filing.filing_type || "N/A";
        const company = filing.company_name || ticker;

        // Plain English summary
        let summary = `${company} filed a ${filingType} on ${filingDate}. `;
        if (goingConcern) {
            summary += "⚠ This filing contains a going concern flag, indicating the auditors have raised doubts about the company's ability to continue as a going concern. Immediate attention is recommended. ";
        } else {
            summary += "No going concern issues were detected. ";
        }
        if (anomalies.length > 0) {
            summary += `${anomalies.length} anomaly${anomalies.length > 1 ? "s were" : " was"} detected across cross-entity analysis. Review the anomaly section below for details.`;
        } else {
            summary += "No cross-entity anomalies were detected in this filing cycle.";
        }

        let anomalyHTML = "";
        if (anomalies.length === 0) {
            anomalyHTML = `<div class="no-anomalies">✓ No anomalies detected for ${ticker} in this filing cycle.</div>`;
        } else {
            anomalyHTML = anomalies.map(a => `
                <div class="anomaly-item">
                    <div class="anomaly-badge">${a.anomaly_type?.replace(/_/g," ").toUpperCase()}</div>
                    <div class="anomaly-desc">${a.description}</div>
                </div>
            `).join("");
        }

        const html = `
            <div class="result-header">
                <div>
                    <div class="company-title">${company} (${ticker})</div>
                    <div class="filing-meta">${filingType} · Filed ${filingDate} · Powered by GPT-4o</div>
                </div>
                <a href="/api/v1/export/dcf/${ticker}" class="btn-download">
                    ⬇ Download DCF Excel
                </a>
            </div>

            <div class="summary-card">
                <div class="summary-title">📋 Plain English Summary</div>
                <div class="summary-text">${summary}</div>
            </div>

            <div class="signals-grid">
                <div class="signal-card">
                    <div class="signal-label">Going Concern</div>
                    <div class="signal-value ${gcClass}">${gcText}</div>
                </div>
                <div class="signal-card">
                    <div class="signal-label">Filing Type</div>
                    <div class="signal-value">${filingType}</div>
                </div>
                <div class="signal-card">
                    <div class="signal-label">Filed Date</div>
                    <div class="signal-value">${filingDate}</div>
                </div>
                <div class="signal-card">
                    <div class="signal-label">Anomalies Detected</div>
                    <div class="signal-value ${anomalies.length > 0 ? "warning" : "positive"}">
                        ${anomalies.length > 0 ? "⚠ " + anomalies.length + " Anomaly" + (anomalies.length > 1 ? "s" : "") : "✓ None"}
                    </div>
                </div>
            </div>

            <div class="anomalies-section">
                <div class="summary-title" style="color:#94a3b8; font-size:12px; margin-bottom:12px;">ANOMALY REPORT</div>
                ${anomalyHTML}
            </div>
        `;

        const resultsDiv = document.getElementById("results");
        resultsDiv.innerHTML = html;
        resultsDiv.style.display = "block";
    }

    // Allow Enter key to trigger analysis
    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("tickerInput").addEventListener("keydown", e => {
            if (e.key === "Enter") runAnalysis();
        });
    });
</script>

</body>
</html>
"""