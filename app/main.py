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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #f9fafb;
            --bg2: #f3f4f6;
            --surface: #ffffff;
            --border: #e5e7eb;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --accent-light: rgba(99,102,241,0.08);
            --green: #10b981;
            --red: #ef4444;
            --yellow: #f59e0b;
            --text: #1f2937;
            --muted: #6b7280;
            --shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }

        /* Navbar */
        .navbar {
            position: fixed; top: 0; left: 0; right: 0; z-index: 100;
            display: flex; justify-content: space-between; align-items: center;
            padding: 16px 40px;
            background: rgba(255,255,255,0.97);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            box-shadow: var(--shadow);
        }
        .logo { font-size: 18px; font-weight: 700; color: var(--text); }
        .logo span { color: var(--accent); }
        .nav-link {
            color: var(--muted); text-decoration: none;
            font-size: 13px; font-weight: 500;
            transition: color 0.2s;
        }
        .nav-link:hover { color: var(--accent); }

        /* Hero */
        .container { max-width: 860px; margin: 0 auto; padding: 100px 24px 60px; }
        .hero-text { text-align: center; margin-bottom: 36px; }
        .badge {
            display: inline-flex; align-items: center; gap: 6px;
            background: rgba(16,185,129,0.08);
            border: 1px solid rgba(16,185,129,0.3);
            color: var(--green);
            padding: 5px 14px; border-radius: 20px;
            font-size: 12px; font-weight: 600; margin-bottom: 20px;
        }
        .status-dot {
            width: 7px; height: 7px; background: var(--green);
            border-radius: 50%; animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
        h1 {
            font-size: 38px; font-weight: 800;
            color: var(--text); margin-bottom: 12px;
            letter-spacing: -0.5px; line-height: 1.2;
        }
        h1 span { color: var(--accent); }
        .subtitle { font-size: 16px; color: var(--muted); line-height: 1.6; }

        /* Search Box */
        .search-box {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: var(--shadow);
        }
        .search-row { display: flex; gap: 12px; flex-wrap: wrap; }
        .ticker-input {
            flex: 1; min-width: 160px;
            background: var(--bg);
            border: 1.5px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            color: var(--text); font-size: 15px;
            outline: none; transition: border-color 0.2s;
            text-transform: uppercase; font-weight: 600;
        }
        .ticker-input::placeholder { color: #9ca3af; text-transform: none; font-weight: 400; }
        .ticker-input:focus { border-color: var(--accent); background: #fff; }
        .select-input {
            background: var(--bg);
            border: 1.5px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            color: var(--text); font-size: 14px;
            outline: none; cursor: pointer;
            transition: border-color 0.2s;
        }
        .select-input:focus { border-color: var(--accent); }
        .btn-analyze {
            background: var(--accent); color: #fff;
            border: none; border-radius: 8px;
            padding: 12px 28px; font-size: 15px;
            font-weight: 600; cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            white-space: nowrap;
        }
        .btn-analyze:hover { background: var(--accent-hover); transform: translateY(-1px); }
        .btn-analyze:disabled { background: #a5b4fc; cursor: not-allowed; transform: none; }

        /* Loading */
        .loading { display: none; text-align: center; padding: 48px; color: var(--muted); }
        .spinner {
            width: 36px; height: 36px;
            border: 3px solid rgba(99,102,241,0.15);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text { font-size: 14px; color: var(--muted); }

        /* Error */
        .error-box {
            display: none;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 10px; padding: 16px 20px;
            color: var(--red); font-size: 14px;
            margin-bottom: 20px;
        }

        /* Results */
        .results { display: none; }
        .result-header {
            display: flex; justify-content: space-between;
            align-items: flex-start; margin-bottom: 20px;
            flex-wrap: wrap; gap: 12px;
        }
        .company-title { font-size: 22px; font-weight: 800; color: var(--text); }
        .filing-meta { font-size: 13px; color: var(--muted); margin-top: 4px; }
        .btn-download {
            background: var(--green); color: #fff;
            border: none; border-radius: 8px;
            padding: 10px 20px; font-size: 14px;
            font-weight: 600; cursor: pointer;
            text-decoration: none; display: inline-flex;
            align-items: center; gap: 8px;
            transition: background 0.2s, transform 0.1s;
        }
        .btn-download:hover { background: #059669; transform: translateY(-1px); }

        /* Summary Card */
        .summary-card {
            background: var(--accent-light);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 12px; padding: 24px;
            margin-bottom: 16px;
        }
        .summary-label {
            font-size: 11px; font-weight: 700;
            color: var(--accent); text-transform: uppercase;
            letter-spacing: 0.8px; margin-bottom: 10px;
        }
        .summary-text { font-size: 15px; color: var(--text); line-height: 1.7; }

        /* Signal Cards */
        .signals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px; margin-bottom: 16px;
        }
        .signal-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px; padding: 18px;
            box-shadow: var(--shadow);
        }
        .signal-label {
            font-size: 11px; font-weight: 600;
            color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.5px; margin-bottom: 8px;
        }
        .signal-value { font-size: 14px; color: var(--text); line-height: 1.5; font-weight: 500; }
        .signal-value.positive { color: var(--green); }
        .signal-value.warning { color: var(--yellow); }
        .signal-value.danger { color: var(--red); }

        /* Anomaly Section */
        .section-label {
            font-size: 11px; font-weight: 700;
            color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.8px; margin-bottom: 12px;
        }
        .anomaly-item {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 10px; padding: 16px;
            margin-bottom: 10px;
        }
        .anomaly-badge {
            display: inline-block;
            background: #fee2e2; color: var(--red);
            border-radius: 4px; padding: 2px 8px;
            font-size: 11px; font-weight: 700;
            margin-bottom: 8px; letter-spacing: 0.5px;
        }
        .anomaly-desc { font-size: 14px; color: #7f1d1d; line-height: 1.5; }
        .no-anomalies {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 10px; padding: 16px;
            font-size: 14px; color: #166534; font-weight: 500;
        }

        /* Footer */
        .footer {
            text-align: center; padding: 40px 24px 24px;
            color: var(--muted); font-size: 13px;
            border-top: 1px solid var(--border); margin-top: 40px;
        }
        .footer a { color: var(--accent); text-decoration: none; }
        .footer a:hover { text-decoration: underline; }

        @media (max-width: 600px) {
            .navbar { padding: 14px 20px; }
            .container { padding: 80px 16px 40px; }
            h1 { font-size: 28px; }
            .search-row { flex-direction: column; }
            .btn-analyze { width: 100%; }
        }
    </style>
</head>
<body>

<nav class="navbar">
    <div class="logo">Data<span>webify</span></div>
    <a href="/docs" class="nav-link">API Docs <i class="fas fa-arrow-right" style="font-size:11px;"></i></a>
</nav>

<div class="container">
    <div class="hero-text">
        <div class="badge"><span class="status-dot"></span>Live Intelligence Engine</div>
        <h1>Financial Filing<br><span>Intelligence Agent</span></h1>
        <p class="subtitle">Enter any US stock ticker to instantly analyze SEC filings,<br>extract financial signals, and download a DCF Excel report.</p>
    </div>

    <div class="search-box">
        <div class="search-row">
            <input type="text" id="tickerInput" class="ticker-input"
                placeholder="Enter ticker (e.g. AAPL, MSFT, TSLA)" maxlength="10" />
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
                <i class="fas fa-search"></i> Analyze
            </button>
        </div>
    </div>

    <div class="error-box" id="errorBox"></div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div class="loading-text" id="loadingText">Fetching SEC EDGAR filings...</div>
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
    let msgIndex = 0, msgInterval;

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
            await fetch(`/api/v1/ingest?tickers=${ticker}&filing_types=${filingType}&days_back=${daysBack}`, { method: "POST" });
            await fetch(`/api/v1/extract`, { method: "POST" });
            const [filingsRes, extRes, anomalyRes] = await Promise.all([
                fetch(`/api/v1/filings?ticker=${ticker}&limit=1`),
                fetch(`/api/v1/extractions?ticker=${ticker}&limit=1`),
                fetch(`/api/v1/anomalies?ticker=${ticker}&limit=5`)
            ]);
            const [filingsData, extData, anomalyData] = await Promise.all([
                filingsRes.json(), extRes.json(), anomalyRes.json()
            ]);
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

        let summary = `${company} filed a ${filingType} on ${filingDate}. `;
        summary += goingConcern
            ? "⚠ This filing contains a going concern flag — auditors have raised doubts about the company's ability to continue operations. Immediate attention is recommended. "
            : "No going concern issues were detected. ";
        summary += anomalies.length > 0
            ? `${anomalies.length} anomaly${anomalies.length > 1 ? "s were" : " was"} detected in cross-entity analysis. See the anomaly report below.`
            : "No cross-entity anomalies were detected in this filing cycle.";

        const anomalyHTML = anomalies.length === 0
            ? `<div class="no-anomalies"><i class="fas fa-check-circle"></i> No anomalies detected for ${ticker} in this filing cycle.</div>`
            : anomalies.map(a => `
                <div class="anomaly-item">
                    <div class="anomaly-badge">${a.anomaly_type?.replace(/_/g," ").toUpperCase()}</div>
                    <div class="anomaly-desc">${a.description}</div>
                </div>`).join("");

        document.getElementById("results").innerHTML = `
            <div class="result-header">
                <div>
                    <div class="company-title">${company} (${ticker})</div>
                    <div class="filing-meta">${filingType} &nbsp;·&nbsp; Filed ${filingDate} &nbsp;·&nbsp; Powered by GPT-4o</div>
                </div>
                <a href="/api/v1/export/dcf/${ticker}" class="btn-download">
                    <i class="fas fa-download"></i> Download DCF Excel
                </a>
            </div>
            <div class="summary-card">
                <div class="summary-label">📋 Plain English Summary</div>
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
            <div class="section-label">Anomaly Report</div>
            ${anomalyHTML}
        `;
        document.getElementById("results").style.display = "block";
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("tickerInput").addEventListener("keydown", e => {
            if (e.key === "Enter") runAnalysis();
        });
    });
</script>
</body>
</html>
"""
