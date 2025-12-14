"""Alert-related API endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.anomaly_detector import AnomalyDetector
from app.services.alert_classifier import AlertClassifier
from app.services.supabase_client import get_supabase_client

router = APIRouter()

def get_services():
    """Get service instances"""
    supabase = get_supabase_client()
    return AnomalyDetector(supabase), AlertClassifier(supabase)


@router.get("/")
async def get_alerts(monitor_id: Optional[str] = None):
    """Get alerts, optionally filtered by monitor"""
    try:
        anomaly_detector, alert_classifier = get_services()
        if monitor_id:
            anomalies = anomaly_detector.detect_anomalies(monitor_id)
        else:
            anomalies_dict = anomaly_detector.analyze_all_monitors()
            anomalies = []
            for monitor_anomalies in anomalies_dict.values():
                anomalies.extend(monitor_anomalies)
        
        # Classify alerts
        classified = alert_classifier.classify_alerts(anomalies)
        return {"alerts": classified, "count": len(classified)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{monitor_id}/summary")
async def get_alert_summary(monitor_id: str):
    """Get alert summary for a monitor"""
    try:
        anomaly_detector, alert_classifier = get_services()
        summary = alert_classifier.get_alert_summary(monitor_id)
        anomalies = anomaly_detector.detect_anomalies(monitor_id)
        summary["total_alerts"] = len(anomalies)
        
        # Count by severity
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

