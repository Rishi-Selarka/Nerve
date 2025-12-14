"""Trend analysis API endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.trend_analyzer import TrendAnalyzer
from app.services.supabase_client import get_supabase_client

router = APIRouter()

def get_analyzer():
    """Get analyzer instance"""
    supabase = get_supabase_client()
    return TrendAnalyzer(supabase)


@router.get("/")
async def get_trends(monitor_id: Optional[str] = None, days: int = 7):
    """Get trend analysis, optionally filtered by monitor"""
    try:
        trend_analyzer = get_analyzer()
        if monitor_id:
            trend = trend_analyzer.analyze_trends(monitor_id, days)
            return {"trends": [trend]}
        else:
            trends = trend_analyzer.analyze_all_monitors()
            return {"trends": list(trends.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{monitor_id}")
async def get_trend(monitor_id: str, days: int = 7):
    """Get trend analysis for a specific monitor"""
    try:
        trend_analyzer = get_analyzer()
        trend = trend_analyzer.analyze_trends(monitor_id, days)
        return trend
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

