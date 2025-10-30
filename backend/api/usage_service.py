from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db.database import get_db
import backend.api.usage_service as usage_service

router = APIRouter()

@router.get("/my-usage", description="Get current user's API usage and quota info.")
def get_my_usage(user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        usage = usage_service.get_user_usage(user_id, db)
        return {"usage": usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage lookup failed: {str(e)}")

@router.post("/check-quota", description="Check whether user can generate more ads or images.")
def check_user_quota(user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        can_generate, message = usage_service.check_user_quota(user_id, db)
        return {"can_generate": can_generate, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quota check failed: {str(e)}")
