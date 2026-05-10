"""
Pipeline 4: Alert Agent
Pushes anomaly reports to Slack and handles human-in-the-loop review gate.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.models.schemas import AlertLog, AnalystReview

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_webhook_url() -> Optional[str]:
    """Read Slack webhook URL from environment at call time (not import time)."""
    import os
    return os.getenv("SLACK_WEBHOOK_URL")


def _build_slack_blocks(anomaly: dict) -> list:
    """
    Build Slack Block Kit payload for a single anomaly.
    Returns a list of blocks ready to POST to Slack.
    """
    anomaly_id = anomaly.get("id", "unknown")
    anomaly_type = anomaly.get("anomaly_type", "unknown")
    tickers = ", ".join(anomaly.get("tickers_involved", []))
    description = anomaly.get("description", "No description provided.")
    severity = anomaly.get("severity", "medium").upper()
    detected_at = anomaly.get("detected_at", str(datetime.now(timezone.utc)))

    # Severity emoji map
    severity_emoji = {"HIGH": ":red_circle:", "MEDIUM": ":large_yellow_circle:", "LOW": ":large_green_circle:"}
    emoji = severity_emoji.get(severity, ":white_circle:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Filing Anomaly Detected — {anomaly_type.replace('_', ' ').title()}"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Anomaly ID:*\n{anomaly_id}"},
                {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                {"type": "mrkdwn", "text": f"*Tickers:*\n{tickers}"},
                {"type": "mrkdwn", "text": f"*Detected At:*\n{detected_at}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{description}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Review this alert at:* `POST /api/v1/alerts/{{anomaly_id}}/review`\n"
                        f"Body: `{{\"action\": \"approve\"}}` or `{{\"action\": \"dismiss\", \"notes\": \"reason\"}}`"
            }
        },
        {"type": "divider"}
    ]
    return blocks


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def push_anomaly_to_slack(anomaly: dict) -> dict:
    """
    Push a single anomaly record to Slack via webhook.
    Returns a result dict with success status and any error message.
    """
    webhook_url = _get_webhook_url()

    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set. Skipping Slack push.")
        return {"success": False, "error": "SLACK_WEBHOOK_URL not configured"}

    blocks = _build_slack_blocks(anomaly)
    payload = {
        "text": f"Filing Anomaly Alert: {anomaly.get('anomaly_type', 'unknown')} — {', '.join(anomaly.get('tickers_involved', []))}",
        "blocks": blocks
    }

    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        logger.info(f"Slack alert sent for anomaly {anomaly.get('id')}")
        return {"success": True, "status_code": response.status_code}

    except httpx.HTTPStatusError as e:
        logger.error(f"Slack webhook HTTP error: {e.response.status_code} — {e.response.text}")
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}

    except Exception as e:
        logger.error(f"Slack push failed: {e}")
        return {"success": False, "error": str(e)}


def log_alert_to_db(db: Session, anomaly_id: str, slack_result: dict) -> None:
    """
    Write an alert log record to filings_alert_logs after Slack push attempt.
    """
    try:
        db.execute(
            text("""
                INSERT INTO filings_alert_logs
                    (anomaly_id, slack_sent, slack_error, analyst_action, created_at)
                VALUES
                    (:anomaly_id, :slack_sent, :slack_error, 'pending', NOW())
                ON CONFLICT (anomaly_id) DO NOTHING
            """),
            {
                "anomaly_id": anomaly_id,
                "slack_sent": slack_result.get("success", False),
                "slack_error": slack_result.get("error")
            }
        )
        db.commit()
        logger.info(f"Alert log written for anomaly {anomaly_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write alert log: {e}")


def process_analyst_review(db: Session, anomaly_id: str, action: str, notes: Optional[str] = None) -> dict:
    """
    Record an analyst's approve or dismiss decision for an alert.
    action must be 'approve' or 'dismiss'.
    """
    if action not in ("approve", "dismiss"):
        return {"success": False, "error": "action must be 'approve' or 'dismiss'"}

    try:
        result = db.execute(
            text("""
                UPDATE filings_alert_logs
                SET
                    analyst_action = :action,
                    analyst_notes  = :notes,
                    reviewed_at    = NOW()
                WHERE anomaly_id = :anomaly_id
                RETURNING anomaly_id
            """),
            {
                "action": action,
                "notes": notes,
                "anomaly_id": anomaly_id
            }
        )
        db.commit()

        row = result.fetchone()
        if not row:
            return {"success": False, "error": f"No alert log found for anomaly_id {anomaly_id}"}

        logger.info(f"Analyst review recorded: anomaly={anomaly_id}, action={action}")
        return {"success": True, "anomaly_id": anomaly_id, "action": action}

    except Exception as e:
        db.rollback()
        logger.error(f"Review update failed: {e}")
        return {"success": False, "error": str(e)}


def run_alert_pipeline(tickers: Optional[list] = None) -> dict:
    """
    Full alert pipeline:
    1. Fetch all unalerted anomalies from filings_anomalies
    2. Push each to Slack
    3. Log result to filings_alert_logs
    Returns a summary dict.
    """
    db = next(get_db())
    results = {"pushed": 0, "skipped": 0, "errors": 0, "anomalies": []}

    try:
        # Fetch anomalies not yet logged (no matching row in alert_logs)
        query = """
            SELECT
                a.id,
                a.anomaly_type,
                a.source_ticker,
                a.target_ticker,
                a.description,
                a.severity,
                a.created_at,
                a.sector_basket
            FROM filings_anomalies a
            LEFT JOIN filings_alert_logs al ON al.anomaly_id = a.id
            WHERE al.anomaly_id IS NULL
        """

        if tickers:
            query += " AND (a.source_ticker = ANY(:tickers) OR a.target_ticker = ANY(:tickers))"
            rows = db.execute(text(query), {"tickers": tickers}).fetchall()
        else:
            rows = db.execute(text(query)).fetchall()

        logger.info(f"Found {len(rows)} unalerted anomalies")

        for row in rows:
            anomaly = {
                "id": str(row[0]),
                "anomaly_type": row[1],
                "tickers_involved": [t for t in [row[2], row[3]] if t],
                "description": row[4],
                "severity": row[5] or "medium",
                "detected_at": str(row[6]),
                "raw_data": {}
            }

            slack_result = push_anomaly_to_slack(anomaly)
            log_alert_to_db(db, anomaly["id"], slack_result)

            if slack_result["success"]:
                results["pushed"] += 1
            else:
                results["errors"] += 1

            results["anomalies"].append({
                "anomaly_id": anomaly["id"],
                "slack_sent": slack_result["success"],
                "error": slack_result.get("error")
            })

        return results

    except Exception as e:
        logger.error(f"Alert pipeline failed: {e}")
        return {"error": str(e), "pushed": 0, "errors": 1}

    finally:
        db.close()