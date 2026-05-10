import os
import json
from uuid import UUID
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import structlog
from sqlalchemy import text

from app.db.database import SessionLocal
from app.models.schemas import AnomalyReport

load_dotenv()

logger = structlog.get_logger()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_extractions_for_basket(tickers: list[str]) -> list[dict]:
    """Fetch all extractions for a given sector basket."""
    db = SessionLocal()
    try:
        placeholders = ", ".join([f"'{t.upper()}'" for t in tickers])
        rows = db.execute(text(f"""
            SELECT
                e.id,
                e.filing_id,
                e.ticker,
                e.filing_type,
                e.capital_structure_changes,
                e.contract_awards,
                e.capex_guidance,
                e.going_concern_flag,
                e.undisclosed_counterparties,
                f.filed_date
            FROM filings_extractions e
            JOIN filings_raw f ON e.filing_id = f.id
            WHERE e.ticker IN ({placeholders})
            ORDER BY e.ticker, f.filed_date DESC
        """)).fetchall()

        return [
            {
                "id": str(r[0]),
                "filing_id": str(r[1]),
                "ticker": r[2],
                "filing_type": r[3],
                "capital_structure_changes": r[4] or [],
                "contract_awards": r[5] or [],
                "capex_guidance": r[6] or [],
                "going_concern_flag": r[7],
                "undisclosed_counterparties": r[8] or [],
                "filed_date": str(r[9])
            }
            for r in rows
        ]
    finally:
        db.close()


def build_counterparty_map(extractions: list[dict]) -> dict[str, list[dict]]:
    """Build a map of counterparty names to which tickers mention them."""
    counterparty_map = {}

    for ext in extractions:
        ticker = ext["ticker"]

        # Named counterparties from contract awards
        for award in (ext["contract_awards"] or []):
            name = award.get("counterparty", "").strip()
            if name and len(name) > 2:
                if name not in counterparty_map:
                    counterparty_map[name] = []
                counterparty_map[name].append({
                    "ticker": ticker,
                    "filing_id": ext["filing_id"],
                    "extraction_id": ext["id"],
                    "source": "contract_award",
                    "context": award.get("description", "")
                })

        # Undisclosed counterparties flagged by GPT-4o
        for cp in (ext["undisclosed_counterparties"] or []):
            name = cp.get("name", "").strip()
            if name and len(name) > 2:
                if name not in counterparty_map:
                    counterparty_map[name] = []
                counterparty_map[name].append({
                    "ticker": ticker,
                    "filing_id": ext["filing_id"],
                    "extraction_id": ext["id"],
                    "source": "undisclosed",
                    "context": cp.get("context", ""),
                    "risk_level": cp.get("risk_level", "medium")
                })

    return counterparty_map


def detect_cross_entity_anomalies(
    extractions: list[dict],
    sector_basket: list[str]
) -> list[AnomalyReport]:
    """Detect anomalies across entities in the sector basket."""
    anomalies = []
    counterparty_map = build_counterparty_map(extractions)

    # Anomaly 1: counterparty named in one filing, undisclosed in another
    for cp_name, mentions in counterparty_map.items():
        tickers_mentioned = set(m["ticker"] for m in mentions)
        if len(tickers_mentioned) < 2:
            continue

        named_mentions = [m for m in mentions if m["source"] == "contract_award"]
        undisclosed_mentions = [m for m in mentions if m["source"] == "undisclosed"]

        for named in named_mentions:
            for undisclosed in undisclosed_mentions:
                if named["ticker"] != undisclosed["ticker"]:
                    anomalies.append(AnomalyReport(
                        sector_basket=sector_basket,
                        anomaly_type="cross_entity_undisclosed_counterparty",
                        description=(
                            f"'{cp_name}' is named as a contract counterparty in "
                            f"{named['ticker']} filings but appears as undisclosed "
                            f"in {undisclosed['ticker']} filings. Context: {undisclosed['context'][:200]}"
                        ),
                        source_ticker=named["ticker"],
                        target_ticker=undisclosed["ticker"],
                        source_filing_id=UUID(named["filing_id"]),
                        target_filing_id=UUID(undisclosed["filing_id"]),
                        severity="high"
                    ))

    # Anomaly 2: going concern flag in any entity
    for ext in extractions:
        if ext.get("going_concern_flag"):
            anomalies.append(AnomalyReport(
                sector_basket=sector_basket,
                anomaly_type="going_concern_flag",
                description=(
                    f"{ext['ticker']} has a going concern flag in their "
                    f"{ext['filing_type']} filing dated {ext['filed_date']}."
                ),
                source_ticker=ext["ticker"],
                target_ticker=ext["ticker"],
                source_filing_id=UUID(ext["filing_id"]),
                target_filing_id=UUID(ext["filing_id"]),
                severity="critical"
            ))

    return anomalies


def save_anomaly_to_db(anomaly: AnomalyReport) -> Optional[str]:
    """Save anomaly to filings_anomalies table."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                INSERT INTO filings_anomalies
                (sector_basket, anomaly_type, description, source_ticker,
                 target_ticker, source_filing_id, target_filing_id, severity, status)
                VALUES
                (:sector_basket, :anomaly_type, :description, :source_ticker,
                 :target_ticker, :source_filing_id, :target_filing_id, :severity, :status)
                RETURNING id
            """),
            {
                "sector_basket": anomaly.sector_basket,
                "anomaly_type": anomaly.anomaly_type,
                "description": anomaly.description,
                "source_ticker": anomaly.source_ticker,
                "target_ticker": anomaly.target_ticker,
                "source_filing_id": str(anomaly.source_filing_id),
                "target_filing_id": str(anomaly.target_filing_id),
                "severity": anomaly.severity,
                "status": anomaly.status
            }
        )
        db.commit()
        anomaly_id = str(result.fetchone()[0])
        logger.info("Anomaly saved", type=anomaly.anomaly_type, id=anomaly_id)
        return anomaly_id
    except Exception as e:
        db.rollback()
        logger.error("Failed to save anomaly", error=str(e))
        return None
    finally:
        db.close()


async def run_comparison_agent(sector_basket: list[str]) -> dict:
    """Main comparison agent: detects cross-entity anomalies for a sector basket."""
    logger.info("Starting comparison agent", basket=sector_basket)

    extractions = get_extractions_for_basket(sector_basket)
    if not extractions:
        logger.warning("No extractions found for basket", basket=sector_basket)
        return {"total": 0, "saved": 0, "errors": 0}

    anomalies = detect_cross_entity_anomalies(extractions, sector_basket)
    results = {"total": len(anomalies), "saved": 0, "errors": 0}

    for anomaly in anomalies:
        anomaly_id = save_anomaly_to_db(anomaly)
        if anomaly_id:
            results["saved"] += 1
        else:
            results["errors"] += 1

    logger.info("Comparison agent complete", **results)
    return results