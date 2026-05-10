import os
import httpx
import asyncio
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv
import structlog

from app.db.database import SessionLocal
from app.models.schemas import FilingIngest

load_dotenv()

logger = structlog.get_logger()

EDGAR_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start_date}&enddt={end_date}&forms={form_type}"
EDGAR_FILING_URL = "https://www.sec.gov/Archives/edgar/full-index"

SUPPORTED_FORMS = ["8-K", "10-K", "10-Q", "6-K"]

HEADERS = {
    "User-Agent": "Datawebify filings@datawebify.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "efts.sec.gov"
}


async def search_edgar_filings(
    ticker: str,
    form_type: str,
    start_date: str,
    end_date: str
) -> list[dict]:
    """Search SEC EDGAR for filings by ticker and form type."""
    url = (
        f"https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{ticker}%22"
        f"&dateRange=custom"
        f"&startdt={start_date}"
        f"&enddt={end_date}"
        f"&forms={form_type}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            logger.info(
                "EDGAR search complete",
                ticker=ticker,
                form_type=form_type,
                results=len(hits)
            )
            return hits
        except Exception as e:
            logger.error("EDGAR search failed", ticker=ticker, error=str(e))
            return []


async def fetch_filing_text(filing_url: str) -> Optional[str]:
    """Download raw text content of a filing from EDGAR."""
    import re
    headers = {
        "User-Agent": "Datawebify filings@datawebify.com",
        "Accept-Encoding": "gzip, deflate"
    }
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        try:
            response = await client.get(filing_url, headers=headers)
            response.raise_for_status()
            index_html = response.text

            doc_links = re.findall(
                r'href="(/Archives/edgar/data/[^"]+\.htm)"',
                index_html
            )
            if not doc_links:
                doc_links = re.findall(
                    r'href="(/Archives/edgar/data/[^"]+\.txt)"',
                    index_html
                )

            if doc_links:
                doc_url = f"https://www.sec.gov{doc_links[0]}"
                doc_response = await client.get(doc_url, headers=headers)
                doc_response.raise_for_status()
                clean_text = re.sub(r'<[^>]+>', ' ', doc_response.text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                return clean_text[:50000]
            else:
                clean_text = re.sub(r'<[^>]+>', ' ', index_html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                return clean_text[:50000] if len(clean_text) > 100 else None

        except Exception as e:
            logger.error("Filing fetch failed", url=filing_url, error=str(e))
            return None


def parse_hit_to_filing(hit: dict, ticker: str, form_type: str) -> Optional[FilingIngest]:
    """Parse a raw EDGAR search hit into a FilingIngest schema."""
    try:
        source = hit.get("_source", {})
        filed_date_str = source.get("file_date", "")
        period_str = source.get("period_of_report", "")

        filed_date = datetime.strptime(filed_date_str, "%Y-%m-%d").date() if filed_date_str else date.today()
        period_of_report = datetime.strptime(period_str, "%Y-%m-%d").date() if period_str else None

        accession_raw = source.get("adsh", "")
        accession_number = accession_raw.replace("-", "") if accession_raw else None

        ciks = source.get("ciks", [])
        cik = ciks[0].lstrip("0") if ciks else ""
        accession_nodash = accession_raw.replace("-", "") if accession_raw else ""
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik}/{accession_nodash}/{accession_raw}-index.htm"
            if accession_raw and cik else None
        )

        raw_display = source.get("display_names", [ticker])
        company_name = raw_display[0].split("(")[0].strip() if raw_display else ticker

        return FilingIngest(
            ticker=ticker.upper(),
            company_name=company_name,
            filing_type=form_type,
            filed_date=filed_date,
            period_of_report=period_of_report,
            accession_number=accession_number,
            filing_url=filing_url,
            status="pending"
        )
    except Exception as e:
        logger.error("Failed to parse hit", error=str(e))
        return None


def save_filing_to_db(filing: FilingIngest, raw_text: Optional[str] = None) -> Optional[str]:
    """Save a filing to the filings_raw table. Returns the inserted ID."""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        check = db.execute(
            text("SELECT id FROM filings_raw WHERE accession_number = :acc"),
            {"acc": filing.accession_number}
        ).fetchone()

        if check:
            logger.info("Filing already exists", accession=filing.accession_number)
            return str(check[0])

        result = db.execute(
            text("""
                INSERT INTO filings_raw
                (ticker, company_name, filing_type, filed_date, period_of_report,
                 accession_number, filing_url, raw_text, chunk_count, status)
                VALUES
                (:ticker, :company_name, :filing_type, :filed_date, :period_of_report,
                 :accession_number, :filing_url, :raw_text, :chunk_count, :status)
                RETURNING id
            """),
            {
                "ticker": filing.ticker,
                "company_name": filing.company_name,
                "filing_type": filing.filing_type,
                "filed_date": filing.filed_date,
                "period_of_report": filing.period_of_report,
                "accession_number": filing.accession_number,
                "filing_url": filing.filing_url,
                "raw_text": raw_text,
                "chunk_count": len(raw_text.split()) // 500 if raw_text else 0,
                "status": "ingested" if raw_text else "pending"
            }
        )
        db.commit()
        filing_id = str(result.fetchone()[0])
        logger.info("Filing saved", ticker=filing.ticker, id=filing_id)
        return filing_id
    except Exception as e:
        db.rollback()
        logger.error("Failed to save filing", error=str(e))
        return None
    finally:
        db.close()


async def run_ingestion_agent(
    tickers: list[str],
    form_types: list[str] = SUPPORTED_FORMS,
    start_date: str = "2024-01-01",
    end_date: str = None
) -> dict:
    """Main ingestion agent: polls EDGAR and stores filings for a list of tickers."""
    if end_date is None:
        end_date = date.today().isoformat()

    results = {"total": 0, "saved": 0, "skipped": 0, "errors": 0}

    for ticker in tickers:
        for form_type in form_types:
            hits = await search_edgar_filings(ticker, form_type, start_date, end_date)
            results["total"] += len(hits)

            for hit in hits[:5]:  # cap at 5 filings per ticker/form combo
                filing = parse_hit_to_filing(hit, ticker, form_type)
                if not filing:
                    results["errors"] += 1
                    continue

                raw_text = None
                if filing.filing_url:
                    raw_text = await fetch_filing_text(filing.filing_url)

                filing_id = save_filing_to_db(filing, raw_text)
                if filing_id:
                    results["saved"] += 1
                else:
                    results["skipped"] += 1

            await asyncio.sleep(0.5)  # rate limit: be polite to EDGAR

    logger.info("Ingestion complete", **results)
    return results