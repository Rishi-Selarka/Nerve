"""Monitor-related API endpoints"""

from fastapi import APIRouter, HTTPException
from app.services.supabase_client import get_supabase_client

router = APIRouter()

def get_supabase():
    """Get supabase client"""
    return get_supabase_client()


@router.get("/")
async def get_monitors():
    """Get all monitors"""
    try:
        supabase = get_supabase()
        response = supabase.table("monitors")\
            .select("*")\
            .eq("is_enabled", True)\
            .execute()
        return {"monitors": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{monitor_id}")
async def get_monitor(monitor_id: str):
    """Get a specific monitor"""
    try:
        supabase = get_supabase()
        response = supabase.table("monitors")\
            .select("*")\
            .eq("id", monitor_id)\
            .single()\
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Monitor not found")

