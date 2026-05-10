import os
import json
from uuid import UUID
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import structlog
from sqlalchemy import text

from app.db.database import SessionLocal
from app.models.schemas import (
    ExtractionResult,
    CapitalStructureChange,
    ContractAward,
    CapexGuidance,
    UndisclosedCounterparty
)

load_dotenv()

logger = structlog.get_logger()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """
You are a senior financial analyst. Analyze the following SEC filing text and extract structured signals.

Return a JSON object with exactly these keys:
{{
    "capital_structure_changes": [
        {{"description": "...", "change_type": "debt|equity|hybrid", "amount": "...", "currency": "USD", "effective_date": "YYYY-MM-DD or null"}}
    ],
    "contract_awards": [
        {{"counterparty": "...", "contract_value": "...", "currency": "USD", "description": "...", "award_date": "YYYY-MM-DD or null"}}
    ],
    "capex_guidance": [
        {{"amount": "...", "currency": "USD", "period": "...", "description": "..."}}
    ],
    "going_concern_flag": true or false,
    "going_concern_details": "explanation if flag is true, else null",
    "undisclosed_counterparties": [
        {{"name": "...", "context": "...", "risk_level": "low|medium|high"}}
    ]
}}

Rules:
- Only extract information explicitly stated in the filing text
- If a field has no data, return an empty list or null
- going_concern_flag is true only if the filing explicitly mentions going concern doubt
- undisclosed_counterparties are entities mentioned without full disclosure of the relationship
- Return ONLY the JSON object, no markdown, no explanation

Filing text:
{filing_text}
"""


def extract_signals_from_text(filing_text: str, ticker: str) -> Optional[dict]:
    """Send filing text to GPT-4o and extract structured financial signals."""
    try:
        truncated_text = filing_text[:12000]  # GPT-4o context limit buffer

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst that extracts structured data from SEC filings. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(filing_text=truncated_text)
                }
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        raw_json = response.choices[0].message.content
        signals = json.loads(raw_json)
        logger.info("Extraction complete", ticker=ticker)
        return signals

    except Exception as e:
        logger.error("GPT-4o extraction failed", ticker=ticker, error=str(e))
        return None


def save_extraction_to_db(extraction: ExtractionResult) -> Optional[str]:
    """Save extraction results to filings_extractions table."""
    db = SessionLocal()
    try:
        check = db.execute(
            text("SELECT id FROM filings_extractions WHERE filing_id = :fid"),
            {"fid": str(extraction.filing_id)}
        ).fetchone()

        if check:
            logger.info("Extraction already exists", filing_id=str(extraction.filing_id))
            return str(check[0])

        result = db.execute(
            text("""
                INSERT INTO filings_extractions
                (filing_id, ticker, filing_type, capital_structure_changes,
                 contract_awards, capex_guidance, going_concern_flag,
                 going_concern_details, undisclosed_counterparties,
                 raw_signals, extraction_model)
                VALUES
                (:filing_id, :ticker, :filing_type, :capital_structure_changes,
                 :contract_awards, :capex_guidance, :going_concern_flag,
                 :going_concern_details, :undisclosed_counterparties,
                 :raw_signals, :extraction_model)
                RETURNING id
            """),
            {
                "filing_id": str(extraction.filing_id),
                "ticker": extraction.ticker,
                "filing_type": extraction.filing_type,
                "capital_structure_changes": json.dumps([c.model_dump() for c in extraction.capital_structure_changes]),
                "contract_awards": json.dumps([c.model_dump() for c in extraction.contract_awards]),
                "capex_guidance": json.dumps([c.model_dump() for c in extraction.capex_guidance]),
                "going_concern_flag": extraction.going_concern_flag,
                "going_concern_details": extraction.going_concern_details,
                "undisclosed_counterparties": json.dumps([c.model_dump() for c in extraction.undisclosed_counterparties]),
                "raw_signals": json.dumps(extraction.raw_signals),
                "extraction_model": extraction.extraction_model
            }
        )
        db.commit()
        extraction_id = str(result.fetchone()[0])
        logger.info("Extraction saved", ticker=extraction.ticker, id=extraction_id)
        return extraction_id

    except Exception as e:
        db.rollback()
        logger.error("Failed to save extraction", error=str(e))
        return None
    finally:
        db.close()


def get_pending_filings() -> list[dict]:
    """Fetch all ingested filings that have not been extracted yet."""
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT f.id, f.ticker, f.filing_type, f.raw_text
            FROM filings_raw f
            LEFT JOIN filings_extractions e ON f.id = e.filing_id
            WHERE f.status = 'ingested'
            AND e.id IS NULL
            AND f.raw_text IS NOT NULL
        """)).fetchall()
        return [{"id": str(r[0]), "ticker": r[1], "filing_type": r[2], "raw_text": r[3]} for r in rows]
    finally:
        db.close()


async def run_extraction_agent() -> dict:
    """Main extraction agent: processes all pending filings."""
    pending = get_pending_filings()
    results = {"total": len(pending), "extracted": 0, "errors": 0}

    logger.info("Starting extraction", pending_count=len(pending))

    for filing in pending:
        signals = extract_signals_from_text(filing["raw_text"], filing["ticker"])

        if not signals:
            results["errors"] += 1
            continue

        try:
            extraction = ExtractionResult(
                filing_id=UUID(filing["id"]),
                ticker=filing["ticker"],
                filing_type=filing["filing_type"],
                capital_structure_changes=[
                    CapitalStructureChange(**c) for c in signals.get("capital_structure_changes", [])
                ],
                contract_awards=[
                    ContractAward(**c) for c in signals.get("contract_awards", [])
                ],
                capex_guidance=[
                    CapexGuidance(**c) for c in signals.get("capex_guidance", [])
                ],
                going_concern_flag=signals.get("going_concern_flag", False),
                going_concern_details=signals.get("going_concern_details"),
                undisclosed_counterparties=[
                    UndisclosedCounterparty(**c) for c in signals.get("undisclosed_counterparties", [])
                ],
                raw_signals=signals
            )

            extraction_id = save_extraction_to_db(extraction)
            if extraction_id:
                results["extracted"] += 1
            else:
                results["errors"] += 1

        except Exception as e:
            logger.error("Extraction build failed", filing_id=filing["id"], error=str(e))
            results["errors"] += 1

    logger.info("Extraction agent complete", **results)
    return results