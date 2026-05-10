"""
FastAPI Routes — Financial Filing Intelligence Agent
Datawebify | filings.datawebify.com
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.agents.ingestion_agent import run_ingestion_agent
from app.agents.extraction_agent import run_extraction_agent
from app.agents.comparison_agent import run_comparison_agent
from app.agents.alert_agent import run_alert_pipeline, process_analyst_review
from app.agents.excel_agent import run_excel_pipeline, build_dcf_export

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "Financial Filing Intelligence Agent",
        "brand": "Datawebify"
    }


# ---------------------------------------------------------------------------
# Pipeline 1: Ingestion
# ---------------------------------------------------------------------------

@router.post("/ingest", tags=["Pipeline 1: Ingestion"])
def ingest_filings(
    tickers: List[str] = Query(..., description="Ticker symbols, e.g. AAPL MSFT"),
    filing_types: List[str] = Query(default=["8-K", "10-K", "10-Q"]),
    days_back: int = Query(default=30, description="How many days back to search"),
):
    """
    Ingest SEC EDGAR filings for one or more tickers.
    Downloads and stores raw filings into the database.
    """
    try:
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days_back)).isoformat()
        result = asyncio.run(
            run_ingestion_agent(
                tickers=tickers,
                form_types=filing_types,
                start_date=start_date,
                end_date=end_date
            )
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filings", tags=["Pipeline 1: Ingestion"])
def list_filings(
    ticker: Optional[str] = Query(None),
    filing_type: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List raw filings stored in the database."""
    try:
        query = """
            SELECT id, ticker, company_name, filing_type, filed_date, status, filing_url
            FROM filings_raw WHERE 1=1
        """
        params = {}
        if ticker:
            query += " AND ticker = :ticker"
            params["ticker"] = ticker.upper()
        if filing_type:
            query += " AND filing_type = :filing_type"
            params["filing_type"] = filing_type
        query += " ORDER BY filed_date DESC LIMIT :limit"
        params["limit"] = limit

        rows = db.execute(text(query), params).fetchall()
        filings = [
            {
                "id": str(r[0]),
                "ticker": r[1],
                "company_name": r[2],
                "filing_type": r[3],
                "filed_date": str(r[4]),
                "status": r[5],
                "filing_url": r[6],
            }
            for r in rows
        ]
        return {"success": True, "count": len(filings), "filings": filings}
    except Exception as e:
        logger.error(f"List filings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipeline 2: Extraction
# ---------------------------------------------------------------------------

@router.post("/extract", tags=["Pipeline 2: Extraction"])
def extract_filings():
    """
    Run GPT-4o extraction on all pending ingested filings.
    Extracts capital structure, contracts, capex, going-concern, counterparties.
    """
    try:
        result = asyncio.run(run_extraction_agent())
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extractions", tags=["Pipeline 2: Extraction"])
def list_extractions(
    ticker: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List extraction results stored in the database."""
    try:
        query = """
            SELECT e.id, e.ticker, e.filing_type, e.going_concern_flag,
                   e.created_at, r.filed_date
            FROM filings_extractions e
            JOIN filings_raw r ON r.id = e.filing_id
            WHERE 1=1
        """
        params = {}
        if ticker:
            query += " AND e.ticker = :ticker"
            params["ticker"] = ticker.upper()
        query += " ORDER BY e.created_at DESC LIMIT :limit"
        params["limit"] = limit

        rows = db.execute(text(query), params).fetchall()
        extractions = [
            {
                "id": str(r[0]),
                "ticker": r[1],
                "filing_type": r[2],
                "going_concern_flag": r[3],
                "extracted_at": str(r[4]),
                "filed_date": str(r[5]),
            }
            for r in rows
        ]
        return {"success": True, "count": len(extractions), "extractions": extractions}
    except Exception as e:
        logger.error(f"List extractions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipeline 3: Comparison
# ---------------------------------------------------------------------------

@router.post("/compare", tags=["Pipeline 3: Comparison"])
def compare_sector(
    tickers: List[str] = Query(..., description="Sector basket tickers"),
):
    """
    Run cross-entity anomaly detection across a sector basket.
    Detects undisclosed counterparties and going-concern flags.
    """
    try:
        result = asyncio.run(run_comparison_agent(sector_basket=tickers))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies", tags=["Pipeline 3: Comparison"])
def list_anomalies(
    ticker: Optional[str] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List detected anomalies stored in the database."""
    try:
        query = """
            SELECT id, anomaly_type, source_ticker, target_ticker,
                   description, severity, status, created_at
            FROM filings_anomalies WHERE 1=1
        """
        params = {}
        if ticker:
            query += " AND (source_ticker = :ticker OR target_ticker = :ticker)"
            params["ticker"] = ticker.upper()
        if anomaly_type:
            query += " AND anomaly_type = :anomaly_type"
            params["anomaly_type"] = anomaly_type
        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        rows = db.execute(text(query), params).fetchall()
        anomalies = [
            {
                "id": str(r[0]),
                "anomaly_type": r[1],
                "source_ticker": r[2],
                "target_ticker": r[3],
                "description": r[4],
                "severity": r[5],
                "status": r[6],
                "detected_at": str(r[7]),
            }
            for r in rows
        ]
        return {"success": True, "count": len(anomalies), "anomalies": anomalies}
    except Exception as e:
        logger.error(f"List anomalies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipeline 4: Alerts
# ---------------------------------------------------------------------------

@router.post("/alerts/push", tags=["Pipeline 4: Alerts"])
def push_alerts(
    tickers: Optional[List[str]] = Query(None),
):
    """Push unalerted anomalies to Slack with human-in-the-loop review gate."""
    try:
        result = run_alert_pipeline(tickers=tickers)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Alert push error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{anomaly_id}/review", tags=["Pipeline 4: Alerts"])
def review_alert(
    anomaly_id: str,
    action: str = Query(..., description="approve or dismiss"),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Analyst approves or dismisses an alert. Dismissed alerts logged for model improvement."""
    result = process_analyst_review(db=db, anomaly_id=anomaly_id, action=action, notes=notes)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {"success": True, "result": result}


@router.get("/alerts", tags=["Pipeline 4: Alerts"])
def list_alerts(
    action: Optional[str] = Query(None, description="pending, approve, or dismiss"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List alert log entries with analyst review status."""
    try:
        query = """
            SELECT al.anomaly_id, al.slack_sent, al.analyst_action,
                   al.analyst_notes, al.reviewed_at, al.created_at,
                   a.anomaly_type, a.source_ticker, a.target_ticker
            FROM filings_alert_logs al
            LEFT JOIN filings_anomalies a ON a.id = al.anomaly_id::uuid
            WHERE 1=1
        """
        params = {}
        if action:
            query += " AND al.analyst_action = :action"
            params["action"] = action
        query += " ORDER BY al.created_at DESC LIMIT :limit"
        params["limit"] = limit

        rows = db.execute(text(query), params).fetchall()
        alerts = [
            {
                "anomaly_id": r[0],
                "slack_sent": r[1],
                "analyst_action": r[2],
                "analyst_notes": r[3],
                "reviewed_at": str(r[4]) if r[4] else None,
                "created_at": str(r[5]),
                "anomaly_type": r[6],
                "source_ticker": r[7],
                "target_ticker": r[8],
            }
            for r in rows
        ]
        return {"success": True, "count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"List alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipeline 5: Excel Export
# ---------------------------------------------------------------------------

@router.post("/export/dcf", tags=["Pipeline 5: Excel Export"])
def export_dcf(
    tickers: List[str] = Query(..., description="Tickers to build DCF scaffold for"),
):
    """Build and export DCF scaffold Excel files for one or more tickers."""
    try:
        result = run_excel_pipeline(tickers=tickers)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"DCF export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/dcf/{ticker}", tags=["Pipeline 5: Excel Export"])
def export_dcf_single(ticker: str, filing_id: Optional[str] = Query(None)):
    """Export DCF scaffold for a single ticker, optionally for a specific filing."""
    try:
        result = build_dcf_export(ticker=ticker.upper(), filing_id=filing_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return {"success": True, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DCF export error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Full pipeline orchestration
# ---------------------------------------------------------------------------

@router.post("/run/full", tags=["Orchestration"])
def run_full_pipeline(
    tickers: List[str] = Query(..., description="Sector basket tickers"),
    filing_types: List[str] = Query(default=["8-K", "10-K", "10-Q"]),
    days_back: int = Query(default=30),
    export_excel: bool = Query(default=True),
    push_slack: bool = Query(default=True),
):
    """
    Run the complete pipeline end-to-end:
    Ingest -> Extract -> Compare -> Alert -> Export
    """
    results = {}
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=days_back)).isoformat()

    results["ingestion"] = asyncio.run(
        run_ingestion_agent(tickers=tickers, form_types=filing_types,
                            start_date=start_date, end_date=end_date)
    )
    results["extraction"] = asyncio.run(run_extraction_agent())
    results["comparison"] = asyncio.run(run_comparison_agent(sector_basket=tickers))

    if push_slack:
        results["alerts"] = run_alert_pipeline(tickers=tickers)
    if export_excel:
        results["excel_export"] = run_excel_pipeline(tickers=tickers)

    return {"success": True, "results": results}


# ---------------------------------------------------------------------------
# LangGraph orchestration route
# ---------------------------------------------------------------------------

@router.post("/run/graph", tags=["Orchestration"])
def run_langgraph(
    tickers: List[str] = Query(..., description="Sector basket tickers"),
    filing_types: List[str] = Query(default=["8-K", "10-K", "10-Q"]),
    days_back: int = Query(default=30),
    push_slack: bool = Query(default=False, description="Push alerts to Slack"),
    export_excel: bool = Query(default=True, description="Export DCF Excel files"),
):
    """
    Run the full LangGraph multi-agent orchestration graph.
    Ingest -> Extract -> Compare -> Alert -> Export
    All pipeline results returned in a single response.
    """
    from app.pipelines.orchestration_graph import run_graph
    try:
        result = run_graph(
            tickers=tickers,
            filing_types=filing_types,
            days_back=days_back,
            push_slack=push_slack,
            export_excel=export_excel,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"LangGraph run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))