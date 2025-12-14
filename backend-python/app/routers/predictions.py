"""Prediction-related API endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.failure_predictor import FailurePredictor
from app.services.supabase_client import get_supabase_client

router = APIRouter()

def get_predictor():
    """Get predictor instance"""
    supabase = get_supabase_client()
    return FailurePredictor(supabase)


@router.get("/")
async def get_predictions(monitor_id: Optional[str] = None):
    """Get failure predictions, optionally filtered by monitor"""
    try:
        failure_predictor = get_predictor()
        if monitor_id:
            prediction = failure_predictor.predict_failure_risk(monitor_id)
            return {"predictions": [prediction]}
        else:
            predictions = failure_predictor.predict_all_monitors()
            return {"predictions": list(predictions.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{monitor_id}")
async def get_prediction(monitor_id: str):
    """Get failure prediction for a specific monitor"""
    try:
        failure_predictor = get_predictor()
        prediction = failure_predictor.predict_failure_risk(monitor_id)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

