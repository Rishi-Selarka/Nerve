"""Alert classification service - categorizes and prioritizes alerts"""

from datetime import datetime
from typing import Dict, List
from supabase import Client


class AlertClassifier:
    """Classifies alerts by severity and type"""
    
    SEVERITY_LEVELS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def classify_alert(self, alert_data: Dict) -> Dict:
        """
        Classify an alert based on its characteristics
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            Classified alert with severity and category
        """
        alert_type = alert_data.get("type", "unknown")
        severity = alert_data.get("severity", "medium")
        
        # Determine category
        if alert_type == "status_anomaly":
            category = "availability"
            if alert_data.get("status_code") == 0:
                severity = "critical"  # Network failure
            elif alert_data.get("status_code", 0) >= 500:
                severity = "high"  # Server error
        elif alert_type == "latency_anomaly":
            category = "performance"
            value = alert_data.get("value", 0)
            threshold = alert_data.get("threshold", 0)
            
            if value > threshold * 2:
                severity = "critical"
            elif value > threshold * 1.5:
                severity = "high"
        else:
            category = "general"
        
        # Calculate priority score
        priority_score = self.SEVERITY_LEVELS.get(severity, 2)
        
        return {
            **alert_data,
            "category": category,
            "severity": severity,
            "priority_score": priority_score,
            "classified_at": datetime.utcnow().isoformat()
        }
    
    def classify_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """Classify multiple alerts"""
        classified = [self.classify_alert(alert) for alert in alerts]
        # Sort by priority score (highest first)
        classified.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return classified
    
    def get_alert_summary(self, monitor_id: str) -> Dict:
        """Get alert summary for a monitor"""
        # This would typically query an alerts table
        # For now, return a placeholder structure
        return {
            "monitor_id": monitor_id,
            "total_alerts": 0,
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "by_category": {
                "availability": 0,
                "performance": 0,
                "general": 0
            }
        }

