"""
Financial Filing Intelligence Agent — FastAPI Entry Point
Datawebify | filings.datawebify.com
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
def root():
    return {
        "service": "Financial Filing Intelligence Agent",
        "brand": "Datawebify",
        "docs": "/docs",
        "version": "1.0.0",
    }