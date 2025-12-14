"""Background worker for continuous analysis"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from app.services.anomaly_detector import AnomalyDetector
from app.services.failure_predictor import FailurePredictor
from app.services.trend_analyzer import TrendAnalyzer
from app.services.alert_classifier import AlertClassifier

logger = logging.getLogger(__name__)


async def analyze_cycle(
    anomaly_detector: AnomalyDetector,
    failure_predictor: FailurePredictor,
    trend_analyzer: TrendAnalyzer,
    alert_classifier: AlertClassifier
):
    """Run one analysis cycle"""
    try:
        logger.info("Starting analysis cycle")
        
        # Run analyses
        anomalies = anomaly_detector.analyze_all_monitors()
        predictions = failure_predictor.predict_all_monitors()
        trends = trend_analyzer.analyze_all_monitors()
        
        logger.info(f"Analysis complete: {len(anomalies)} monitors with anomalies, "
                   f"{len(predictions)} predictions, {len(trends)} trends")
        
        # Here you could store results in database if needed
        # For now, we just log them
        
    except Exception as e:
        logger.error(f"Error in analysis cycle: {e}")


async def analyzer_worker_loop(
    anomaly_detector: AnomalyDetector,
    failure_predictor: FailurePredictor,
    trend_analyzer: TrendAnalyzer,
    alert_classifier: AlertClassifier,
    interval_seconds: int = 300  # 5 minutes
):
    """Main worker loop"""
    logger.info(f"Starting analyzer worker (interval: {interval_seconds}s)")
    
    while True:
        try:
            await analyze_cycle(
                anomaly_detector,
                failure_predictor,
                trend_analyzer,
                alert_classifier
            )
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Analyzer worker cancelled")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(interval_seconds)


def start_analyzer_worker(
    anomaly_detector: AnomalyDetector,
    failure_predictor: FailurePredictor,
    trend_analyzer: TrendAnalyzer,
    alert_classifier: AlertClassifier
) -> asyncio.Task:
    """Start the analyzer worker as a background task"""
    task = asyncio.create_task(
        analyzer_worker_loop(
            anomaly_detector,
            failure_predictor,
            trend_analyzer,
            alert_classifier
        )
    )
    return task

