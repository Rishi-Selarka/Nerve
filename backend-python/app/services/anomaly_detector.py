"""Anomaly detection service - identifies unusual patterns in monitoring data"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from supabase import Client


class AnomalyDetector:
    """Detects anomalies in latency and status patterns"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def detect_anomalies(self, monitor_id: str, hours: int = 24) -> List[Dict]:
        """
        Detect anomalies for a specific monitor
        
        Args:
            monitor_id: UUID of the monitor
            hours: Number of hours of data to analyze
            
        Returns:
            List of anomaly records
        """
        # Fetch recent ping logs
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        response = self.supabase.table("ping_logs")\
            .select("*")\
            .eq("monitor_id", monitor_id)\
            .gte("checked_at", start_time.isoformat())\
            .order("checked_at", desc=False)\
            .execute()
        
        if not response.data:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        df['checked_at'] = pd.to_datetime(df['checked_at'])
        df = df.sort_values('checked_at')
        
        anomalies = []
        
        # Detect latency anomalies using IQR method
        latency_anomalies = self._detect_latency_anomalies(df)
        anomalies.extend(latency_anomalies)
        
        # Detect status code anomalies (unexpected failures)
        status_anomalies = self._detect_status_anomalies(df)
        anomalies.extend(status_anomalies)
        
        return anomalies
    
    def _detect_latency_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect latency anomalies using IQR (Interquartile Range) method"""
        anomalies = []
        
        if len(df) < 10:  # Need minimum data points
            return anomalies
        
        latencies = df['latency_ms'].values
        
        Q1 = np.percentile(latencies, 25)
        Q3 = np.percentile(latencies, 75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Find anomalies
        anomaly_mask = (latencies < lower_bound) | (latencies > upper_bound)
        anomaly_rows = df[anomaly_mask]
        
        for _, row in anomaly_rows.iterrows():
            anomalies.append({
                "type": "latency_anomaly",
                "monitor_id": row['monitor_id'],
                "checked_at": row['checked_at'].isoformat(),
                "value": int(row['latency_ms']),
                "threshold": float(upper_bound if row['latency_ms'] > upper_bound else lower_bound),
                "severity": "high" if row['latency_ms'] > upper_bound * 2 else "medium"
            })
        
        return anomalies
    
    def _detect_status_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect unexpected status code changes"""
        anomalies = []
        
        if len(df) < 5:
            return anomalies
        
        # Group by success status
        recent_success_rate = df.tail(10)['is_success'].mean()
        
        # If recent failures after a period of success
        if recent_success_rate < 0.5 and df['is_success'].head(-10).mean() > 0.9:
            failed_rows = df[~df['is_success']].tail(5)
            for _, row in failed_rows.iterrows():
                anomalies.append({
                    "type": "status_anomaly",
                    "monitor_id": row['monitor_id'],
                    "checked_at": row['checked_at'].isoformat(),
                    "status_code": int(row['status_code']),
                    "severity": "critical" if row['status_code'] == 0 else "high"
                })
        
        return anomalies
    
    def analyze_all_monitors(self) -> Dict[str, List[Dict]]:
        """Analyze all active monitors for anomalies"""
        # Fetch all enabled monitors
        response = self.supabase.table("monitors")\
            .select("id")\
            .eq("is_enabled", True)\
            .execute()
        
        results = {}
        for monitor in response.data:
            monitor_id = monitor['id']
            anomalies = self.detect_anomalies(monitor_id)
            if anomalies:
                results[monitor_id] = anomalies
        
        return results

