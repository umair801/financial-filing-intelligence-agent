from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID


# ─── Pipeline 1: Filing Ingestion ───────────────────────────────────────────

class FilingIngest(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    filing_type: str
    filed_date: date
    period_of_report: Optional[date] = None
    accession_number: Optional[str] = None
    filing_url: Optional[str] = None
    raw_text: Optional[str] = None
    chunk_count: int = 0
    status: str = "pending"


class FilingResponse(FilingIngest):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Pipeline 2: GPT-4o Extraction ──────────────────────────────────────────

class CapitalStructureChange(BaseModel):
    description: str
    change_type: str
    amount: Optional[str] = None
    currency: Optional[str] = None
    effective_date: Optional[str] = None

class ContractAward(BaseModel):
    counterparty: str
    contract_value: Optional[str] = None
    currency: Optional[str] = None
    description: str
    award_date: Optional[str] = None

class CapexGuidance(BaseModel):
    amount: Optional[str] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    description: str

class UndisclosedCounterparty(BaseModel):
    name: str
    context: str
    risk_level: str = "medium"

class ExtractionResult(BaseModel):
    filing_id: UUID
    ticker: str
    filing_type: str
    capital_structure_changes: list[CapitalStructureChange] = []
    contract_awards: list[ContractAward] = []
    capex_guidance: list[CapexGuidance] = []
    going_concern_flag: bool = False
    going_concern_details: Optional[str] = None
    undisclosed_counterparties: list[UndisclosedCounterparty] = []
    raw_signals: dict = {}
    extraction_model: str = "gpt-4o"


# ─── Pipeline 3: Cross-Entity Anomaly ───────────────────────────────────────

class AnomalyReport(BaseModel):
    sector_basket: list[str]
    anomaly_type: str
    description: str
    source_ticker: str
    target_ticker: str
    source_filing_id: UUID
    target_filing_id: UUID
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = "pending_review"


# ─── Pipeline 4: Alert ───────────────────────────────────────────────────────

class AlertLog(BaseModel):
    anomaly_id: UUID
    slack_message_ts: Optional[str] = None
    slack_channel: Optional[str] = None
    analyst_action: Optional[str] = None
    analyst_note: Optional[str] = None


class AnalystReview(BaseModel):
    anomaly_id: UUID
    action: str = Field(pattern="^(approve|dismiss)$")
    note: Optional[str] = None


# ─── Pipeline 5: Excel Export ────────────────────────────────────────────────

class DCFInput(BaseModel):
    ticker: str
    filing_id: UUID
    revenue_guidance: Optional[str] = None
    capex_total: Optional[str] = None
    capex_period: Optional[str] = None
    going_concern: bool = False
    filing_date: date
    notes: Optional[str] = None


# ─── API Response Wrappers ───────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None