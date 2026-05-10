"""
LangGraph Orchestration Graph — Financial Filing Intelligence Agent
Connects all five pipelines as a stateful multi-agent graph.
Datawebify | filings.datawebify.com
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.ingestion_agent import run_ingestion_agent
from app.agents.extraction_agent import run_extraction_agent
from app.agents.comparison_agent import run_comparison_agent
from app.agents.alert_agent import run_alert_pipeline
from app.agents.excel_agent import run_excel_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph State — shared across all nodes
# ---------------------------------------------------------------------------

class FilingAgentState(TypedDict):
    # Inputs
    tickers: List[str]
    filing_types: List[str]
    days_back: int
    push_slack: bool
    export_excel: bool

    # Pipeline outputs
    ingestion_result: Optional[Dict[str, Any]]
    extraction_result: Optional[Dict[str, Any]]
    comparison_result: Optional[Dict[str, Any]]
    alert_result: Optional[Dict[str, Any]]
    excel_result: Optional[Dict[str, Any]]

    # Control flow
    errors: List[str]
    current_step: str
    completed_steps: List[str]


# ---------------------------------------------------------------------------
# Node functions — one per pipeline
# ---------------------------------------------------------------------------

def node_ingest(state: FilingAgentState) -> FilingAgentState:
    """Node 1: Ingest filings from SEC EDGAR for all tickers in the basket."""
    logger.info(f"[LangGraph] Node: ingest | Tickers: {state['tickers']}")

    try:
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=state["days_back"])).isoformat()

        result = asyncio.run(
            run_ingestion_agent(
                tickers=state["tickers"],
                form_types=state["filing_types"],
                start_date=start_date,
                end_date=end_date
            )
        )
        logger.info(f"[LangGraph] Ingestion complete: {result}")
        return {
            **state,
            "ingestion_result": result,
            "current_step": "ingest",
            "completed_steps": state["completed_steps"] + ["ingest"]
        }
    except Exception as e:
        logger.error(f"[LangGraph] Ingestion node failed: {e}")
        return {
            **state,
            "ingestion_result": {"error": str(e)},
            "errors": state["errors"] + [f"ingest: {e}"],
            "current_step": "ingest",
            "completed_steps": state["completed_steps"] + ["ingest"]
        }


def node_extract(state: FilingAgentState) -> FilingAgentState:
    """Node 2: Run GPT-4o extraction on all pending ingested filings."""
    logger.info("[LangGraph] Node: extract")

    try:
        result = asyncio.run(run_extraction_agent())
        logger.info(f"[LangGraph] Extraction complete: {result}")
        return {
            **state,
            "extraction_result": result,
            "current_step": "extract",
            "completed_steps": state["completed_steps"] + ["extract"]
        }
    except Exception as e:
        logger.error(f"[LangGraph] Extraction node failed: {e}")
        return {
            **state,
            "extraction_result": {"error": str(e)},
            "errors": state["errors"] + [f"extract: {e}"],
            "current_step": "extract",
            "completed_steps": state["completed_steps"] + ["extract"]
        }


def node_compare(state: FilingAgentState) -> FilingAgentState:
    """Node 3: Run cross-entity anomaly detection across the sector basket."""
    logger.info(f"[LangGraph] Node: compare | Basket: {state['tickers']}")

    try:
        result = asyncio.run(
            run_comparison_agent(sector_basket=state["tickers"])
        )
        logger.info(f"[LangGraph] Comparison complete: {result}")
        return {
            **state,
            "comparison_result": result,
            "current_step": "compare",
            "completed_steps": state["completed_steps"] + ["compare"]
        }
    except Exception as e:
        logger.error(f"[LangGraph] Comparison node failed: {e}")
        return {
            **state,
            "comparison_result": {"error": str(e)},
            "errors": state["errors"] + [f"compare: {e}"],
            "current_step": "compare",
            "completed_steps": state["completed_steps"] + ["compare"]
        }


def node_alert(state: FilingAgentState) -> FilingAgentState:
    """Node 4: Push anomaly alerts to Slack (conditional on push_slack flag)."""
    if not state.get("push_slack", True):
        logger.info("[LangGraph] Node: alert | Skipped (push_slack=False)")
        return {
            **state,
            "alert_result": {"skipped": True},
            "current_step": "alert",
            "completed_steps": state["completed_steps"] + ["alert"]
        }

    logger.info("[LangGraph] Node: alert")
    try:
        result = run_alert_pipeline(tickers=state["tickers"])
        logger.info(f"[LangGraph] Alert complete: {result}")
        return {
            **state,
            "alert_result": result,
            "current_step": "alert",
            "completed_steps": state["completed_steps"] + ["alert"]
        }
    except Exception as e:
        logger.error(f"[LangGraph] Alert node failed: {e}")
        return {
            **state,
            "alert_result": {"error": str(e)},
            "errors": state["errors"] + [f"alert: {e}"],
            "current_step": "alert",
            "completed_steps": state["completed_steps"] + ["alert"]
        }


def node_export(state: FilingAgentState) -> FilingAgentState:
    """Node 5: Build and export DCF scaffold Excel files (conditional on export_excel flag)."""
    if not state.get("export_excel", True):
        logger.info("[LangGraph] Node: export | Skipped (export_excel=False)")
        return {
            **state,
            "excel_result": {"skipped": True},
            "current_step": "export",
            "completed_steps": state["completed_steps"] + ["export"]
        }

    logger.info(f"[LangGraph] Node: export | Tickers: {state['tickers']}")
    try:
        result = run_excel_pipeline(tickers=state["tickers"])
        logger.info(f"[LangGraph] Export complete: {result}")
        return {
            **state,
            "excel_result": result,
            "current_step": "export",
            "completed_steps": state["completed_steps"] + ["export"]
        }
    except Exception as e:
        logger.error(f"[LangGraph] Export node failed: {e}")
        return {
            **state,
            "excel_result": {"error": str(e)},
            "errors": state["errors"] + [f"export: {e}"],
            "current_step": "export",
            "completed_steps": state["completed_steps"] + ["export"]
        }


# ---------------------------------------------------------------------------
# Conditional edge: skip extract if ingestion found nothing new
# ---------------------------------------------------------------------------

def should_extract(state: FilingAgentState) -> str:
    """After ingestion: proceed to extract, or skip to compare if nothing saved."""
    ingestion = state.get("ingestion_result") or {}
    if ingestion.get("error"):
        logger.warning("[LangGraph] Ingestion had errors, proceeding to extract anyway")
    saved = ingestion.get("saved", 0)
    if saved == 0:
        logger.info("[LangGraph] No new filings saved, skipping to compare")
        return "compare"
    return "extract"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Assemble and compile the LangGraph orchestration graph."""
    graph = StateGraph(FilingAgentState)

    # Register nodes
    graph.add_node("ingest", node_ingest)
    graph.add_node("extract", node_extract)
    graph.add_node("compare", node_compare)
    graph.add_node("alert", node_alert)
    graph.add_node("export", node_export)

    # Entry point
    graph.set_entry_point("ingest")

    # Conditional edge after ingestion
    graph.add_conditional_edges(
        "ingest",
        should_extract,
        {
            "extract": "extract",
            "compare": "compare"
        }
    )

    # Linear edges for the rest
    graph.add_edge("extract", "compare")
    graph.add_edge("compare", "alert")
    graph.add_edge("alert", "export")
    graph.add_edge("export", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

def run_graph(
    tickers: List[str],
    filing_types: Optional[List[str]] = None,
    days_back: int = 30,
    push_slack: bool = True,
    export_excel: bool = True,
) -> Dict[str, Any]:
    """
    Run the full LangGraph orchestration pipeline.
    Returns the final state with all pipeline results.
    """
    if filing_types is None:
        filing_types = ["8-K", "10-K", "10-Q"]

    initial_state: FilingAgentState = {
        "tickers": [t.upper() for t in tickers],
        "filing_types": filing_types,
        "days_back": days_back,
        "push_slack": push_slack,
        "export_excel": export_excel,
        "ingestion_result": None,
        "extraction_result": None,
        "comparison_result": None,
        "alert_result": None,
        "excel_result": None,
        "errors": [],
        "current_step": "start",
        "completed_steps": [],
    }

    logger.info(f"[LangGraph] Starting graph | Tickers: {tickers}")
    graph = build_graph()
    final_state = graph.invoke(initial_state)

    logger.info(f"[LangGraph] Graph complete | Steps: {final_state.get('completed_steps')}")
    return {
        "tickers": final_state["tickers"],
        "completed_steps": final_state["completed_steps"],
        "errors": final_state["errors"],
        "ingestion": final_state["ingestion_result"],
        "extraction": final_state["extraction_result"],
        "comparison": final_state["comparison_result"],
        "alerts": final_state["alert_result"],
        "excel_export": final_state["excel_result"],
    }