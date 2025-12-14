"""
Nerve AIOps Backend - FastAPI Application
Provides anomaly detection, failure prediction, trend analysis, and alert classification
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.services.supabase_client import get_supabase_client
from app.services.anomaly_detector import AnomalyDetector
from app.services.failure_predictor import FailurePredictor
from app.services.trend_analyzer import TrendAnalyzer
from app.services.alert_classifier import AlertClassifier
from app.routers import monitors, alerts, predictions, trends
from app.workers.analyzer_worker import start_analyzer_worker
import asyncio

# Load environment variables
load_dotenv()

# Global services
anomaly_detector = None
failure_predictor = None
trend_analyzer = None
alert_classifier = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global anomaly_detector, failure_predictor, trend_analyzer, alert_classifier
    
    # Initialize services
    supabase = get_supabase_client()
    anomaly_detector = AnomalyDetector(supabase)
    failure_predictor = FailurePredictor(supabase)
    trend_analyzer = TrendAnalyzer(supabase)
    alert_classifier = AlertClassifier(supabase)
    
    # Start background worker
    worker_task = start_analyzer_worker(
        anomaly_detector,
        failure_predictor,
        trend_analyzer,
        alert_classifier
    )
    
    yield
    
    # Cleanup - cancel the task (it will handle cancellation gracefully)
    if worker_task and not worker_task.done():
        worker_task.cancel()
        # Don't wait for completion here - let it cancel in the background


# Create FastAPI app
app = FastAPI(
    title="Nerve AIOps Backend",
    description="AIOps intelligence layer for monitoring and predictions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(monitors.router, prefix="/api/monitors", tags=["monitors"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nerve AIOps Backend",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

