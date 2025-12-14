"""Trend analysis service - identifies performance trends over time"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from supabase import Client


class TrendAnalyzer:
    """Analyzes trends in monitoring data"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def analyze_trends(self, monitor_id: str, days: int = 7) -> Dict:
        """
        Analyze trends for a monitor
        
        Args:
            monitor_id: UUID of the monitor
            days: Number of days to analyze
            
        Returns:
            Trend analysis results
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        response = self.supabase.table("ping_logs")\
            .select("*")\
            .eq("monitor_id", monitor_id)\
            .gte("checked_at", start_time.isoformat())\
            .order("checked_at", desc=False)\
            .execute()
        
        if not response.data or len(response.data) < 10:
            return {
                "monitor_id": monitor_id,
                "trend": "insufficient_data",
                "metrics": {}
            }
        
        df = pd.DataFrame(response.data)
        df['checked_at'] = pd.to_datetime(df['checked_at'])
        df = df.sort_values('checked_at')
        
        # Calculate hourly aggregates
        df['hour'] = df['checked_at'].dt.floor('h')  # Changed 'H' to 'h' for pandas compatibility
        hourly_stats = df.groupby('hour').agg({
            'latency_ms': ['mean', 'std', 'min', 'max'],
            'is_success': 'mean',
            'status_code': 'mean'
        }).reset_index()
        
        # Latency trend
        latencies = df['latency_ms'].values
        if len(latencies) >= 20:
            # Simple linear regression for trend
            x = np.arange(len(latencies))
            slope = np.polyfit(x, latencies, 1)[0]
            
            if slope > 5:  # Increasing by more than 5ms per check
                latency_trend = "increasing"
            elif slope < -5:
                latency_trend = "decreasing"
            else:
                latency_trend = "stable"
        else:
            latency_trend = "insufficient_data"
        
        # Uptime trend
        recent_uptime = df.tail(100)['is_success'].mean()
        older_uptime = df.head(100)['is_success'].mean() if len(df) >= 200 else recent_uptime
        
        if recent_uptime < older_uptime - 0.1:
            uptime_trend = "degrading"
        elif recent_uptime > older_uptime + 0.1:
            uptime_trend = "improving"
        else:
            uptime_trend = "stable"
        
        # Overall trend
        if latency_trend == "increasing" and uptime_trend == "degrading":
            overall_trend = "declining"
        elif latency_trend == "decreasing" and uptime_trend == "improving":
            overall_trend = "improving"
        else:
            overall_trend = "stable"
        
        # Calculate statistics (convert numpy types to native Python types)
        avg_latency = float(df['latency_ms'].mean())
        p95_latency = float(df['latency_ms'].quantile(0.95))
        p99_latency = float(df['latency_ms'].quantile(0.99))
        uptime_percentage = float(df['is_success'].mean() * 100)
        total_checks = int(len(df))
        successful_checks = int(df['is_success'].sum())
        failed_checks = int((~df['is_success']).sum())
        
        return {
            "monitor_id": monitor_id,
            "trend": overall_trend,
            "latency_trend": latency_trend,
            "uptime_trend": uptime_trend,
            "metrics": {
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "p99_latency_ms": round(p99_latency, 2),
                "uptime_percentage": round(uptime_percentage, 2),
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks
            },
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days
            },
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def analyze_all_monitors(self) -> Dict[str, Dict]:
        """Analyze trends for all active monitors"""
        response = self.supabase.table("monitors")\
            .select("id")\
            .eq("is_enabled", True)\
            .execute()
        
        results = {}
        for monitor in response.data:
            monitor_id = monitor['id']
            results[monitor_id] = self.analyze_trends(monitor_id)
        
        return results

