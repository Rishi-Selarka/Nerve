"""Failure prediction service - predicts potential failures before they happen"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from sklearn.ensemble import IsolationForest
from supabase import Client


class FailurePredictor:
    """Predicts potential failures based on historical patterns"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.models = {}  # Cache models per monitor
    
    def predict_failure_risk(self, monitor_id: str, hours: int = 48) -> Dict:
        """
        Predict failure risk for a monitor
        
        Args:
            monitor_id: UUID of the monitor
            hours: Hours of historical data to use
            
        Returns:
            Prediction with risk score and factors
        """
        # Fetch historical data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        response = self.supabase.table("ping_logs")\
            .select("*")\
            .eq("monitor_id", monitor_id)\
            .gte("checked_at", start_time.isoformat())\
            .order("checked_at", desc=False)\
            .execute()
        
        if not response.data or len(response.data) < 20:
            return {
                "monitor_id": monitor_id,
                "risk_score": 0.0,
                "risk_level": "low",
                "confidence": 0.0,
                "factors": [],
                "prediction": "insufficient_data"
            }
        
        df = pd.DataFrame(response.data)
        df['checked_at'] = pd.to_datetime(df['checked_at'])
        df = df.sort_values('checked_at')
        
        # Calculate risk factors
        risk_factors = []
        risk_score = 0.0
        
        # Factor 1: Recent failure rate
        recent_failures = df.tail(20)['is_success'].sum() / 20
        if recent_failures < 0.8:
            risk_score += 0.4
            risk_factors.append({
                "factor": "recent_failure_rate",
                "value": 1 - recent_failures,
                "impact": "high"
            })
        
        # Factor 2: Latency trend (increasing latency)
        if len(df) >= 30:
            recent_latency = df.tail(15)['latency_ms'].mean()
            older_latency = df.head(15)['latency_ms'].mean()
            latency_increase = (recent_latency - older_latency) / older_latency if older_latency > 0 else 0
            
            if latency_increase > 0.3:  # 30% increase
                risk_score += 0.3
                risk_factors.append({
                    "factor": "latency_increase",
                    "value": latency_increase,
                    "impact": "medium"
                })
        
        # Factor 3: Status code degradation
        recent_status_codes = df.tail(20)['status_code'].values
        non_200_count = np.sum((recent_status_codes < 200) | (recent_status_codes >= 300))
        if non_200_count > 5:
            risk_score += 0.2
            risk_factors.append({
                "factor": "status_code_degradation",
                "value": non_200_count / 20,
                "impact": "high"
            })
        
        # Factor 4: Latency volatility (using Isolation Forest)
        if len(df) >= 30:
            latencies = df['latency_ms'].values.reshape(-1, 1)
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            outliers = iso_forest.fit_predict(latencies)
            outlier_count = np.sum(outliers == -1)
            
            if outlier_count > len(df) * 0.15:  # More than 15% outliers
                risk_score += 0.1
                risk_factors.append({
                    "factor": "high_volatility",
                    "value": outlier_count / len(df),
                    "impact": "medium"
                })
        
        # Normalize risk score to 0-1
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "critical"
        elif risk_score >= 0.5:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Calculate confidence based on data quality
        confidence = min(len(df) / 100, 1.0)  # More data = higher confidence
        
        return {
            "monitor_id": monitor_id,
            "risk_score": float(round(risk_score, 3)),
            "risk_level": risk_level,
            "confidence": float(round(confidence, 3)),
            "factors": risk_factors,
            "prediction": f"Failure risk is {risk_level}",
            "predicted_at": datetime.utcnow().isoformat()
        }
    
    def predict_all_monitors(self) -> Dict[str, Dict]:
        """Predict failure risk for all active monitors"""
        response = self.supabase.table("monitors")\
            .select("id")\
            .eq("is_enabled", True)\
            .execute()
        
        predictions = {}
        for monitor in response.data:
            monitor_id = monitor['id']
            predictions[monitor_id] = self.predict_failure_risk(monitor_id)
        
        return predictions

